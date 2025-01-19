import httpx
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Response
from fastapi import HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from utils import logger
from utils.mysql_db import search_unionid_sql
from api.api import *
from fastapi.security import OAuth2PasswordBearer

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from src.db.user_token_model import UserToken
from datetime import datetime, timedelta, timezone



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
SECRET_KEY = "your-secret-key"  # 用于签名和验证 JWT 的密钥
ALGORITHM = "HS256"  # 加密算法
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # JWT Token 过期时间

# OAuth2密码Bearer令牌
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 生成 JWT Token,并添加到数据库中
with_async_session
async def create_system_token(session,unionid: str, wechat_access_token: str):
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": unionid, "exp": expire}
    system_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    db_token = UserToken(
        id=str(uuid.uuid4()),
        unionid=unionid,
        wechat_access_token=wechat_access_token,
        system_token=system_token,
        expires_at=expire,
        create_time=datetime.now()
    )
    session.add(db_token)
    session.commit()
    session.refresh(db_token)
    return system_token

# 解码并验证 JWT Token
def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
 # 获取当前用户记录   
async def get_current_user(token: str = Depends(oauth2_scheme),session:AsyncSession= Depends(get_async_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if unionid is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user_token = session.query(UserToken).filter(UserToken.unionid == unionid).first()
    if user_token is None:
        raise credentials_exception
    return user_token    

@app.get("/")
def read_root():
    return {"Hello": "我是Molly后端服务"}

@app.get("/wechat_callback")
async def wechat_callback(code: str, state: str,request: Response):

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
    user=search_unionid_sql(unionid=unionid)
    
    if not user:
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
            privilege=user_info.get("privilege")     # 用户特权信息（可选）
        )

        # 3. 入库存储用户
        add_user(request=add_user_request)

    # 生成自身系统的 JWT Token,并存入user_token表中
    access_token = await create_system_token(unionid=unionid,wechat_access_token=token_data['access_token'])

    # 将 JWT Token 存入 Cookie
    request.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Cookie 过期时间（秒）
        httponly=True,  # 确保前端只能通过 HTTP 请求访问
        secure=True,  # 如果是生产环境，可以设置为 True，确保安全
    )    
    return {
        "unionid": token_data['unionid'],
    }
# 受保护的路由
@app.get("/protected")
async def protected_route(current_user: UserToken = Depends(get_current_user)):
    return {"message": "You are authenticated", "openid": current_user.unionid}


# app.post("/add_user",tags=["用户数据"],summary="添加用户")(add_user)

app.post("/query_user_info",tags=["用户数据"],summary="查询用户信息")(query_user_info)

app.post("/delete_specific_session",tags=["会话数据"],summary="删除特定会话")(delete_specific_session)#

app.post("/delete_sessions",tags=["会话数据"],summary="删除全部会话")(delete_sessions)

app.post("/search_specific_session",tags=["会话数据"],summary="查询单一会话")(search_specific_session)

app.post("/search_sessions",tags=["会话数据"],summary="查询会话历史")(search_sessions)

app.post("/insert_user_input",tags=["消息数据"],summary="插入单一会话内部-用户输入")(insert_user_input)

app.post("/add_sessions",tags=["会话数据"],summary="新建会话记录信息")(add_sessions)

# 补充