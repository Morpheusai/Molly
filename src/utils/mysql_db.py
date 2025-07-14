import httpx
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from collections import OrderedDict

from dotenv import load_dotenv
from fastapi import (
    Body,
    Depends,
    HTTPException,
    status
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import delete, desc, update, asc, func, text
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.api.protocols import *
from src.db import (
    ConversationModel,
    FileModel,
    MessageModel,
    PatientModel,
    PredictionModel,
    ProjectModel,
    UserModel,
    WorkflowModel,
    PredictionDetailModel,
    TaskQueueModel,
)
from src.utils.jwt_util import decode_vaild
from src.utils.session import get_async_db, with_async_session
from src.utils.delete_agent_state import remote_delete_agent_state
from src.utils import logger

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "")  # 用于签名和验证 JWT 的密钥
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # 加密算法

# 查询unionid的记录
@with_async_session
async def search_unionid_sql(session, unionid: str) -> Optional[UserModel]:
    """
    根据unionid查询用户记录
    
    Args:
        unionid: 用户统一标识
    
    Returns:
        UserModel实例 或 None（如果未找到）
    """
    if not unionid:
        raise HTTPException(status_code=401, detail="无效的用户认证")
    
    try:
        # 使用更明确的查询方式
        stmt = select(UserModel).where(UserModel.unionid == unionid)
        result = await session.execute(stmt)
        return result.scalars().first()
    except Exception as e:
        logger.error(f"查询用户失败: {e}", exc_info=True)
        return None

