from utils.mysql_db import *
import copy
import logging
from typing import List
from utils.session import get_async_db
from utils.session import with_async_session
from fastapi import BackgroundTasks
from config import g_config
from .protocols import *
from constants import CodeAgentState

from fastapi import HTTPException, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from db.user_model import UserModel
import uuid
from datetime import datetime

#添加用户
async def add_user(
        request: AddUserRequest = Body(...),
        session: AsyncSession = Depends(get_async_db)
):
    """
    用户注册逻辑
    """
    print(f"request: {request}")

    user = UserModel(
        id=str(uuid.uuid4()),
        request_id=request.request_id,
        user_id=request.user_id,
        user_name=request.user_name,
        email=request.email,
        phone=request.phone,
        create_time=datetime.now(),
    )
    return await add_user_sql(user,session,request)

#查询用户信息
async def query_user_info(
        request: QueryUserInfoRequest = Body(...),
        session: AsyncSession = Depends(get_async_db)
):
    return await query_user_info_sql(session,request)

#删除单一会话
async def delete_specific_session(
        request: DeleteSessionRequest = Body(...),
        session: AsyncSession = Depends(get_async_db)
):
    return await delete_specific_session_sql(session,request)
#清空所有会话
async def delete_sessions(
        request: SessionsRequest = Body(...),
        session: AsyncSession = Depends(get_async_db)
):
   return await delete_sessions_sql(session,request)

#查询单一会话
async def search_specific_session(
        request: QuerySingleSessionRequest = Body(...),
        session: AsyncSession = Depends(get_async_db)
):
    return await search_specific_session_sql(session,request)

#查询会话历史
async def search_sessions(
        request: SessionsRequest = Body(...),
        session: AsyncSession = Depends(get_async_db)
):
    return await search_sessions_sql(session,request)


#插入单一会话内部-用户输入
async def insert_user_input(
        request: InsertUserInputSessionRequest = Body(...),
        session: AsyncSession = Depends(get_async_db)
):
    msg = MessageModel(
        id=str(uuid.uuid4()),
        conversation_id=request.id,
        query=request.query,
        response="",
        create_time=datetime.now(),
    )    
    return await insert_user_input_sql(msg,session,request)

#后端接口，没有放在路由上
#插入单一会话内部-AI回复
async def insert_ai_input(
        request: InsertAIInputSessionRequest = Body(...),
        session: AsyncSession = Depends(get_async_db)        
):
    return await insert_ai_input_sql(session,request)

#查询微信用户信息
async def search_wx_info(
        request: UserInfoRequest = Body(...),
        session: AsyncSession = Depends(get_async_db)        
):
    return await search_wx_info_sql(session,request)