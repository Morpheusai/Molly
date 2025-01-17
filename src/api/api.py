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

#用户注册
async def add_user(
        request: AddUserRequest = Body(...),
        session: AsyncSession = Depends(get_async_db)
):
    return await add_user_sql(session,request)

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

    return await insert_user_input_sql(session,request)

#后端接口，没有放在路由上
#插入单一会话内部-AI回复
async def insert_ai_input(
        request: InsertAIInputSessionRequest = Body(...),
        session: AsyncSession = Depends(get_async_db)        
):
    return await insert_ai_input_sql(session,request)

#新建会话记录
async def add_sessions(
        session: AsyncSession = Depends(get_async_db),
        request: AddSessionRequest = Body(...)        
):
    return await add_sessions_sql(session,request)