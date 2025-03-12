from src.utils.mysql_db import *
from src.utils.mysql_db import search_sessions_sql
import copy
import logging
from typing import List
from src.utils.session import get_async_db
from src.utils.session import with_async_session
from fastapi import BackgroundTasks
from src.config import g_config
from .protocols import *
from src.constants import CodeAgentState

from fastapi import HTTPException, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.user_model import UserModel

from datetime import datetime

from src.demo.insert_example import insert_demo
#用户注册
async def add_user(
        request: AddUserRequest = None,
):
    return await add_user_sql(request)

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
        request: DelAllSessionsRequest = Body(...),
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
@with_async_session
async def insert_ai_input(
        session,
        request: InsertAIInputSessionRequest = None
              
):
    return await insert_ai_input_sql(session,request)

#新建会话记录
async def add_sessions(
        session: AsyncSession = Depends(get_async_db),
        request: AddSessionRequest = Body(...)        
):
    return await add_sessions_sql(session,request)

#返回会话id
async def get_new_session_id(
        session: AsyncSession = Depends(get_async_db),
        request: AddSessionRequest = Body(...)        
):
    return await get_new_session_id_sql(session,request)



# 使用 UPSERT 操作更新或插入 conversation 记录
async def upsert_conversation(
        conversation_id: str,      
        unionid: str,
        prompt:str
):
    return await upsert_conversation_sql(conversation_id, unionid,prompt)

#更改会话名称
async def update_session_name(
        session: AsyncSession = Depends(get_async_db),
        request: UpdateSessionRequest = Body(...)        
):
    return await update_session_name_sql(session,request)

#插入demo示例
async def insert_demo_conversation(
        user_id: str
):
    return await insert_demo(user_id)




