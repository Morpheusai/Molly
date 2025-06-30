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
from sqlalchemy.exc import SQLAlchemyError
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
    QuestionModel,
    ToolModel,
    UserTokenModel,
    UserModel,
    WorkflowModel,
    PredictionDetailModel,
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
        return None  # 空unionid直接返回None
    
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
    """
    创建新的病历记录
    Args:
        request: 创建病历请求对象
        unionid: 创建者用户ID
    Returns:
        BaseResponse实例
    """
    try:
        # 创建新的病历记录
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
            clinical_medication=None,
            clinical_diagnosis=None,
            created_by=unionid,
            status='new',
            source_id=request.source_id if hasattr(request, 'source_id') else None
        )
        session.add(patient)
        await session.commit()
        await session.refresh(patient)

        # # 新增：创建PredictionModel记录
        # prediction = PredictionModel(
        #     patient_id=patient.id,
        #     result=None,
        #     summary=None
        # )
        # session.add(prediction)
        # await session.commit()
        # await session.refresh(prediction)

        # 新增：为该预测插入4条PredictionDetailModel记录
        # now = datetime.now()
        # details = [
        #     PredictionDetailModel(
        #         patient_id=patient.id,
        #         prediction_id=prediction.id,
        #         rank=1,
        #         tool_name="Netchop",
        #         tool_parameters={
        #             "input_filename": "minio://molly/c7cbf447-835d-4049-bfce-a0166ab8ed0d_test.fasta",
        #             "cleavage_site_threshold": 0.5,
        #             "model": 0,
        #             "format": 0,
        #             "strict": 0
        #         },
        #         status="pending",
        #         start_time=now,
        #         end_time=now,
        #         elapsed_time=None,
        #         error_message=None,
        #         tool_output={
        #             "url": "minio://netchop-results/ecdef096ea4a4d7b91373e7b04486fea_NetChop_results.xlsx",
        #             "content": "工具结果"
        #         }
        #     ),
        #     PredictionDetailModel(
        #         patient_id=patient.id,
        #         prediction_id=prediction.id,
        #         rank=2,
        #         tool_name="Netctlpan",
        #         tool_parameters={
        #             "input_filename": "minio://molly/a66b7062-b6cb-4d0a-8258-50b869ac657b_test.fasta",
        #             "mhc_allele": "HLA-A02:01,HLA-A02:02,HLA-A02:03,HLA-A02:04",
        #             "peptide_length": 9,
        #             "weight_of_tap": 0.025,
        #             "weight_of_clevage": 0.225,
        #             "epi_threshold": 1.0,
        #             "output_threshold": -99.9,
        #             "sort_by": -1
        #         },
        #         status="pending",
        #         start_time=now,
        #         end_time=now,
        #         elapsed_time=None,
        #         error_message=None,
        #         tool_output={
        #             "url": "minio://netchop-results/ecdef096ea4a4d7b91373e7b04486fea_NetChop_results.xlsx",
        #             "content": "工具结果"
        #         }
        #     ),
        #     PredictionDetailModel(
        #         patient_id=patient.id,
        #         prediction_id=prediction.id,
        #         rank=3,
        #         tool_name="Netmhcpan",
        #         tool_parameters={
        #             "input_filename": "minio://molly/c7cbf447-835d-4049-bfce-a0166ab8ed0d_test.fasta",
        #             "mhc_allele": "HLA-A02:01,HLA-A02:02",
        #             "peptide_length": -1,
        #             "high_threshold_of_bp": 0.5,
        #             "low_threshold_of_bp": 2.0,
        #             "rank_cutoff": -99.9
        #         },
        #         status="pending",
        #         start_time=now,
        #         end_time=now,
        #         elapsed_time=None,
        #         error_message=None,
        #         tool_output={
        #             "url": "minio://netchop-results/ecdef096ea4a4d7b91373e7b04486fea_NetChop_results.xlsx",
        #             "content": "工具结果"
        #         }
        #     ),
        #     PredictionDetailModel(
        #         patient_id=patient.id,
        #         prediction_id=prediction.id,
        #         rank=4,
        #         tool_name="Bigmhcpan",
        #         tool_parameters={
        #             "input_filename": "minio://molly/c7cbf447-835d-4049-bfce-a0166ab8ed0d_test.fasta",
        #             "mhc_allele": "HLA-A02:01,HLA-A02:02"
        #         },
        #         status="pending",
        #         start_time=now,
        #         end_time=now,
        #         elapsed_time=None,
        #         error_message=None,
        #         tool_output={
        #             "url": "minio://netchop-results/ecdef096ea4a4d7b91373e7b04486fea_NetChop_results.xlsx",
        #             "content": "工具结果"
        #         }
        #     )
        # ]
        # session.add_all(details)
        # await session.commit()

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
        logger.error(f"创建病历失败: {e}", exc_info=True)
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
    创建新的项目记录
    Args:
        request: 创建项目请求对象
        unionid: 创建者用户ID
    Returns:
        CreateProjectResponse实例
    """
    try:
        project = ProjectModel(
            name=request.name,
            created_by=unionid
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
        logger.error(f"创建项目失败: {e}", exc_info=True)
        return CreateProjectResponse(
            ok=1,
            failed=str(e),
            project_id=None
        )


async def get_projects_by_unionid_sql(session, unionid: str):
    """
    查询指定unionid下所有项目
    Args:
        unionid: 用户唯一标识
    Returns:
        list[dict]，每个dict包含project_id和name
    """
    try:
        projects = await session.execute(
            select(ProjectModel.id, ProjectModel.name).where(ProjectModel.created_by == unionid)
        )
        result = [
            {"project_id": row.id, "name": row.name} for row in projects.all()
        ]
        return result
    except Exception as e:
        logger.error(f"查询项目列表失败: {e}", exc_info=True)
        return []

@with_async_session
async def get_patients_brief_by_project_sql(session, project_id: int):
    """
    查询指定项目下所有病人的id和姓名
    """
    try:
        patients = await session.execute(
            select(PatientModel.id, PatientModel.name,PatientModel.medical_record_number).where(PatientModel.project_id == project_id)
        )
        result = [
            {"patient_id": row.id, "name": row.name,"medical_record_number":row.medical_record_number} for row in patients.all()
        ]
        return result
    except Exception as e:
        logger.error(f"查询项目下病人简要信息失败: {e}", exc_info=True)
        return []

@with_async_session
async def get_patient_files_sql(session, patient_id: int):
    """
    查询指定病人id下所有文件的名、路径、类型及数量
    """
    try:
        files = await session.execute(
            select(FileModel.file_name, FileModel.file_path, FileModel.file_type, FileModel.file_desc)
            .where(FileModel.patient_id == patient_id, FileModel.is_deleted == 0)
        )
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
        
    except Exception as e:
        await session.rollback()
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
        logger.error(f"插入用户消息失败: {e}", exc_info=True)
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
                    PredictionDetailModel.tool_output
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
                error_message=None
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