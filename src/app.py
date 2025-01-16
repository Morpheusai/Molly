from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils import logger
from api.api import  *

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

@app.get("/")
def read_root():
    return {"Hello": "我是Molly后端服务"}

app.post("/login", tags=["登录"], summary="生成代码")(user_login)

app.post("/logout",tags=["登录"],summary="获取默认训练参数")(user_logout)

app.post("/add_user",tags=["用户数据"],summary="添加用户")(add_user)

app.post("/query_user_info",tags=["用户数据"],summary="查询用户信息")(query_user_info)

app.post("/delete_specific_session",tags=["会话数据"],summary="删除特定会话")(delete_specific_session)

app.post("/delete_sessions",tags=["会话数据"],summary="查询用户信息")(delete_sessions)

#补充