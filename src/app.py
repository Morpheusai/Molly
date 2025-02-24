import os
import json
import asyncio
import shutil

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException, FastAPI, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.utils import logger
from src.utils.mysql_db import search_unionid_sql
from src.api.api import *
from src.model.openai_engine import proxy_stream_generator
from src.utils.jwt_util import create_system_token
from src.file.upload_router import router as upload_router
from src.db.uploadfiles_model import UploadedFile
from src.file.upload_router import minio_client
from src.api.protocols import UserInput
from pydantic import ValidationError

logger.info(f"========================start molly backend==============================")

app = FastAPI()

origins = [
    "*",  # 允许的来源，可以添加多个
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许访问的源列表
    allow_credentials=True,  # 支持cookie跨域
    allow_methods=["*"],  # 允许的请求方法
    allow_headers=["*"],  # 允许的请求头
)

load_dotenv()
# 微信开放平台应用的 AppID 和 AppSecret
WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")
WECHAT_REDIRECT_URI = os.getenv("WECHAT_REDIRECT_URI", "")

# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "") # 用于签名和验证 JWT 的密钥
ALGORITHM = os.getenv("ALGORITHM", "HS256") # 加密算法
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))  # JWT Token 过期时间

@app.get("/")
def read_root():
    return {"Hello": "我是Molly后端服务"}

@app.get("/backend/wechat_callback")
async def wechat_callback(code: str):

    # 1. 使用 code 获取 access_token
    token_url = f"https://api.weixin.qq.com/sns/oauth2/access_token?appid={WECHAT_APP_ID}&secret={WECHAT_APP_SECRET}&code={code}&grant_type=authorization_code"
    async with httpx.AsyncClient() as client:
        response = await client.get(token_url)
        token_data = response.json()

    if "errcode" in token_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=token_data["errmsg"])

    # 2. 使用 access_token 获取用户信息
    user_info_url = f"https://api.weixin.qq.com/sns/userinfo?access_token={token_data['access_token']}&openid={token_data['openid']}"
    async with httpx.AsyncClient() as client:
        response = await client.get(user_info_url)
        user_info = response.json()

    if "errcode" in user_info:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=user_info["errmsg"])
    
    #获取unionid
    unionid = token_data.get("unionid")
    if not unionid:
        raise ValueError("未获取到unionid")
    
    #判断用户表是否已经存在记录
    user=await search_unionid_sql(unionid=unionid)
    if not user:
        #将privilege字段转成字符串
        if isinstance(user_info.get("privilege"), list):
            user_info["privilege"] = ",".join(user_info["privilege"])
    # 创建 AddUserRequest 实例
        add_user_request = AddUserRequest(
            unionid=user_info.get("unionid"),  # 用户统一标识（必填）
            openid=user_info.get("openid"),    # 普通用户的标识（必填）
            nickname=user_info.get("nickname"),  # 普通用户昵称（可选）
            sex=user_info.get("sex"),            # 普通用户性别，1为男性，2为女性（可选）
            province=user_info.get("province"),  # 普通用户个人资料填写的省份（可选）
            city=user_info.get("city"),          # 普通用户个人资料填写的城市（可选）
            country=user_info.get("country"),    # 国家，如中国为CN（可选）
            headimgurl=user_info.get("headimgurl"),  # 用户头像 URL（可选）
            privilege=user_info.get("privilege"),     # 用户特权信息（可选）
            phone=None,  #TODO 后面需要传入的参数
            email=None   #TODO 后面需要传入的参数
        )

        # 3. 入库存储用户
        await add_user(request=add_user_request)

    # 生成自身系统的 JWT Token,并存入user_token表中
    system_token = await create_system_token(unionid=unionid,wechat_access_token=token_data['access_token'])

    # 返回成功响应
    return {
        "ok": "0",
        "failed":"",
        "system_token": system_token,
        "unionid": user_info.get("unionid"),
        "headimgurl": user_info.get("headimgurl"),
        "nickname": user_info.get("nickname")
    }
#chat with files
# 存储每个会话的停止事件
stop_events: Dict[str, asyncio.Event] = {}