# 添加用户记录sql
@with_async_session
async def add_user_sql(session,  request: AddUserRequest = None):
    try:
        user = UserModel(
            unionid=request.unionid,
            openid=request.openid,
            role=request.role,
            nickname=request.nickname,
            province=request.province,
            city=request.city,
            country=request.country,
            headimgurl=request.headimgurl,
            created_by=request.created_by,
            phone=request.phone,
            email=request.email,
            is_active=request.is_active,
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

# 创建病历记录
async def create_medical_records_sql(session, request: CreateMedicalRecordRequest, unionid: str):
    try:
        # 判断是新增还是修改
        if request.patient_id and str(request.patient_id).isdigit():
            # 修改模式
            patient = await session.get(PatientModel, int(request.patient_id))
            if not patient:
                return CreateMedicalRecordResponse(ok=1, failed="未找到该病人", patient_id=None)
            # 更新字段
            patient.project_id = request.project_id
            patient.medical_record_number = request.medical_record_number or ""
            patient.name = request.name or ""
            patient.gender = request.gender or "other"
            patient.birth_date = datetime.strptime(request.birth_date, "%Y-%m-%d").date() if request.birth_date else None
            patient.phone = request.phone or ""
            patient.email = request.email or ""
            patient.hospital = request.hospital or ""
            patient.blood_type = request.blood_type or "unknown"
            patient.tumor_type = request.tumor_type or ""
            patient.HLA_type = request.HLA_type or ""
            patient.CDR_type = request.CDR_type or ""
            patient.treatment_state = request.treatment_state or ""
            patient.additional_info = request.additional_info or ""
            patient.source_id = request.source_id if hasattr(request, 'source_id') else None
            patient.clinical_medication = request.clinical_medication or ""
            patient.clinical_diagnosis = request.clinical_diagnosis or ""
            # 这里不更新created_by/status等只读字段
            await session.commit()
            return CreateMedicalRecordResponse(ok=0, failed="", patient_id=patient.id)
        else:
            # 原有创建逻辑
            patient = PatientModel(
                project_id=request.project_id,
                medical_record_number=request.medical_record_number if request.medical_record_number else "",
                name=request.name if request.name else "",
                gender=request.gender if request.gender else "other",
                birth_date=datetime.strptime(request.birth_date, "%Y-%m-%d").date() if request.birth_date else None,
                phone=request.phone if request.phone else "",
                email=request.email if request.email else "",
                hospital=request.hospital if request.hospital else "",
                blood_type=request.blood_type if request.blood_type else "unknown",
                tumor_type=request.tumor_type if request.tumor_type else "",
                HLA_type=request.HLA_type if request.HLA_type else "",
                CDR_type=request.CDR_type if request.CDR_type else "",
                treatment_state=request.treatment_state if request.treatment_state else "",
                additional_info=request.additional_info if request.additional_info else "",
                clinical_medication=request.clinical_medication or "",
                clinical_diagnosis=request.clinical_diagnosis or "",
                created_by=unionid,
                status='new',
                source_id=request.source_id if hasattr(request, 'source_id') else None
            )
            session.add(patient)
            await session.commit()
            await session.refresh(patient)
            # 如果传了source_id，更新对应文件的patient_id
            if getattr(request, 'source_id', None):
                file_obj = await session.get(FileModel, request.source_id)
                if file_obj:
                    file_obj.patient_id = patient.id
                    await session.commit()
            return CreateMedicalRecordResponse(
                ok=0,
                failed="",
                patient_id=patient.id
            )
    except Exception as e:
        await session.rollback()
        logger.error(f"创建/修改病历失败: {e}", exc_info=True)
        return CreateMedicalRecordResponse(
            ok=1,
            failed=str(e),
            patient_id=None
        )

@with_async_session
async def get_patients_by_unionid_sql(session, unionid: str):
    """
    根据用户unionid查询其所有病人及病人文件信息
    """
    try:
        # 查询所有该用户创建的病人，并预加载files，避免异步环境下的延迟加载报错
        patients = await session.execute(
            select(PatientModel)
            .options(selectinload(PatientModel.files))
            .where(PatientModel.created_by == unionid)
        )
        patients = patients.scalars().all()
        result = []
        for patient in patients:
            # 查询该病人所有文件
            files = []
            for file in patient.files:
                files.append({
                    'file_name': file.file_name,
                    'file_type': file.file_type,
                    'file_desc': file.file_desc,
                    'file_path': file.file_path,
                    'created_at': file.created_at.strftime('%Y-%m-%d %H:%M:%S') if file.created_at else None
                })
            result.append({
                'patient_id': patient.id,
                'medical_record_number': patient.medical_record_number,
                'name': patient.name,
                'gender': patient.gender,
                'birth_date': patient.birth_date.strftime('%Y-%m-%d') if patient.birth_date else None,
                'phone': patient.phone,
                'email': patient.email,
                'hospital': patient.hospital,
                'blood_type': patient.blood_type,
                'tumor_type': patient.tumor_type,
                'HLA_type': patient.HLA_type,
                'CDR_type': patient.CDR_type,
                'treatment_state': patient.treatment_state,
                'additional_info': patient.additional_info,
                'status': patient.status,
                'source_id': patient.source_id,
                'created_at': patient.created_at.strftime('%Y-%m-%d %H:%M:%S') if patient.created_at else None,
                'files': files
            })
        return result
    except Exception as e:
        logger.error(f"查询病人及文件失败: {e}", exc_info=True)
        return []

@with_async_session
async def get_patients_brief_by_unionid_sql(session, unionid: str):
    """
    查询指定 unionid 下所有病人的 id 和姓名
    """
    try:
        patients = await session.execute(
            select(PatientModel.id, PatientModel.name).where(PatientModel.created_by == unionid)
        )
        result = [
            {"patient_id": row.id, "name": row.name} for row in patients.all()
        ]
        return result
    except Exception as e:
        logger.error(f"查询病人简要信息失败: {e}", exc_info=True)
        return []

@with_async_session
async def get_patient_detail_by_id_sql(session, patient_id: int):
    """
    根据病人ID查询该病人的详细信息（不返回id、source_id、created_at等字段）。
    
    参数：
        session: 数据库会话，由装饰器自动注入
        patient_id: 需要查询的病人主键ID
    返回：
        - 查询成功：返回 dict，包含病人详细信息（字段见 PatientDetailInfo）
        - 未查到：返回 None
        - 异常：返回 None，并记录日志
    """
    try:
        patient = await session.get(PatientModel, patient_id)
        if not patient:
            return None
        return {
            'medical_record_number': patient.medical_record_number,
            'name': patient.name,
            'gender': patient.gender,
            'birth_date': patient.birth_date.strftime('%Y-%m-%d') if patient.birth_date else None,
            'phone': patient.phone,
            'email': patient.email,
            'hospital': patient.hospital,
            'blood_type': patient.blood_type,
            'tumor_type': patient.tumor_type,
            'HLA_type': patient.HLA_type,
            'CDR_type': patient.CDR_type,
            'treatment_state': patient.treatment_state,
            'additional_info': patient.additional_info,
            'clinical_medication': patient.clinical_medication,
            'clinical_diagnosis': patient.clinical_diagnosis,
            'status': patient.status,
            'updated_at': patient.updated_at.strftime('%Y-%m-%d %H:%M:%S') if patient.updated_at else None
        }
    except Exception as e:
        logger.error(f"查询病人详细信息失败: {e}", exc_info=True)
        return None


async def create_project_sql(session, request: CreateProjectRequest, unionid: str):
    """
    创建或更新项目记录
    Args:
        request: 创建项目请求对象
        unionid: 创建者用户ID
    Returns:
        CreateProjectResponse实例
    """
    try:
        # 如果传入了project_id，则更新现有项目
        if request.project_id is not None:
            project = await session.get(ProjectModel, request.project_id)
            if not project:
                return CreateProjectResponse(
                    ok=1,
                    failed="项目不存在",
                    project_id=None
                )
            
            # 验证项目是否属于当前用户
            if project.created_by != unionid:
                return CreateProjectResponse(
                    ok=1,
                    failed="无权修改此项目",
                    project_id=None
                )
            
            # 更新项目信息
            project.name = request.name
            project.project_code = request.project_code
            project.short_name = request.short_name
            project.description = request.description
            project.project_type = request.project_type
            project.indication = request.indication
            project.study_phase = request.study_phase
            project.is_multicenter = request.is_multicenter
            project.registration_number = request.registration_number
            project.registration_platform_url = request.registration_platform_url
            project.principal_investigator = request.principal_investigator
            project.pi_email = request.pi_email
            project.hospital = request.hospital
            project.phone = request.phone
            project.patient_enrollment_count = request.patient_enrollment_count
            project.status = request.status
            project.updated_at = datetime.now()
            
            await session.commit()
            await session.refresh(project)
            return CreateProjectResponse(
                ok=0,
                failed="",
                project_id=project.id
            )
        else:
            # 创建新项目
            project = ProjectModel(
                name=request.name,
                created_by=unionid,
                project_code=request.project_code,
                short_name=request.short_name,
                description=request.description,
                project_type=request.project_type,
                indication=request.indication,
                study_phase=request.study_phase,
                is_multicenter=request.is_multicenter,
                registration_number=request.registration_number,
                registration_platform_url=request.registration_platform_url,
                principal_investigator=request.principal_investigator,
                pi_email=request.pi_email,
                hospital=request.hospital,
                phone=request.phone,
                patient_enrollment_count=request.patient_enrollment_count,
                status=request.status
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            return CreateProjectResponse(
                ok=0,
                failed="",
                project_id=project.id
            )
    except Exception as e:
        await session.rollback()
        logger.error(f"创建或更新项目失败: {e}", exc_info=True)
        return CreateProjectResponse(
            ok=1,
            failed=str(e),
            project_id=None
        )


async def get_projects_by_unionid_sql(session, unionid: str):
    """
    查询指定unionid下所有项目，返回所有字段
    """
    try:
        projects = await session.execute(
            select(ProjectModel)
            .where(ProjectModel.created_by == unionid)
        )
        result = []
        for project in projects.scalars().all():
            result.append({
                "project_id": project.id,
                "name": project.name,
                "project_code": project.project_code,
                "short_name": project.short_name,
                "description": project.description,
                "project_type": project.project_type,
                "indication": project.indication,
                "study_phase": project.study_phase,
                "is_multicenter": project.is_multicenter,
                "registration_number": project.registration_number,
                "registration_platform_url": project.registration_platform_url,
                "principal_investigator": project.principal_investigator,
                "pi_email": project.pi_email,
                "hospital": project.hospital,
                "phone": project.phone,
                "patient_enrollment_count": project.patient_enrollment_count,
                "doctor_enrollment_count": getattr(project, 'doctor_enrollment_count', None),
                "status": project.status,
                "created_at": project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else None,
                "updated_at": project.updated_at.strftime('%Y-%m-%d %H:%M:%S') if project.updated_at else None,
                "created_by": project.created_by
            })
        return result
    except Exception as e:
        logger.error(f"查询项目列表失败: {e}", exc_info=True)
        return []

@with_async_session
async def get_patients_brief_by_project_sql(session, project_id: int):
    """
    查询指定项目下所有病人，返回所有字段
    """
    try:
        patients = await session.execute(
            select(PatientModel)
            .where(PatientModel.project_id == project_id)
        )
        result = []
        for patient in patients.scalars().all():
            result.append({
                "patient_id": patient.id,
                "project_id": patient.project_id,
                "source_id": patient.source_id,
                "medical_record_number": patient.medical_record_number,
                "name": patient.name,
                "gender": patient.gender,
                "birth_date": patient.birth_date.strftime('%Y-%m-%d') if patient.birth_date else None,
                "phone": patient.phone,
                "email": patient.email,
                "hospital": patient.hospital,
                "blood_type": patient.blood_type,
                "tumor_type": patient.tumor_type,
                "HLA_type": patient.HLA_type,
                "CDR_type": patient.CDR_type,
                "treatment_state": patient.treatment_state,
                "additional_info": patient.additional_info,
                "clinical_medication": patient.clinical_medication,
                "clinical_diagnosis": patient.clinical_diagnosis,
                "status": patient.status,
                "created_by": patient.created_by,
                "created_at": patient.created_at.strftime('%Y-%m-%d %H:%M:%S') if patient.created_at else None,
                "updated_at": patient.updated_at.strftime('%Y-%m-%d %H:%M:%S') if patient.updated_at else None
            })
        return result
    except Exception as e:
        logger.error(f"查询项目下病人简要信息失败: {e}", exc_info=True)
        return []

@with_async_session
async def get_patient_files_sql(session, patient_id: int, file_type: Optional[str] = None):
    """
    查询指定病人id下所有文件的名、路径、类型及数量
    如果提供了file_type，则只查询该类型的文件
    """
    try:
        query = select(FileModel.file_name, FileModel.file_path, FileModel.file_type, FileModel.file_desc) \
            .where(FileModel.patient_id == patient_id, FileModel.is_deleted == 0)

        if file_type:
            query = query.where(FileModel.file_type == file_type)

        files = await session.execute(query)
        
        file_list = [
            {"file_name": row.file_name, "file_path": row.file_path, "file_type": row.file_type, "file_desc": row.file_desc}
            for row in files.all()
        ]
        return {
            "files": file_list,
            "total": len(file_list)
        }
    except Exception as e:
        logger.error(f"查询病人文件失败: {e}", exc_info=True)
        return {"files": [], "total": 0}

@with_async_session
async def create_conversation_sql(session, patient_id: int, conversation_type: str, title: str):
    """
    创建新的会话记录
    Args:
        session: 数据库会话
        patient_id: 病人ID
        conversation_type: 会话类型
        title: 会话标题
    Returns:
        dict: 包含ok、failed和conversation_id的字典
    """
    try:
        conversation = ConversationModel(
            patient_id=patient_id,
            type=conversation_type,
            title=title,
            is_deleted=0
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        
        return {
            "ok": 0,
            "failed": "",
            "conversation_id": conversation.id
        }
    except Exception as e:
        await session.rollback()
        logger.error(f"创建会话记录失败: {e}", exc_info=True)
        return {
            "ok": 1,
            "failed": str(e),
            "conversation_id": None
        }


@with_async_session
async def predict_process_messages(
    session,
    conversation_id: str,
    ai_messages: List[Dict],
    tool_messages: List[Dict],
    tool_result_analysis_list: list,
    msg_response: str,
    tool_middle_result: str,
):
    # 更新 message 表的 response 字段
    try:
        # 检查msg_response是否为空或只包含空白字符
        if not msg_response or msg_response.strip() == "":
            logger.warning(f"msg_response为空，跳过创建assistant消息，conversation_id: {conversation_id}")
            return BaseResponse(
                ok=0,
                failed=""
            )
        
        # 创建新的assistant类型消息记录
        new_message = MessageModel(
            conversation_id=conversation_id,
            type='assistant',
            content=msg_response,
            is_deleted=0
        )
        session.add(new_message)
        await session.commit()
        await session.refresh(new_message)
        
        # 保存新创建的消息ID，供后续tool记录使用
        msg_id = new_message.id
        logger.info(f"成功创建assistant消息，message_id: {msg_id}, conversation_id: {conversation_id}")
        
    except Exception as e:
        await session.rollback()
        logger.error(f"创建assistant消息失败: {e}", exc_info=True)
        return BaseResponse(
            ok=1,
            failed=str(e)
        )

    # # 第二步：处理 Tool 消息
    # tool_calls_map = {}

    # # 收集所有 AI 消息中的 tool_calls
    # for ai_msg in ai_messages:
    #     content = ai_msg.get("content", {})
    #     for tool_call in content.get("tool_calls", []):
    #         tool_calls_map[tool_call["id"]] = {
    #             "name": tool_call["name"],
    #             "args": tool_call["args"]
    #         }

    # # 批量插入 Tool 数据
    # tool_models = []
    # # 批量插入Tool_files数据
    # tool_files = []
    # # 初始化基准时间（循环开始前记录）
    # base_time = datetime.now()
    # for index, tool_msg in enumerate(tool_messages):

    #     content = tool_msg.get("content", {})
    #     tool_call_id = content.get("tool_call_id")
    #     if tool_call_id in tool_calls_map:
    #         tool_info = tool_calls_map[tool_call_id]
    #         new_id = str(uuid.uuid4())
    #         # 每次循环增加1秒
    #         current_time = base_time + timedelta(seconds=len(tool_models))

    #         # 获取对应索引的分析结果
    #         tool_analysis = tool_result_analysis_list[index] if index < len(
    #             tool_result_analysis_list) else ""
    #         #目前只考虑而每次调用只要一个工具的中间结果的情况
    #         if index==0:
    #             tool_models.append(
    #                 ToolModel(
    #                     id=new_id,
    #                     message_id=msg_id,  # 关联到 message 表的 ID
    #                     conversation_id=conversation_id,
    #                     tool_id=tool_call_id,
    #                     tool_name=tool_info["name"],
    #                     # 将 args 转为 JSON 字符串
    #                     tool_args=json.dumps(tool_info["args"]),
    #                     # tool_result=content.get('content', ''), #当前工具返回的是一个json，text/link
    #                     tool_result=content.get('content', ""),
    #                     tool_middle_result=tool_middle_result,
    #                     create_time=current_time,
    #                     tool_result_analysis=tool_analysis
    #                 )
    #             )            
    #         else:    
    #             tool_models.append(
    #                 ToolModel(
    #                     id=new_id,
    #                     message_id=msg_id,  # 关联到 message 表的 ID
    #                     conversation_id=conversation_id,
    #                     tool_id=tool_call_id,
    #                     tool_name=tool_info["name"],
    #                     # 将 args 转为 JSON 字符串
    #                     tool_args=json.dumps(tool_info["args"]),
    #                     # tool_result=content.get('content', ''), #当前工具返回的是一个json，text/link
    #                     tool_result=content.get('content', ""),
    #                     create_time=current_time,
    #                     tool_result_analysis=tool_analysis
    #                 )
    #             )
    # # 批量插入工具数据
    # if tool_models:
    #     try:
    #         session.add_all(tool_models)
    #         await session.commit()
    #     except Exception as e:
    #         await session.rollback()
    #         return BaseResponse(
    #             ok=1,
    #             failed=str(e)
    #         )

    # # 批量插入Tool_files数据
    # if tool_files:
    #     try:
    #         session.add_all(tool_files)
    #         await session.commit()
    #     except Exception as e:
    #         await session.rollback()
    #         return BaseResponse(
    #             ok=1,
    #             failed=str(e)
    #         )

@with_async_session
async def insert_message_sql(session, conversation_id: int, type:str,content: str):
    """
    插入一条用户消息到消息表
    Args:
        session: 数据库会话
        conversation_id: 会话ID
        type: 消息类型
        content: 消息内容
    Returns:
        新消息的id
    """
    try:
        new_message = MessageModel(
            conversation_id=conversation_id,
            type=type,
            content=content,
            is_deleted=0
        )
        session.add(new_message)
        await session.commit()
        await session.refresh(new_message)
        return new_message.id
    except Exception as e:
        await session.rollback()
        logger.error(f"插入消息失败: {e}", exc_info=True)
        return None

@with_async_session
async def get_messages_by_conversation_id_sql(session, conversation_id: int):
    """
    查询指定会话ID下的所有未删除的消息记录，并按创建时间升序排序。
    
    Args:
        session: 数据库会话，由装饰器自动注入。
        conversation_id: 要查询的会话ID。
    
    Returns:
        一个包含消息信息的字典列表，如果出错则返回空列表。
    """
    try:
        # 构建查询，选择指定conversation_id且未被删除的消息
        messages = await session.execute(
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id, MessageModel.is_deleted == 0)
            .order_by(MessageModel.create_time)  # 按创建时间排序
        )
        # 格式化查询结果
        message_list = [
            {
                "id": msg.id,
                "type": msg.type,
                "content": msg.content,
                "create_time": msg.create_time.strftime('%Y-%m-%d %H:%M:%S')
            }
            for msg in messages.scalars().all()
        ]
        return message_list
    except Exception as e:
        logger.error(f"查询会话消息失败: {e}", exc_info=True)
        return []

@with_async_session
async def get_workflow_status_by_patient_id_sql(session, patient_id: int):
    """
    根据病人ID查询所有工作流状态
    """
    try:
        logger.info(f"查询病人 {patient_id} 的工作流状态")
        workflows = await session.execute(
            select(WorkflowModel.stage, WorkflowModel.status, WorkflowModel.rank)
            .where(WorkflowModel.patient_id == patient_id)
            .order_by(WorkflowModel.rank)
        )
        result = []
        for row in workflows.all():
            result.append({
                "stage": row.stage,
                "status": row.status,
                "rank": row.rank
            })
        logger.info(f"查询结果: {result}")
        return result
    except Exception as e:
        logger.error(f"查询工作流状态失败: {e}", exc_info=True)
        return []

@with_async_session
async def get_conversation_id_by_patient_and_type_sql(session, patient_id: int, conversation_type: str):
    """
    根据病人ID和会话类型查找最新的conversation_id。
    """
    try:
        conversation = await session.execute(
            select(ConversationModel.id)
            .where(
                ConversationModel.patient_id == patient_id,
                ConversationModel.type == conversation_type,
                ConversationModel.is_deleted == 0
            )
            .order_by(ConversationModel.create_time.desc())
        )
        row = conversation.first()
        if row:
            return row.id
        return None
    except Exception as e:
        logger.error(f"查找会话ID失败: {e}", exc_info=True)
        return None

@with_async_session
async def get_prediction_details_by_patient_id_sql(session, patient_id: int):
    """
    根据病人ID查询其所有PredictionDetailModel记录，按rank升序返回指定字段，并包含PredictionModel的创建时间。
    """
    try:
        details = await session.execute(
            select(
                PredictionDetailModel.rank,
                PredictionDetailModel.tool_name,
                PredictionDetailModel.tool_parameters,
                PredictionDetailModel.status,
                PredictionDetailModel.start_time,
                PredictionDetailModel.end_time,
                PredictionDetailModel.elapsed_time,
                PredictionDetailModel.error_message,
                PredictionDetailModel.tool_output,
                PredictionModel.create_time.label("prediction_create_time")
            ).join(PredictionModel, PredictionDetailModel.prediction_id == PredictionModel.id)
            .where(PredictionDetailModel.patient_id == patient_id)
            .order_by(asc(PredictionDetailModel.rank))
        )
        result = []
        for row in details.all():
            # 将JSON字符串反序列化为字典
            tool_parameters = json.loads(row.tool_parameters) if row.tool_parameters else None
            tool_output = json.loads(row.tool_output) if row.tool_output else None
            
            result.append({
                "rank": row.rank,
                "tool_name": row.tool_name,
                "tool_parameters": tool_parameters,
                "status": row.status,
                "start_time": row.start_time.strftime('%Y-%m-%d %H:%M:%S') if row.start_time else None,
                "end_time": row.end_time.strftime('%Y-%m-%d %H:%M:%S') if row.end_time else None,
                "elapsed_time": row.elapsed_time,
                "error_message": row.error_message,
                "tool_output": tool_output,
                "prediction_create_time": row.prediction_create_time.strftime('%Y-%m-%d %H:%M:%S') if row.prediction_create_time else None
            })
        return result
    except Exception as e:
        logger.error(f"查询PredictionDetailModel失败: {e}", exc_info=True)
        return []

@with_async_session
async def get_prediction_groups_by_patient_id_sql(session, patient_id: int):
    """
    查询该病人所有预测表及其细节，按预测表创建时间降序排列。
    返回：[{prediction_id, create_time, details:[...]}]
    """
    try:
        # 查询所有预测表，按创建时间降序
        predictions = await session.execute(
            select(PredictionModel.id, PredictionModel.create_time)
            .where(PredictionModel.patient_id == patient_id)
            .order_by(PredictionModel.create_time.desc())
        )
        prediction_rows = predictions.all()
        result = []
        for pred in prediction_rows:
            details_query = await session.execute(
                select(
                    PredictionDetailModel.rank,
                    PredictionDetailModel.tool_name,
                    PredictionDetailModel.tool_parameters,
                    PredictionDetailModel.status,
                    PredictionDetailModel.start_time,
                    PredictionDetailModel.end_time,
                    PredictionDetailModel.elapsed_time,
                    PredictionDetailModel.error_message,
                    PredictionDetailModel.tool_output,
                    PredictionDetailModel.flag
                ).where(PredictionDetailModel.prediction_id == pred.id)
                .order_by(asc(PredictionDetailModel.rank))
            )
            details = []
            for row in details_query.all():
                # 将JSON字符串反序列化为字典
                tool_parameters = json.loads(row.tool_parameters) if row.tool_parameters else None
                tool_output = json.loads(row.tool_output) if row.tool_output else None
                
                details.append({
                    "rank": row.rank,
                    "tool_name": row.tool_name,
                    "tool_parameters": tool_parameters,
                    "status": row.status,
                    "start_time": row.start_time.strftime('%Y-%m-%d %H:%M:%S') if row.start_time else None,
                    "end_time": row.end_time.strftime('%Y-%m-%d %H:%M:%S') if row.end_time else None,
                    "elapsed_time": row.elapsed_time,
                    "error_message": row.error_message,
                    "tool_output": tool_output,
                    "flag": row.flag,
                    "prediction_create_time": pred.create_time.strftime('%Y-%m-%d %H:%M:%S') if pred.create_time else None
                })
            result.append({
                "prediction_id": pred.id,
                "create_time": pred.create_time.strftime('%Y-%m-%d %H:%M:%S') if pred.create_time else None,
                "prediction_details": details
            })
        return result
    except Exception as e:
        logger.error(f"查询PredictionGroup失败: {e}", exc_info=True)
        return []

@with_async_session
async def handle_tool_input_output_sql(session, request):
    """
    处理工具输入输出参数
    Args:
        session: 数据库会话（由装饰器自动注入）
        request: 工具输入输出请求对象
        unionid: 用户ID
    Returns:
        ToolInputOutputResponse实例
    """
    try:
        # 验证病人和预测是否存在
        patient = await session.get(PatientModel, request.patient_id)
        if not patient:
            return ToolInputOutputResponse(ok=1, failed="病人不存在", predict_detail_id=None)
        
        prediction = await session.get(PredictionModel, request.prediction_id)
        if not prediction:
            return ToolInputOutputResponse(ok=1, failed="预测记录不存在", predict_detail_id=None)
        
        # 验证预测是否属于该病人
        if prediction.patient_id != request.patient_id:
            return ToolInputOutputResponse(ok=1, failed="预测记录不属于该病人", predict_detail_id=None)
        
        # 将字典序列化为JSON字符串，保持键的顺序
        parameters_json = json.dumps(request.parameters, ensure_ascii=False, separators=(',', ':'))
        
        # 根据mode判断是输入还是输出
        if request.mode == 0:  # 工具输入参数
            # 获取当前最大rank
            max_rank_result = await session.execute(
                select(func.max(PredictionDetailModel.rank))
                .where(PredictionDetailModel.prediction_id == request.prediction_id)
            )
            max_rank = max_rank_result.scalar() or 0
            new_rank = max_rank + 1

            # 创建新记录
            new_detail = PredictionDetailModel(
                patient_id=request.patient_id,
                prediction_id=request.prediction_id,
                rank=new_rank,
                tool_name=request.tool_name,
                tool_parameters=parameters_json,  # 存储JSON字符串
                tool_output=None,
                status='pending',
                start_time=datetime.now(),
                end_time=None,
                elapsed_time=None,
                error_message=None,
                flag=request.flag
            )
            session.add(new_detail)
            await session.commit()
            await session.refresh(new_detail)
            predict_detail_id = new_detail.id
                
        elif request.mode == 1:  # 工具输出结果
            # 查找对应的工具记录（按start_time降序，取最新的）
            detail = await session.execute(
                select(PredictionDetailModel)
                .where(
                    PredictionDetailModel.prediction_id == request.prediction_id,
                    PredictionDetailModel.tool_name == request.tool_name
                )
                .order_by(PredictionDetailModel.start_time.desc())
            )
            detail = detail.scalar_one_or_none()
            
            if not detail:
                return ToolInputOutputResponse(ok=1, failed="未找到对应的工具记录", predict_detail_id=None)
            
            # 更新输出结果
            detail.tool_output = parameters_json  # 存储JSON字符串
            detail.status = 'completed'
            detail.end_time = datetime.now()
            detail.flag = request.flag  # 更新flag值
            if detail.start_time:
                detail.elapsed_time = int((detail.end_time - detail.start_time).total_seconds())
            await session.commit()
            predict_detail_id = detail.id

        else:
            return ToolInputOutputResponse(ok=1, failed="无效的mode值", predict_detail_id=None)
        
        return ToolInputOutputResponse(ok=0, failed="", predict_detail_id=predict_detail_id)
        
    except Exception as e:
        await session.rollback()
        logger.error(f"处理工具输入输出失败: {e}", exc_info=True)
        return ToolInputOutputResponse(ok=1, failed=str(e), predict_detail_id=None)

@with_async_session
async def handle_ai_message_sql(session, request: HandleAIMessageRequest):
    """
    处理AI消息：如果最新消息不是assistant则新建，否则追加内容。
    简化版本：只基于消息类型判断，使用ID排序确保稳定性。
    
    Args:
        session: 数据库会话
        request: HandleAIMessageRequest
    Returns:
        HandleAIMessageResponse
    """
    try:
        # 使用ID排序而不是时间排序，更稳定
        messages = await session.execute(
            select(MessageModel)
            .where(MessageModel.conversation_id == request.conversation_id, MessageModel.is_deleted == 0)
            .order_by(MessageModel.id.desc())
        )
        latest_msg = messages.scalars().first()
        
        # 如果没有消息或最新消息不是assistant类型，创建新消息
        if not latest_msg or latest_msg.type != 'assistant':
            logger.info(f"创建新的assistant消息，conversation_id: {request.conversation_id}")
            # 新建assistant类型消息
            new_message = MessageModel(
                conversation_id=request.conversation_id,
                type='assistant',
                content=request.ai_message or "",
                is_deleted=0
            )
            session.add(new_message)
            await session.commit()
            await session.refresh(new_message)
            return HandleAIMessageResponse(ok=0, failed="", message_id=new_message.id, content=new_message.content)
        
        # 最新消息是assistant类型，进行合并
        current_content = latest_msg.content or ""
        new_content = request.ai_message or ""
        
        # 如果当前内容为空，直接设置新内容
        if not current_content:
            logger.info(f"当前消息内容为空，直接设置新内容，message_id: {latest_msg.id}")
            latest_msg.content = new_content
            await session.commit()
            return HandleAIMessageResponse(ok=0, failed="", message_id=latest_msg.id, content=new_content)
        
        # 合并内容
        logger.info(f"合并消息内容，message_id: {latest_msg.id}")
        merged_content = current_content + new_content
        latest_msg.content = merged_content
        await session.commit()
        return HandleAIMessageResponse(ok=0, failed="", message_id=latest_msg.id, content=merged_content)
        
    except Exception as e:
        await session.rollback()
        logger.error(f"处理AI消息失败: {e}", exc_info=True)
        return HandleAIMessageResponse(ok=1, failed=str(e), message_id=None, content=None)

@with_async_session
async def get_project_detail_by_id_sql(session, project_id: int):
    """
    根据项目ID查询项目详情（返回所有字段）
    """
    try:
        project = await session.get(ProjectModel, project_id)
        if not project:
            return None
        return {
            'name': project.name,
            'created_at': project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else '',
            'updated_at': project.updated_at.strftime('%Y-%m-%d %H:%M:%S') if project.updated_at else '',
            'project_code': project.project_code,
            'short_name': project.short_name,
            'description': project.description,
            'project_type': project.project_type,
            'indication': project.indication,
            'study_phase': project.study_phase,
            'is_multicenter': project.is_multicenter,
            'registration_number': project.registration_number,
            'registration_platform_url': project.registration_platform_url,
            'principal_investigator': project.principal_investigator,
            'pi_email': project.pi_email,
            'doctor_enrollment_count': project.doctor_enrollment_count,
            'patient_enrollment_count': project.patient_enrollment_count,
            'hospital': project.hospital,
            'phone': project.phone,
            'status': project.status
        }
    except Exception as e:
        logger.error(f"查询项目详情失败: {e}", exc_info=True)
        return None

@with_async_session
async def get_project_stage_stats_sql(session, project_id: int):
    """
    统计项目下病人资料和测序数据的覆盖率与阶段进展
    """
    try:
        # 获取项目表的patient_enrollment_count
        project = await session.get(ProjectModel, project_id)
        if not project:
            return None
        patient_enrollment_count = project.patient_enrollment_count
        # 获取该项目下所有病人
        patients = await session.execute(
            select(PatientModel.id).where(PatientModel.project_id == project_id)
        )
        patient_ids = [row.id for row in patients.all()]
        patient_count = len(patient_ids)
        # 统计有测序数据完成的病人数量
        seq_completed_count = 0
        if patient_count > 0:
            for pid in patient_ids:
                workflow = await session.execute(
                    select(WorkflowModel).where(
                        WorkflowModel.patient_id == pid,
                        WorkflowModel.stage == '测序数据',
                        WorkflowModel.status == 'completed'
                    )
                )
                if workflow.scalars().first():
                    seq_completed_count += 1
        return {
            "patient_info": {
                "coverage": {
                    "numerator": patient_count,
                    "denominator": patient_enrollment_count
                },
                "progress": {
                    "numerator": patient_count,
                    "denominator": patient_count
                }
            },
            "sequencing_data": {
                "coverage": {
                    "numerator": patient_count,
                    "denominator": patient_enrollment_count
                },
                "progress": {
                    "numerator": seq_completed_count if patient_count > 0 else 0,
                    "denominator": patient_count
                }
            }
        }
    except Exception as e:
        logger.error(f"统计项目阶段进展失败: {e}", exc_info=True)
        return None

@with_async_session
async def get_task_queue_status_sql(session, patient_id: int):
    """
    查询该病人下所有任务的排队顺序和预计等待时间（只查一次数据库）
    """
    tasks = await session.execute(
        select(TaskQueueModel).where(TaskQueueModel.patient_id == patient_id).order_by(asc(TaskQueueModel.id))
    )
    tasks = tasks.scalars().all()
    now = datetime.utcnow()
    result = []
    for task in tasks:
        # 只查一次，获取所有id更小且status为queued/running的任务
        prev_tasks = await session.execute(
            select(TaskQueueModel).where(
                TaskQueueModel.patient_id == patient_id,
                TaskQueueModel.id < task.id,
                TaskQueueModel.status.in_(["queued", "running"])
            ).order_by(asc(TaskQueueModel.id))
        )
        prev_tasks = prev_tasks.scalars().all()
        queue_position = len(prev_tasks)
        wait_time = 0
        for t in prev_tasks:
            if t.status == 'queued':
                wait_time += t.estimated_time
            elif t.status == 'running':
                elapsed = (now - t.started_at).total_seconds() if t.started_at else 0
                remain = t.estimated_time - elapsed
                wait_time += remain if remain > 0 else 0
        result.append({
            "task_id": task.id,
            "celery_task_id": task.celery_task_id,
            "status": task.status,
            "queue_position": queue_position,
            "wait_time": int(wait_time)
        })
    return result

@with_async_session
async def insert_task_queue_record(session, celery_task_id: str, patient_id: int, conversation_id: int):
    """
    在任务发出后插入task_queue记录，包含celery_task_id、patient_id、conversation_id和初始状态queued。
    """
    task = TaskQueueModel(
        celery_task_id=celery_task_id,
        patient_id=patient_id,
        conversation_id=conversation_id,
        estimated_time=1000,#0.0427*肽段条数
        status='queued'
    )
    session.add(task)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        # 已有记录，忽略即可