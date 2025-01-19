from db.user_model import UserModel
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from fastapi import HTTPException, Depends, Body
from sqlalchemy.exc import IntegrityError
from api.protocols import *
from db.conversation_model import ConversationModel
from db.message_model import MessageModel
from utils.session import with_async_session
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from sqlalchemy import delete
import uuid
from datetime import datetime
from fastapi import Response
from fastapi.responses import JSONResponse
from typing import List
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from utils.session import get_async_db
from sqlalchemy import desc
from fastapi import HTTPException

#查询unionid的记录
with_async_session
async def search_unionid_sql(session,  unionid: str = None):
    result = await session.execute(select(UserModel).where(UserModel.unionid == unionid))
    user = result.scalars().first()
    return user
#添加用户记录sql
with_async_session
async def add_user_sql(session,  request: AddUserRequest = None):
    try:
        user = UserModel(
        unionid=request.unionid,
        openid=request.openid,
        nickname=request.nickname,
        sex=request.sex,
        province=request.province,
        city=request.city,
        country=request.country,
        headimgurl=request.headimgurl,
        privilege=request.privilege,
        create_time=datetime.now(),
    )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        return BaseResponse(
            ok=0,
            failed=""
        )
    except Exception as e:
        await session.rollback()
        return BaseResponse(
            ok=1,
            failed=str(e)
        )

#查询用户信息sql
async def query_user_info_sql(session:AsyncSession= Depends(get_async_db),  request: QueryUserInfoRequest = Body(...)):
    try:
        user = await session.execute(select(UserModel).where(UserModel.unionid == request.unionid))
        user = user.scalar_one_or_none()
        return QueryUserInfoResponse(
        unionid=user.unionid,
        openid=user.openid,
        nickname=user.nickname,
        sex=user.sex,
        province=user.province,
        city=user.city,
        country=user.country,
        headimgurl=user.headimgurl,
        privilege=user.privilege,
        )
    except Exception as e:
        await session.rollback()
        return BaseResponse(
            ok=1,
            failed=str(e)
        )


#删除单一会话sql
async def delete_specific_session_sql(
        session: AsyncSession = Depends(get_async_db),
        request: DeleteSessionRequest = Body(...),
):
    async with session.begin():
        # 检查是否存在指定的会话
        conversation = await session.get(ConversationModel, request.session_id)
        if not conversation:
            # 如果会话不存在，返回404错误
            raise Exception("Conversation not found")    
    try:
        # 删除与会话关联的所有消息
        await session.execute(
            delete(MessageModel).where(MessageModel.conversation_id == request.session_id)
        )        
        await session.delete(conversation)

        # 提交事务
        await session.commit()
        
        return BaseResponse(
            ok=0,
            failed=""
        )
    except Exception as e:
        await session.rollback()
        return BaseResponse(
            ok=1,
            failed=str(e)
        )

#清空所有会话sql
async def delete_sessions_sql(
    session: AsyncSession = Depends(get_async_db),
    request: SessionsRequest = Body(...)
):
    try:
        async with session.begin():
            # 查询该用户的所有会话 ID
            result = await session.execute(
                select(ConversationModel.id).where(
                    ConversationModel.user_id == request.user_id
                )
            )
            session_ids = result.scalars().all()

            if not session_ids:
                # 如果该用户没有会话，直接返回成功
                return BaseResponse(
                    ok=0,
                    failed=""
                )

            # 删除所有会话关联的消息
            await session.execute(
                delete(MessageModel).where(
                    MessageModel.conversation_id.in_(session_ids)
                )
            )

            # 删除所有会话
            await session.execute(
                delete(ConversationModel).where(
                    ConversationModel.user_id == request.user_id
                )
            )

            return BaseResponse(
                ok=0,
                failed=""
            )
    except Exception as e:
        await session.rollback()
        return BaseResponse(
            ok=1,
            failed=str(e)
        )

