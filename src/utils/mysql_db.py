from src.db.user_model import UserModel
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from fastapi import HTTPException, Depends, Body, status
from sqlalchemy.exc import IntegrityError
from src.api.protocols import *
from src.db.conversation_model import ConversationModel
from src.db.message_model import MessageModel
from src.db.uploadfiles_model import UploadedFile
from src.db.tool_msg_model import ToolModel
from src.db.tool_files_model import ToolFileModel
from src.utils.session import with_async_session
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.dialects.mysql import insert  # 正确导入 MySQL 的 insert 模块
import uuid
from datetime import datetime
from fastapi import Response
from fastapi.responses import JSONResponse
from typing import List
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.utils.session import get_async_db
from sqlalchemy import desc
from fastapi import HTTPException
from jose import JWTError, jwt
from src.utils.jwt_util import decode_vaild
import os
import json
import ast
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "") # 用于签名和验证 JWT 的密钥
ALGORITHM = os.getenv("ALGORITHM", "HS256") # 加密算法

#查询unionid的记录
@with_async_session
async def search_unionid_sql(session,  unionid: str = None):
    result = await session.execute(select(UserModel).where(UserModel.unionid == unionid))
    user = result.scalars().first()
    return user

#添加用户记录sql
@with_async_session
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
        phone=request.phone,
        email=request.email,
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
    """
    删除特定会话
    :param session: 异步数据库会话
    :param request: 删除会话的请求模型
    :return: BaseResponse
    """
    #检验token有效性    
    payload = decode_vaild(request.system_token, SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="unionid不存在",
    )
    async with session.begin():
        # 检查是否存在指定的会话，并且会话属于当前用户
        result = await session.execute(
            select(ConversationModel)
            .where(ConversationModel.id == request.session_id)
            .where(ConversationModel.user_id == unionid)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            # 如果会话不存在或不属于当前用户，返回404错误
            return BaseResponse(
                ok=1,
                failed="Conversation not found or does not belong to the user"
            )

    try:
        # 删除与会话关联的所有工具
        await session.execute(
            delete(ToolModel)
            .where(ToolModel.conversation_id == request.session_id)
        )      

        # 删除与会话关联的所有消息
        await session.execute(
            delete(MessageModel)
            .where(MessageModel.conversation_id == request.session_id)
        )

        #删除于会话关联的上传文件信息
        await session.execute(
            delete(UploadedFile)
            .where(UploadedFile.conversation_id == request.session_id)
        )

  

        # 删除会话
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
    request: DelAllSessionsRequest = Body(...)
):
    #检验token有效性    
    payload = decode_vaild(request.system_token, SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="unionid不存在",
    )    
    try:
        async with session.begin():
            # 查询该用户的所有会话 ID
            result = await session.execute(
                select(ConversationModel.id).where(
                    ConversationModel.user_id == unionid
                )
            )
            session_ids = result.scalars().all()

            if not session_ids:
                # 如果该用户没有会话，直接返回成功
                return BaseResponse(
                    ok=0,
                    failed=""
                )
            
            # 删除所有会话关联的工具
            await session.execute(
                delete(ToolModel).where(
                    ToolModel.conversation_id.in_(session_ids)
                )
            )

            # 删除所有会话关联的消息
            await session.execute(
                delete(MessageModel).where(
                    MessageModel.conversation_id.in_(session_ids)
                )
            )
            # 删除所有会话关联的文件
            await session.execute(
                delete(UploadedFile).where(
                    UploadedFile.conversation_id.in_(session_ids)
                )
            )

            # 删除所有会话
            await session.execute(
                delete(ConversationModel).where(
                    ConversationModel.user_id == unionid
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
    # 检验token有效性    
    payload = decode_vaild(request.system_token, SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unionid不存在",
        )

    try:
        # 查询Conversation以获取session_title并验证会话存在性和权限
        conversation_query = select(ConversationModel).where(ConversationModel.id == request.session_id)
        conversation_result = await session.execute(conversation_query)
        conversation = conversation_result.scalars().first()

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        # 查询会话历史消息
        message_query = (
            select(MessageModel)
            .where(MessageModel.conversation_id == request.session_id)
            .options(selectinload(MessageModel.tools))  # 加载关联工具
            .order_by(desc(MessageModel.create_time))
        )
        message_result = await session.execute(message_query)
        message_data = message_result.scalars().unique().all()

        # 查询会话关联的文件
        file_query = (
            select(UploadedFile)
            .where(UploadedFile.conversation_id == request.session_id)
            .order_by(desc(UploadedFile.create_time))
        )
        file_result = await session.execute(file_query)
        file_data = file_result.scalars().unique().all()

        # 如果没有消息和文件，返回空结果
        if not message_data and not file_data:
            return QuerySessionResponse(
                ok=1,
                failed="No data found",
                session_id=request.session_id,
                session_title=None,
                chats=[],
                files=[]
            )

        # 构建带工具信息的响应
        chats = []
        for message in message_data:
            # 处理工具信息（自动按 create_time 排序）
            tools = [
                ToolItem(
                    tool_name=tool.tool_name,
                    tool_args=tool.tool_args,
                    tool_result=tool.tool_result,
                    create_time=tool.create_time.strftime('%Y-%m-%d %H:%M:%S')
                )
                for tool in sorted(message.tools, key=lambda x: x.create_time)  # 双重排序保障
            ]

            print("............111111")
            print(tools)
            # print(f"Tools for message ID {message.id}:")
            # for tool in tools:
            #     print(f"  - Tool Name: {tool.tool_name}")
            #     print(f"    Tool Args: {tool.tool_args}")
            #     print(f"    Tool Result: {tool.tool_result}")
            #     print(f"    Create Time: {tool.create_time}")    

            chats.append(ChatItemWithTools(
                id=message.id,
                query=message.query,
                response=message.response,
                create_time=message.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                tools=tools
            ))

        # 构建文件信息响应
        files = [
            FileItem(
                file_name=file.file_name,
                file_path=file.file_path,
                file_desc=file.file_desc
            )
            for file in file_data
        ]

        return QuerySessionResponse(
            ok=0,
            failed="",
            session_id=request.session_id,
            session_title=conversation.session_title,
            chats=chats,
            files=files  # 添加文件信息
        )

    except Exception as e:
        print(e)
        return QuerySessionResponse(
            ok=1,
            failed=str(e),
            session_id=request.session_id,
            session_title=None,
            chats=[],
            files=[]
        )


#查询会话历史sql
async def search_sessions_sql(
    session: AsyncSession = Depends(get_async_db),
    request: SessionsRequest = Body(...)
):
    #检验token有效性    
    payload = decode_vaild(request.system_token, SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="unionid不存在",
    )
    #查询会话列表的逻辑
    try:
        # 查询该用户的所有会话记录
        result = await session.execute(
            select(ConversationModel).where(
                ConversationModel.user_id == unionid
            )
            .order_by(desc(ConversationModel.updata_time))

        )
        session_data = result.scalars().all()
        # 判断 session_data 是否为空
        if not session_data:
            return QuerySessionsResponse(
                ok=2,
                failed="会话记录为空",
                sessions=[]
            )        

        # 构建会话列表
        sessions = []
        
        for record in session_data:
            # 格式化时间为 YYYY-MM-DD HH:MM:SS
            formatted_update_time = record.updata_time.strftime("%Y-%m-%d %H:%M:%S")
            formatted_create_time = record.create_time.strftime("%Y-%m-%d %H:%M:%S")
            sessions.append(SessionItem(
                session_id=record.id,
                session_title=record.session_title,
                updata_time=formatted_update_time,
                create_time=formatted_create_time
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
    
#chat路由插入单一会话内部-用户输入sql
@with_async_session
async def insert_user_input_chat(
        session,
        conversation_id:str,
        query:str
):

    try:
        msg = MessageModel(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        query=query,
        response=None,
        meta_data=None,
        feedback_score=None,
        feedback_reason=None,
        create_time=datetime.now(),
        )    
        # 添加到数据库会话
        session.add(msg)
        # 提交到数据库
        await session.commit()
        # 刷新以获取数据库分配的 ID 等字段
        await session.refresh(msg)
        return msg.id
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
        msg_id:str,
        response:str,
):
    try:
        result = await session.execute(select(MessageModel).filter_by(id=msg_id))
        m=result.scalars().first()
        if m is not None:
            if response is not None:
                m.response = response
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
    #检验token有效性    
    payload = decode_vaild(request.system_token, SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="unionid不存在",
    )    
    try:
        msg = ConversationModel(
        id=str(uuid.uuid4()),
        user_id=unionid,
        session_title=request.session_title,
        chat_type=request.chat_type,
        updata_time=datetime.now(),
        create_time=datetime.now(),
        )
        # 添加到数据库会话
        session.add(msg)
        # 提交到数据库
        await session.commit()
        # 刷新以获取数据库分配的 ID 等字段
        await session.refresh(msg)
        return SessionResponse(
            ok=0,
            failed="",
            conversation_id=msg.id
        )
    except Exception as e:
        await session.rollback()
        return BaseResponse(
            ok=1,
            failed=str(e)
            )



#返回会话id
async def get_new_session_id_sql(
        session: AsyncSession = Depends(get_async_db),
        request: AddSessionRequest = Body(...)        
):
    #检验token有效性    
    payload = decode_vaild(request.system_token, SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="unionid不存在",
    )    
    try:
        id=str(uuid.uuid4())
        return SessionResponse(
            ok=0,
            failed="",
            conversation_id=id
        )
    except Exception as e:
        return BaseResponse(
            ok=1,
            failed=str(e)
            )


@with_async_session
# 使用 UPSERT 操作更新或插入 conversation 记录
async def upsert_conversation_sql(session,conversation_id: str, unionid: str, prompt:str):
    try:
    # 构建 UPSERT 语句
        stmt = (
            insert(ConversationModel)
            .values(
                id=conversation_id,
                user_id=unionid,
                session_title=prompt,  # 设置会话标题
                chat_type=None,  # 设置聊天类型为 None
                updata_time=datetime.now(),  # 设置更新时间
                create_time=datetime.now(),  # 设置创建时间
            )
            .on_duplicate_key_update(  # 使用 MySQL 的 ON DUPLICATE KEY UPDATE 语法
                updata_time=datetime.now(),  # 冲突时更新的字段
            )
        )
        await session.execute(stmt)
        return conversation_id
    except Exception as e:
        # 捕获异常并回滚事务
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库操作失败: {str(e)}",
        )        


async def update_session_name_sql(
        session: AsyncSession = Depends(get_async_db),
        request: UpdateSessionRequest = Body(...)        
):
    #检验token有效性    
    payload = decode_vaild(request.system_token, SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="unionid不存在",
    )    
    try:
        # 检查会话是否存在且属于当前用户
        result = await session.execute(
            select(ConversationModel)
            .where(ConversationModel.id == request.session_id)
            .where(ConversationModel.user_id == unionid)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            # 如果会话不存在或不属于当前用户，返回错误
            return BaseResponse(
                ok=1,
                failed="会话不存在或不属于当前用户"
            )

        # 直接通过对象修改会话名称
        conversation.session_title = request.session_title
        conversation.updata_time = datetime.now()  # 更新修改时间

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

@with_async_session
async def process_messages(
    session,
    msg_id: str,
    conversation_id: str,
    ai_messages: List[Dict],
    tool_messages: List[Dict],
    full_response:str
):

    # 第一步：更新 message 表的 response 字段
    final_ai_content = ""

    # 找到最后一个有内容的 AI 消息
    # for ai_msg in ai_messages:
    #     content = ai_msg.get("content", {})
    #     if content.get("content"):
    #         final_ai_content = content.get("content")
    #         break
    # ai_msg=ai_messages[-1]
    # content = ai_msg.get("content", {})   
    # if content.get("content"): 
    #     final_ai_content = content.get("content")

    # 更新 message 表的 response 字段
    try:
        result = await session.execute(select(MessageModel).filter_by(id=msg_id))
        m=result.scalars().first()
        if m is not None:
            m.response = full_response
            session.add(m)
            await session.commit()
    except Exception as e:
        await session.rollback()
        return BaseResponse(
            ok=1,
            failed=str(e)
        )    

    # 第二步：处理 Tool 消息
    tool_calls_map = {}

    # 收集所有 AI 消息中的 tool_calls
    for ai_msg in ai_messages:
        content = ai_msg.get("content", {})
        for tool_call in content.get("tool_calls", []):
            tool_calls_map[tool_call["id"]] = {
                "name": tool_call["name"],
                "args": tool_call["args"]
            }

    # 批量插入 Tool 数据
    tool_models = []
    #批量插入Tool_files数据
    tool_files = []
    for tool_msg in tool_messages:
        print(tool_msg['content']['content']) 
        # 解析 content 字段中的 JSON 字符串
        content_dict = json.loads(tool_msg['content']['content'])
        if 'url' in content_dict:
            # 原始字符串
            url = content_dict['url']
            tool_llm_content = content_dict['content']
            # 提取 minio:// 和 / 之间的值
            prefix = "minio://"
            start_index = len(prefix)  # 跳过 minio://
            end_index = url.find("/", start_index)  # 找到第一个 / 的位置
            # 提取目标值
            target_value = url[start_index:end_index]

            # 判断是否等于 netmhcpan-results
            if target_value == "netmhcpan-results":
                tool_files.append(
                    ToolFileModel(
                        id = str(uuid.uuid4()),
                        tool_id = "acfe6b85-f651-11ef-a368-00163e1ab54a",
                        file_url = url,
                        tool_llm_content = tool_llm_content
                    )
                )
            else:
                pass

        content = tool_msg.get("content", {})
        tool_call_id = content.get("tool_call_id")
        if tool_call_id in tool_calls_map:
            tool_info = tool_calls_map[tool_call_id]
            new_id = str(uuid.uuid4())
            # 获取当前时间
            current_time = datetime.now()  

            # # 解析 tool_result
            # tool_result_str = content.get('content', '')
            # try:
            #     tool_result_dict = ast.literal_eval(tool_result_str)
            #     print(tool_result_dict)
            # except (SyntaxError, ValueError) as e:
            #     print(f"解析 tool_result 失败: {e}")
            #     tool_result_dict = {}  # 如果解析失败，设置为空字典    
            # print("ID:", new_id)
            # print("Message ID:", msg_id)  # 关联到 message 表的 ID
            # print("Conversation ID:", conversation_id)
            # print("Tool ID:", tool_call_id)
            # print("Tool Name:", tool_info["name"])
            # print("Tool Args:", json.dumps(tool_info["args"]))  # 将 args 转为 JSON 字符串
            # print("Tool Result:", content.get('content', "")) 
            #  # 当前工具返回的是一个json，text/link
            # print(".....................")
            # print("Tool Result:", json.dumps(content.get('content', "")))
            # print("Create Time:", current_time) 
            tool_models.append(
                ToolModel(
                    id=new_id,
                    message_id=msg_id,  # 关联到 message 表的 ID
                    conversation_id=conversation_id,
                    tool_id=tool_call_id,
                    tool_name=tool_info["name"],
                    tool_args=json.dumps(tool_info["args"]),  # 将 args 转为 JSON 字符串
                    #tool_result=content.get('content', ''), #当前工具返回的是一个json，text/link
                    tool_result=content.get('content', ""), 
                    create_time=current_time,
                )
            )
        
    # 批量插入工具数据
    if tool_models:
        try:
            session.add_all(tool_models)
            await session.commit()
        except Exception as e:
            await session.rollback()
            return BaseResponse(
                ok=1,
                failed=str(e)
            )   
        
    # 批量插入Tool_files数据    
    if tool_files:
        try:
            session.add_all(tool_files)
            await session.commit()
        except Exception as e:
            await session.rollback()
            return BaseResponse(
                ok=1,
                failed=str(e)
            ) 