import json
import os
import uuid
from datetime import datetime, timedelta
from typing import List

from dotenv import load_dotenv
from fastapi import (
    Body,
    Depends,
    HTTPException,
    status
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import delete, desc, update
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.api.protocols import *
from src.db.conversation_model import ConversationModel
from src.db.message_model import MessageModel
from src.db.tool_files_model import ToolFileModel
from src.db.tool_msg_model import ToolModel
from src.db.uploadfiles_model import UploadedFile
from src.db.user_model import UserModel
from src.utils.jwt_util import decode_vaild
from src.utils.session import get_async_db, with_async_session
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "")  # 用于签名和验证 JWT 的密钥
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # 加密算法

# 查询unionid的记录
@with_async_session
async def search_unionid_sql(session,  unionid: str = None):
    result = await session.execute(select(UserModel).where(UserModel.unionid == unionid))
    user = result.scalars().first()
    return user

# 添加用户记录sql
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

# 查询用户信息sql
async def query_user_info_sql(session: AsyncSession = Depends(get_async_db),  request: QueryUserInfoRequest = Body(...)):
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

# 删除单一会话sql
async def delete_specific_session_sql(
    session: AsyncSession,
    credentials: HTTPAuthorizationCredentials,
    request: DeleteSessionRequest,
):
    """
    删除特定会话
    :param session: 异步数据库会话
    :param request: 删除会话的请求模型
    :return: BaseResponse
    """
    # 提取并校验 token
    system_token = credentials.credentials  # 直接获取Token
    payload = decode_vaild(system_token,
                           SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        return {
            "ok": 1,
            "failed": "unionid不存在"
        }    
    async with session.begin():
        # 检查是否存在指定的会话，并且会话属于当前用户
        result = await session.execute(
            select(ConversationModel)
            .where(ConversationModel.id == request.conversation_id)
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
            .where(ToolModel.conversation_id == request.conversation_id)
        )

        # 删除与会话关联的所有消息
        await session.execute(
            delete(MessageModel)
            .where(MessageModel.conversation_id == request.conversation_id)
        )

        # 删除于会话关联的上传文件信息
        await session.execute(
            delete(UploadedFile)
            .where(UploadedFile.conversation_id == request.conversation_id)
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

# 清空所有会话sql
async def delete_sessions_sql(
    session: AsyncSession,
    credentials: HTTPAuthorizationCredentials
):
    # 提取并校验 token
    system_token = credentials.credentials  # 直接获取Token
    payload = decode_vaild(system_token,
                           SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        return {
            "ok": 1,
            "failed": "unionid不存在"
        }    
    try:
        async with session.begin():
            # 查询该用户的所有会话 ID
            result = await session.execute(
                select(ConversationModel.id).where(
                    ConversationModel.user_id == unionid,
                    ConversationModel.chat_type != 'demo'
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
                    ConversationModel.user_id == unionid,
                    ConversationModel.chat_type != 'demo'
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

# 查询单一会话历史sql
async def search_specific_session_sql(
    session: AsyncSession,
    credentials: HTTPAuthorizationCredentials,
    request: QuerySingleSessionRequest
):
    """
    查询单一会话历史的逻辑
    """

    # 提取并校验 token
    system_token = credentials.credentials  # 直接获取Token
    payload = decode_vaild(system_token,
                           SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        return {
            "ok": 1,
            "failed": "unionid不存在"
        }    

    try:
        # 查询Conversation以获取session_title并验证会话存在性和权限
        conversation_query = select(ConversationModel).where(
            ConversationModel.id == request.conversation_id)
        conversation_result = await session.execute(conversation_query)
        conversation = conversation_result.scalars().first()

        if conversation is None:
            return {
                "ok": 1,
                "failed": "Session not found"
            }            
        # 查询会话历史消息
        message_query = (
            select(MessageModel)
            .where(MessageModel.conversation_id == request.conversation_id)
            .options(selectinload(MessageModel.tools))  # 加载关联工具
            .order_by(desc(MessageModel.create_time))
        )
        message_result = await session.execute(message_query)
        message_data = message_result.scalars().unique().all()


        # 查询会话关联的文件（排除 neo_default_file）
        file_query = (
            select(UploadedFile)
            .where(
                UploadedFile.conversation_id == request.conversation_id,
                UploadedFile.file_type != "neo_default_file"  # 排除 neo_default_file
            )
            .order_by(desc(UploadedFile.create_time)))
        file_result = await session.execute(file_query)
        file_data = file_result.scalars().unique().all()

        # 单独查询 neo_default_file 类型的文件
        neo_file_query = (
            select(UploadedFile)
            .where(
                UploadedFile.conversation_id == request.conversation_id,
                UploadedFile.file_type == "neo_default_file"  # 仅查询 neo_default_file
            )
            .order_by(desc(UploadedFile.create_time)))
        neo_file_result = await session.execute(neo_file_query)
        neo_file_data = neo_file_result.scalars().unique().all()        


        # 如果没有消息和文件，返回空结果
        if not message_data and not file_data and not neo_file_data:
            return QuerySessionResponse(
                ok=1,
                failed="No data found",
                conversation_id=request.conversation_id,
                session_title="",
                chats=[],
                files=[],
                neo_files=[]
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
                    tool_result_analysis=tool.tool_result_analysis,
                    create_time=tool.create_time.strftime('%Y-%m-%d %H:%M:%S')
                )
                # 双重排序保障
                for tool in sorted(message.tools, key=lambda x: x.create_time)
            ]

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

        # 构建neo_files信息响应
        neo_files = [
            FileItem(
                file_name=file.file_name,
                file_path=file.file_path,
                file_desc=file.file_desc
            )
            for file in neo_file_data
        ]   

        return QuerySessionResponse(
            ok=0,
            failed="",
            conversation_id=request.conversation_id,
            session_title=conversation.session_title,
            chat_type=conversation.chat_type,
            chats=chats,
            files=files,  # 添加文件信息
            neo_files=neo_files
        )

    except Exception as e:
        return QuerySessionResponse(
            ok=1,
            failed=str(e),
            conversation_id=request.conversation_id,
            session_title="",
            chat_type=conversation.chat_type,
            chats=[],
            files=[],
            neo_files=[]
        )


# 查询会话历史sql
async def search_sessions_sql(
    session: AsyncSession ,
    credentials: HTTPAuthorizationCredentials
):
    # 提取并校验 token
    system_token = credentials.credentials  # 直接获取Token
    payload = decode_vaild(system_token,
                           SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        return {
            "ok": 1,
            "failed": "unionid不存在"
        }       
    # 查询会话列表的逻辑
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
            formatted_update_time = record.updata_time.strftime(
                "%Y-%m-%d %H:%M:%S")
            formatted_create_time = record.create_time.strftime(
                "%Y-%m-%d %H:%M:%S")
            sessions.append(SessionItem(
                conversation_id=record.id,
                session_title=record.session_title,
                updata_time=formatted_update_time,
                create_time=formatted_create_time,
                chat_type=record.chat_type
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


# chat路由插入单一会话内部-用户输入sql
@with_async_session
async def insert_user_input_chat(
        session,
        conversation_id: str,
        query: str
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


# 新建会话记录sql
async def add_sessions_sql(
        session: AsyncSession,
        credentials: HTTPAuthorizationCredentials,
        request: AddSessionRequest
):
    # 提取并校验 token
    system_token = credentials.credentials  # 直接获取Token
    payload = decode_vaild(system_token,
                           SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        return {
            "ok": 1,
            "failed": "unionid不存在"
        }  
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


# 返回会话id
async def get_new_session_id_sql(
        credentials: HTTPAuthorizationCredentials,
        
):
    # 提取并校验 token
    system_token = credentials.credentials  # 直接获取Token
    payload = decode_vaild(system_token,
                           SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        return {
            "ok": 1,
            "failed": "unionid不存在"
        }  
    try:
        id = str(uuid.uuid4())
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
async def upsert_conversation_sql(session, conversation_id: str, unionid: str, prompt: str):
    try:
        # 确保 prompt 是字符串，并截取前 30 个字符
        truncated_prompt = str(prompt)[:64] if prompt is not None else ""
    # 构建 UPSERT 语句
        stmt = (
            insert(ConversationModel)
            .values(
                id=conversation_id,
                user_id=unionid,
                session_title=truncated_prompt,  # 设置会话标题
                chat_type="normal",  # 设置聊天类型为 normal
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

        return {
            "ok": 1,
            "failed": f"数据库操作失败: {str(e)}"
        }  

async def update_session_name_sql(
        session: AsyncSession,
        credentials: HTTPAuthorizationCredentials,
        request: UpdateSessionRequest
):
    # 提取并校验 token
    system_token = credentials.credentials  # 直接获取Token
    payload = decode_vaild(system_token,
                           SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        return {
            "ok": 1,
            "failed": "unionid不存在"
        }  
    try:
        # 检查会话是否存在且属于当前用户
        result = await session.execute(
            select(ConversationModel)
            .where(ConversationModel.id == request.conversation_id)
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
    tool_result_analysis_list: list,
    msg_response: str
):

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
        m = result.scalars().first()
        if m is not None:
            # json_str = json.dumps(tool_result_analysis_list, ensure_ascii=False)

            m.response = msg_response
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
    # 批量插入Tool_files数据
    tool_files = []
    # 初始化基准时间（循环开始前记录）
    base_time = datetime.now()
    for index, tool_msg in enumerate(tool_messages):
        # 解析 content 字段中的 JSON 字符串
        content_dict = json.loads(tool_msg['content']['content'])
        url_field = content_dict.get("url", None)
        tool_llm_content = content_dict.get('content', '')
        # if 'url' in content_dict:
        #     # 原始字符串
        #     url = content_dict['url']
        #     tool_llm_content = content_dict['content']
        #     # 提取 minio:// 和 / 之间的值
        #     prefix = "minio://"
        #     start_index = len(prefix)  # 跳过 minio://
        #     end_index = url.find("/", start_index)  # 找到第一个 / 的位置
        #     # 提取目标值
        #     target_value = url[start_index:end_index]
        if isinstance(url_field, str) and url_field.startswith("minio://"):
            bucket_name = url_field[len("minio://"):].split("/", 1)[0]
            # 判断是否等于 netmhcpan-results
            if bucket_name == "netmhcpan-results":
                tool_files.append(
                    ToolFileModel(
                        id=str(uuid.uuid4()),
                        tool_id="acfe6b85-f651-11ef-a368-00163e1ab54a",
                        file_url=url_field,
                        tool_llm_content=tool_llm_content
                    )
                )
            else:
                pass

            if bucket_name == "esm-results":
                tool_files.append(
                    ToolFileModel(
                        id=str(uuid.uuid4()),
                        tool_id="bcfe6b85-f651-11ef-a368-00174e1ab54a",
                        file_url=url_field,
                        tool_llm_content=tool_llm_content
                    )
                )
            else:
                pass
        elif isinstance(url_field, dict):
            for _, single_url in url_field.items():
                if isinstance(single_url, str) and single_url.startswith("minio://"):
                    bucket_name = single_url[len("minio://"):].split("/", 1)[0]
                    if bucket_name == "netmhcpan-results":
                        tool_files.append(
                            ToolFileModel(
                                id=str(uuid.uuid4()),
                                tool_id="acfe6b85-f651-11ef-a368-00163e1ab54a",
                                file_url=url_field,
                                tool_llm_content=tool_llm_content
                            )
                        )
                    else:
                        pass

                    if bucket_name == "esm-results":
                        tool_files.append(
                            ToolFileModel(
                                id=str(uuid.uuid4()),
                                tool_id="bcfe6b85-f651-11ef-a368-00174e1ab54a",
                                file_url=url_field,
                                tool_llm_content=tool_llm_content
                            )
                        )
                    else:
                        pass

        content = tool_msg.get("content", {})
        tool_call_id = content.get("tool_call_id")
        if tool_call_id in tool_calls_map:
            tool_info = tool_calls_map[tool_call_id]
            new_id = str(uuid.uuid4())
            # 每次循环增加1秒
            current_time = base_time + timedelta(seconds=len(tool_models))

            # 获取对应索引的分析结果
            tool_analysis = tool_result_analysis_list[index] if index < len(
                tool_result_analysis_list) else ""
            tool_models.append(
                ToolModel(
                    id=new_id,
                    message_id=msg_id,  # 关联到 message 表的 ID
                    conversation_id=conversation_id,
                    tool_id=tool_call_id,
                    tool_name=tool_info["name"],
                    # 将 args 转为 JSON 字符串
                    tool_args=json.dumps(tool_info["args"]),
                    # tool_result=content.get('content', ''), #当前工具返回的是一个json，text/link
                    tool_result=content.get('content', ""),
                    create_time=current_time,
                    tool_result_analysis=tool_analysis
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

# 使用 update 操作更新uploadfiles的file_type字段值,并输出QuerySessionResponse: 包含会话消息、文件和neo_files的完整响应
@with_async_session
async def update_uploadfiles_file_type_sql(
    session,
    file_paths: list[str], 
    conversation_id: str,
):
    try:
        # 执行批量更新
        stmt = (
            update(UploadedFile)
            .where(
                UploadedFile.file_path.in_(file_paths),
                UploadedFile.conversation_id == conversation_id
            )
            .values(file_type="application/octet-stream")
        )
        
        await session.execute(stmt)
        await session.commit()
    except Exception as e:
        await session.rollback()
        return {
            "ok": 1,
            "failed": str(e)
        }
        
    try:
        # 查询Conversation以获取session_title并验证会话存在性和权限
        conversation_query = select(ConversationModel).where(
            ConversationModel.id == conversation_id)
        conversation_result = await session.execute(conversation_query)
        conversation = conversation_result.scalars().first()

        if conversation is None:
            return {
                "ok": 1,
                "failed": "Session not found"
            }            
        # 查询会话历史消息
        message_query = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .options(selectinload(MessageModel.tools))  # 加载关联工具
            .order_by(desc(MessageModel.create_time))
        )
        message_result = await session.execute(message_query)
        message_data = message_result.scalars().unique().all()


        # 查询会话关联的文件（排除 neo_default_file）
        file_query = (
            select(UploadedFile)
            .where(
                UploadedFile.conversation_id == conversation_id,
                UploadedFile.file_type != "neo_default_file"  # 排除 neo_default_file
            )
            .order_by(desc(UploadedFile.create_time)))
        file_result = await session.execute(file_query)
        file_data = file_result.scalars().unique().all()

        # 单独查询 neo_default_file 类型的文件
        neo_file_query = (
            select(UploadedFile)
            .where(
                UploadedFile.conversation_id == conversation_id,
                UploadedFile.file_type == "neo_default_file"  # 仅查询 neo_default_file
            )
            .order_by(desc(UploadedFile.create_time)))
        neo_file_result = await session.execute(neo_file_query)
        neo_file_data = neo_file_result.scalars().unique().all()        


        # 如果没有消息和文件，返回空结果
        if not message_data and not file_data and not neo_file_data:
            return QuerySessionResponse(
                ok=1,
                failed="No data found",
                conversation_id=conversation_id,
                session_title="",
                chats=[],
                files=[],
                neo_files=[]
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
                    tool_result_analysis=tool.tool_result_analysis,
                    create_time=tool.create_time.strftime('%Y-%m-%d %H:%M:%S')
                )
                # 双重排序保障
                for tool in sorted(message.tools, key=lambda x: x.create_time)
            ]

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

        # 构建neo_files信息响应
        neo_files = [
            FileItem(
                file_name=file.file_name,
                file_path=file.file_path,
                file_desc=file.file_desc
            )
            for file in neo_file_data
        ]   

        return QuerySessionResponse(
            ok=0,
            failed="",
            conversation_id=conversation_id,
            session_title=conversation.session_title,
            chat_type=conversation.chat_type,
            chats=chats,
            files=files,  # 添加文件信息
            neo_files=neo_files
        )

    except Exception as e:
        return QuerySessionResponse(
            ok=1,
            failed=str(e),
            conversation_id= conversation_id,
            session_title="",
            chat_type=conversation.chat_type,
            chats=[],
            files=[],
            neo_files=[]
        )
#初始化demo聊天区
async def reset_conversation_sql(
    session: AsyncSession,
    credentials: HTTPAuthorizationCredentials,
    request: ResetConversationRequest
):
    try:
        # 提取并校验 token
        system_token = credentials.credentials  # 直接获取Token
        payload = decode_vaild(system_token,SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if unionid is None:
            return BaseResponse(ok=1, failed="unionid不存在") 
    except Exception as e:
        return BaseResponse(ok=1, failed=f"Token校验失败: {e}")
    try:
        # 检查会话是否存在且属于当前用户
        result = await session.execute(
            select(ConversationModel)
            .where(ConversationModel.id == request.conversation_id)
            .where(ConversationModel.user_id == unionid)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            return BaseResponse(ok=1, failed="Conversation not found or does not belong to the user")
        
        # 找到初始消息（最早的create_time）
        message_query = (
            select(MessageModel)
            .where(MessageModel.conversation_id == request.conversation_id)
            .options(selectinload(MessageModel.tools))
            .order_by(MessageModel.create_time.asc())
            .limit(1)
        )
        message_result = await session.execute(message_query)
        initial_message = message_result.scalars().first()
        
        # 删除与会话关联的工具，但保留初始消息的工具（如果有）
        if initial_message is not None:
            initial_message_tool_ids = [tool.id for tool in initial_message.tools]
            if initial_message_tool_ids:
                await session.execute(
                    delete(ToolModel)
                    .where(ToolModel.conversation_id == request.conversation_id)
                    .where(~ToolModel.id.in_(initial_message_tool_ids))
                )
            else:
                # 初始消息没有工具，删除所有工具
                await session.execute(
                    delete(ToolModel)
                    .where(ToolModel.conversation_id == request.conversation_id)
                )
                
        # 删除除初始消息外的所有消息
        if initial_message is not None:
            await session.execute(
                delete(MessageModel)
                .where(MessageModel.conversation_id == request.conversation_id)
                .where(MessageModel.id != initial_message.id)
            )

        # 删除用户上传的文件（file_origin=0），保留系统默认文件（file_origin=1）
        await session.execute(
            delete(UploadedFile)
            .where(UploadedFile.conversation_id == request.conversation_id)
            .where(UploadedFile.file_origin == 0)
        )

        # 更新系统默认文件（file_origin=1）的file_type为"neo_default_file"
        await session.execute(
            update(UploadedFile)
            .where(UploadedFile.conversation_id == request.conversation_id)
            .where(UploadedFile.file_origin == 1)
            .values(file_type="neo_default_file")
        )
        # 提交事务
        await session.commit()
        return BaseResponse(ok=0, failed="")
    
    except SQLAlchemyError as e:
        await session.rollback()
        return BaseResponse(ok=1, failed=f"数据库错误: {e}")
    except Exception as e:
        await session.rollback()
        return BaseResponse(ok=1, failed=f"系统错误: {e}")
