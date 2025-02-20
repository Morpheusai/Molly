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
#from src.db.uploadfiles_model import UploadedFile
from src.model.openai_engine import proxy_stream_generator
from src.utils.jwt_util import create_system_token
from src.file.upload_router import router as upload_router
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

# # 附件存储目录
# UPLOAD_DIR = "./files/upload"


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
    print(".........................")
    print(user)
    print(".........................")
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


    # print(".........................")
    # print( {
    #     "system_token":system_token,
    #     "unionid": user_info.get("unionid"),
    #     "headimgurl":user_info.get("headimgurl"),
    #     "nickname":user_info.get("nickname")
    # })
    # print(".........................")
    #TODO Userinfo_图片和昵称和system_token和unid
    # 返回成功响应
    return {
        "ok": "0",
        "failed":"",
        "system_token": system_token,
        "unionid": user_info.get("unionid"),
        "headimgurl": user_info.get("headimgurl"),
        "nickname": user_info.get("nickname")
    }

#TODO dic{code：401,statu：用户状态失效}
#TODO 200
# app.post("/add_user",tags=["用户数据"],summary="添加用户")(add_user)

# 存储每个会话的停止事件
stop_events: Dict[str, asyncio.Event] = {}

# @app.post("/backend/chat")
# async def chat(request: Request):
#     """
#     流式聊天接口
#     :param request: 原始请求对象
#     :return: StreamingResponse
#     """
#     # 读取请求体
#     body = await request.body()
#     try:
#         # 解析请求体为 JSON
#         data = json.loads(body.decode("utf-8"))
#         prompt = data.get("prompt")
#         system_token=data.get("system_token")
#         conversation_id=data.get("conversation_id")
#         if not prompt:
#             raise HTTPException(status_code=422, detail="Missing 'prompt' field")
#         if not system_token:
#             raise HTTPException(status_code=422, detail="Missing 'system_token' field")
#         if not conversation_id:
#             raise HTTPException(status_code=422, detail="Missing 'conversation_id' field")        
#     except json.JSONDecodeError:
#         raise HTTPException(status_code=422, detail="Invalid JSON format")
    
#     #检验token有效性    
#     payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
#     unionid: str = payload.get("sub")
#     if unionid is None:
#         raise HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="unionid不存在",
#     )

#     # 使用 UPSERT 操作更新或插入 conversation 记录
#     await upsert_conversation(conversation_id, unionid, prompt)

#     #将人类的输入插入数据库,并获取消息id
#     msg_id=await insert_user_input_chat(conversation_id, query=prompt)

#     # 初始化停止事件
#     stop_event = stop_events.setdefault(conversation_id, asyncio.Event())
#     stop_event.clear()

#     # 用于存储 AI 的完整回复
#     full_response = ""

#     # 将数据包装为 SSE 格式
#     async def generate_sse():
#         nonlocal full_response
#         try:
#             async for chunk in deepseek_model.generate_stream(prompt):
#                 #判断是否停止
#                 if stop_event.is_set():
#                     break
#                 # 将 chunk 拼接到 full_response 中
#                 full_response += chunk
#                 # 每条消息以 "data:" 开头，并以两个换行符结尾
#                 yield f"data: {chunk}\n\n"
#             # 流式处理完成后，将完整的 AI 回复插入数据库
#             await insert_ai_input_sql(msg_id=msg_id,response=full_response)
#         finally:
#             if conversation_id in stop_events:
#                 del stop_events[conversation_id]            

#     return StreamingResponse(
#         generate_sse(),  # 使用包装后的生成器
#         media_type="text/event-stream",  # 设置正确的 media_type
#         headers={"Content-Type": "text/event-stream; charset=UTF-8"}  # 显式设置字符集
# )
@app.post("/backend/chat")
async def backend_chat(request: Request) -> StreamingResponse:
    """
    代理聊天接口，流式转发到目标服务器
    """
    try:
        # 手动解析请求体
        raw_body = await request.body()
        logger.info(f"Raw request body: {raw_body.decode('utf-8')}")  # 关键日志1：原始字节数据
        
        # 转换为JSON并记录
        body = await request.json()
        logger.info(f"Parsed JSON body: {json.dumps(body, ensure_ascii=False)}")  # 关键日志2：结构化数据
        
        # 手动验证模型
        user_input = UserInput(**body)
        logger.info(f"Validated model: {user_input.dict()}")  # 关键日志3：验证后的模型数据
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {str(e)}")
        raise HTTPException(status_code=422, detail="Invalid JSON format")
        
    except ValidationError as e:
        logger.error(f"模型验证失败: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors(),
        )
        
    except Exception as e:
        logger.exception("未捕获的异常:")  # 记录完整堆栈
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
    
    #检验token有效性    
    payload = decode_vaild(user_input.system_token, SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="unionid不存在",
    )

    conversation_id=user_input.conversation_id
    prompt=user_input.prompt
    
    # 使用 UPSERT 操作更新或插入 conversation 记录
    await upsert_conversation(conversation_id, unionid, prompt)

    #将人类的输入插入数据库,并获取消息id
    msg_id=await insert_user_input_chat(conversation_id, query=prompt)
    print(msg_id)
    return StreamingResponse(
        proxy_stream_generator(user_input,msg_id),  # 直接调用函数，传入参数
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )



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

# 补充