#查询单一会话历史sql
async def search_specific_session_sql(
    session: AsyncSession = Depends(get_async_db),
    request: QuerySingleSessionRequest = Body(...)
):
    """
    查询单一会话历史的逻辑
    """
    try:
        # 查询会话记录，按创建时间从后往前排序
        result = await session.execute(
            select(MessageModel)
            .where(
                MessageModel.conversation_id == request.session_id,
                
            )
            .order_by(desc(MessageModel.create_time))  # 按创建时间倒序排列
        )
        session_data = result.scalars().all()

        if not session_data:
            return QuerySessionResponse(
                user_id=request.user_id,
                session_id=request.session_id,
                ok=1,
                failed="Session not found",
                chats=[]
            )

        # 构建聊天记录
        chats = []
        for record in session_data:
            chats.append(ChatItem(query=record.query, response=record.response))

        return QuerySessionResponse(
            user_id=request.user_id,
            session_id=request.session_id,
            ok=0,
            failed="",
            chats=chats
        )
    except Exception as e:
        return QuerySessionResponse(
            user_id=request.user_id,
            session_id=request.session_id,
            ok=1,
            failed=str(e),
            chats=[]
        )


#查询会话历史sql
async def search_sessions_sql(
    session: AsyncSession = Depends(get_async_db),
    request: SessionsRequest = Body(...)
):
    """
    查询会话列表的逻辑
    """
    try:
        # 查询该用户的所有会话记录
        result = await session.execute(
            select(ConversationModel).where(
                ConversationModel.user_id == request.user_id
            )
        )
        session_data = result.scalars().all()

        # 构建会话列表
        sessions = []
        for record in session_data:
            sessions.append(SessionItem(
                session_id=record.id,
                session_title=record.session_title
            ))

        return QuerySessionsResponse(
            ok=0,
            failed="",
            sessions=sessions
        )
    except Exception as e:
        return QuerySessionsResponse(
            ok=1,
            failed=str(e),
            sessions=[]
        )

#插入单一会话内部-用户输入sql
async def insert_user_input_sql(
        session: AsyncSession = Depends(get_async_db),
        request: InsertUserInputSessionRequest = Body(...)
):

    try:
        msg = MessageModel(
        id=str(uuid.uuid4()),
        conversation_id=request.id,
        query=request.query,
        response=request.response,
        meta_data=request.meta_data,
        feedback_score=request.feedback_score,
        feedback_reason=request.feedback_reason,
        create_time=datetime.now(),
        )    
        # 添加到数据库会话
        session.add(msg)
        # 提交到数据库
        await session.commit()
        # 刷新以获取数据库分配的 ID 等字段
        await session.refresh(msg)
        return BaseResponse(
            ok=0,
            failed=""
        )
    except Exception as e:
        await session.rollback()
        return BaseResponse(
            ok=1,
            failed=str(e)
        )
    
#插入单一会话内部-AI回复sql
@with_async_session
async def insert_ai_input_sql(
        session,
        request: InsertAIInputSessionRequest = None      
):
    try:
        result = await session.execute(select(MessageModel).filter_by(id=request.id))
        m=result.scalars().first()
        if m is not None:
            if request.response is not None:
                m.response = request.response
            session.add(m)    
            await session.commit()
        return BaseResponse(
            ok=0,
            failed=""
        )
    except Exception as e:
        await session.rollback()
        return BaseResponse(
            ok=1,
            failed=str(e)
        )




#新建会话记录sql
async def add_sessions_sql(
        session: AsyncSession = Depends(get_async_db),
        request: AddSessionRequest = Body(...)        
):
    try:
        msg = ConversationModel(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        session_title=request.session_title,
        chat_type=request.chat_type,
        create_time=datetime.now(),
        )    
        # 添加到数据库会话
        session.add(msg)
        # 提交到数据库
        await session.commit()
        # 刷新以获取数据库分配的 ID 等字段
        await session.refresh(msg)
        return BaseResponse(
            ok=0,
            failed=""
        )
    except Exception as e:
        await session.rollback()
        return BaseResponse(
            ok=1,
            failed=str(e)
            )
