@app.post("/backend/chat_with_files")
async def backend_chat_with_files(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> StreamingResponse:
    """代理聊天接口，支持文件上传信息，流式转发到目标服务器"""
    try:
        raw_body = await request.body()
        logger.info(f"Raw request body: {raw_body.decode('utf-8')}")
        
        body = await request.json()
        logger.info(f"Parsed JSON body: {json.dumps(body, ensure_ascii=False)}")
        
        user_input = UserInput(**body)
        logger.info(f"Validated model: {user_input.dict()}")

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {str(e)}")
        raise HTTPException(status_code=422, detail="Invalid JSON format")
    except ValidationError as e:
        logger.error(f"模型验证失败: {e.errors()}")
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception as e:
        logger.exception("未捕获的异常:")
        raise HTTPException(status_code=500, detail="Internal server error")
    # 校验 token
    payload = decode_vaild(user_input.system_token, SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        raise HTTPException(status_code=401, detail="unionid不存在")
    conversation_id = user_input.conversation_id
    prompt = user_input.prompt

    # 更新 conversation 和插入用户输入
    await upsert_conversation(conversation_id, unionid, prompt)
    msg_id = await insert_user_input_chat(conversation_id, query=prompt)
    logger.info(f"Generated msg_id: {msg_id}")

    # 初始化停止事件
    stop_event = stop_events.setdefault(conversation_id, asyncio.Event())
    stop_event.clear()

    # 根据 conversation_id 从数据库查询所有文件
    uploaded_files = await db.execute(
        select(UploadedFile).where(
            UploadedFile.conversation_id == conversation_id,
            UploadedFile.file_status == True,
            UploadedFile.file_origin == 0 
        )
    )
    uploaded_files = uploaded_files.scalars().all()

    # 构造 file_list
    file_groups = []
    if uploaded_files:
        logger.info(f"Found {len(uploaded_files)} files for conversation_id: {conversation_id}")
        files = []
        for uploaded_file in uploaded_files:
            file_name, file_content = get_file_content(uploaded_file.file_path)
            if file_content:  # 检查内容是否非空
                logger.info(f"File: {file_name}, Content length: {len(file_content)}")
                files.append(FileInfo(file_name=file_name, file_content=file_content))
            else:
                logger.warning(f"Skipped file {file_name} due to empty content")
            logger.info(f"File: {file_name}, Content length: {len(file_content)}")
            files.append(FileInfo(file_name=file_name, file_content=file_content))
        if files:
            file_groups.append(FileGroup(conversation_id=conversation_id, files=files))
            logger.info(f"Files: {files}, file_groups: {file_groups}")
    else:
        logger.warning(f"No files found in DB for conversation_id: {conversation_id}")
    # 更新 user_input.file_list
    user_input.file_list = file_groups
    
    logger.info(f"Final file_list length: {len(file_groups)} for conversation_id: {conversation_id}")
    return StreamingResponse(
        proxy_stream_generator(user_input, msg_id, conversation_id, stop_event, stop_events),  
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )

# 获取文件内容
def get_file_content(file_path: str) -> tuple[str, str]:
    path = file_path.replace("minio://", "")
    bucket_name, object_name = path.split("/", 1)
    file_name = object_name  
    try:
        response = minio_client.get_object(bucket_name, object_name)
        file_content = response.read().decode("utf-8") 
    except Exception as e:
        logger.error(f"Error fetching file from MinIO: {e}")
        file_content = ""
    finally:
        response.close()
        response.release_conn()
    return file_name, file_content

@app.post("/backend/stop")
async def stop(request: Request):
    body = await request.body()
    try:
        data = json.loads(body.decode("utf-8"))
        system_token=data.get("system_token")
        conversation_id = data.get("conversation_id")
        if not system_token:
            raise HTTPException(status_code=422, detail="Missing 'system_token' field")
        if not conversation_id:
            raise HTTPException(status_code=422, detail="Missing 'conversation_id' field")
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON format")
    
    #检验token有效性    
    payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="unionid不存在",
    )
    # 设置停止事件
    if conversation_id in stop_events:
        stop_events[conversation_id].set()
    return {"status": "200"}

app.include_router(upload_router, prefix="/backend")

app.post("/query_user_info",tags=["用户数据"],summary="查询用户信息")(query_user_info)

app.post("/backend/delete_specific_session",tags=["会话数据"],summary="删除特定会话")(delete_specific_session)#

app.post("/backend/delete_sessions",tags=["会话数据"],summary="删除全部会话")(delete_sessions)

app.post("/backend/search_specific_session",tags=["会话数据"],summary="查询单一会话")(search_specific_session)

app.post("/backend/search_sessions",tags=["会话数据"],summary="查询会话历史")(search_sessions)

app.post("/insert_user_input",tags=["消息数据"],summary="插入单一会话内部-用户输入")(insert_user_input)

app.post("/backend/add_sessions",tags=["会话数据"],summary="新建会话记录信息")(add_sessions)

app.post("/backend/get_new_session_id",tags=["会话数据"],summary="返回会话id")(get_new_session_id)

app.post("/backend/update_session_name",tags=["会话数据"],summary="更改会话名称")(update_session_name)
