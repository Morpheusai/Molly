import httpx
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from utils import logger
from api.api import *

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


@app.get("/")
def read_root():
    return {"Hello": "我是Molly后端服务"}

@app.get("/wechat_callback")
async def wechat_callback(code: str, state: str):

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

    # 3. 入库存储用户, TODO

    return {
        "openid": token_data['openid'],
    }

app.post("/add_user",tags=["用户数据"],summary="添加用户")(add_user)

app.post("/query_user_info",tags=["用户数据"],summary="查询用户信息")(query_user_info)

app.post("/delete_specific_session",tags=["会话数据"],summary="删除特定会话")(delete_specific_session)

app.post("/delete_sessions",tags=["会话数据"],summary="查询用户信息")(delete_sessions)

# 补充