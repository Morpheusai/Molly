from fastapi import Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.mysql_db import *
from src.utils.mysql_db import search_sessions_sql
from src.utils.session import get_async_db
from src.utils.session import with_async_session
from .protocols import *


from src.demo.insert_guide_demo import insert_guide_demo

security = HTTPBearer()

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
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_async_db)
):
    return await delete_specific_session_sql(session,credentials,request)

#清空所有会话
async def delete_sessions(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_async_db)
):
   return await delete_sessions_sql(session,credentials)

#查询单一会话
async def search_specific_session(
        request: QuerySingleSessionRequest = Body(...),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_async_db)
):
    return await search_specific_session_sql(session,credentials,request)

#查询会话历史
async def search_sessions(
        # request: SessionsRequest = Body(...),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_async_db)
):
    return await search_sessions_sql(session,credentials)


#新建会话记录
async def add_sessions(
        session: AsyncSession = Depends(get_async_db),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        request: AddSessionRequest = Body(...)        
):
    return await add_sessions_sql(session,credentials,request)

#返回会话id
async def get_new_session_id(
        credentials: HTTPAuthorizationCredentials = Depends(security),
):
    return await get_new_session_id_sql(credentials)



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
        credentials: HTTPAuthorizationCredentials = Depends(security),
        request: UpdateSessionRequest = Body(...)        
):
    return await update_session_name_sql(session,credentials,request)

#插入demo示例
async def insert_demo_conversation(
        user_id: str
):
    return await insert_guide_demo(user_id)


# 使用 update 操作更新uploadfiles的file_type字段值
async def update_uploadfiles_file_type(
        file_paths: list[str],      
        conversation_id: str,
):
        return await update_uploadfiles_file_type_sql(file_paths,conversation_id)

# 
async def reset_conversation(
        session: AsyncSession = Depends(get_async_db),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        request: ResetConversationRequest = Body(...)
):
        return await reset_conversation_sql(session,credentials,request)