import asyncio
import httpx
import json
import os
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from celery import Celery
from fastapi import Depends, FastAPI, Request, HTTPException,status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.api import (
    add_user,
    create_medical_records,
    get_project_patients,
    get_patient_detail,
    create_project,
    get_projects_by_token,
    get_patient_files,
    create_conversation,
    get_conversation_messages,
    get_workflow_status,
    get_patient_prediction_details,
    handle_tool_input_output,
    handle_ai_message_url,
    get_project_detail,
    get_project_stage_stats,
    get_task_queue_status,
    delete_specific_session,
    delete_sessions,
    search_specific_session,
    search_sessions,
    add_sessions,
    get_new_session_id,
    update_session_name,
    reset_conversation,
    vcf_file_parse,
    excel_to_dictlist_api,
)
from src.api.protocols import (
    UserInput, 
    AddUserRequest, 
    PredictUserInputRequest, 
    PredictUserInputAgentRequest,
    CustomPredictUserInputRequest, 
    VcfParseRequest, 
    VcfParseResponse,
)
from src.api.api import insert_user_input_chat
from src.db.conversation_model import ConversationModel
from src.db.patient_model import PatientModel
from src.db.workflows_model import WorkflowModel
from src.db.prediction_model import PredictionModel
from src.db.file_model import FileModel
from src.config import g_config
from src.file.download_router import router as download_router
from src.file.display_router import router as display_router
from src.file.upload_sequence_files_router import router as upload_router
from src.file.extract_patient_info_router import router as extract_router
from src.file.markdown_download_router import router as markdown_download_file
from src.file.delete_router import router as delete_file_router
from src.file.upload_tumor_normal_files_router import router as tumor_normal_upload_router
from src.model.openai_engine import proxy_stream_generator
from src.utils import logger
from src.utils.jwt_util import create_system_token, decode_vaild
from src.utils.mysql_db import (
    search_unionid_sql,
    insert_message_sql,
    get_conversation_id_by_patient_and_type_sql,
    insert_task_queue_record,
    update_conversation_title_and_time,
)
from src.utils.minio import download_from_minio_uri
from src.utils.utils import (
    count_peptides,
    sliding_window_from_file,
    deduplicate_fasta_by_sequence,
)
from src.utils.session import get_async_db, get_async_session_local
from src.utils.celery_task_agent import celery_agent

logger.info(f"========================start neo backend==============================")

app = FastAPI()

security = HTTPBearer()

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

load_dotenv()
# 微信开放平台应用的 AppID 和 AppSecret
NEO_PRD_WECHAT_APP_ID = os.getenv("NEO_PRD_WECHAT_APP_ID", "")
NEO_PRD_WECHAT_APP_SECRET = os.getenv("NEO_PRD_WECHAT_APP_SECRET", "")
NEO_PRD_M_WECHAT_APP_ID = os.getenv("NEO_PRD_M_WECHAT_APP_ID", "")
NEO_PRD_M_WECHAT_APP_SECRET = os.getenv("NEO_PRD_M_WECHAT_APP_SECRET", "")

MOLLY_PRD_WECHAT_APP_ID = os.getenv("MOLLY_PRD_WECHAT_APP_ID", "")
MOLLY_PRD_WECHAT_APP_SECRET = os.getenv("MOLLY_PRD_WECHAT_APP_SECRET", "")

MOLLY_STG_WECHAT_APP_ID = os.getenv("MOLLY_STG_WECHAT_APP_ID", "")
MOLLY_STG_WECHAT_APP_SECRET = os.getenv("MOLLY_STG_WECHAT_APP_SECRET", "")
MOLLY_STG_M_WECHAT_APP_ID = os.getenv("MOLLY_STG_M_WECHAT_APP_ID", "")
MOLLY_STG_M_WECHAT_APP_SECRET = os.getenv("MOLLY_STG_M_WECHAT_APP_SECRET", "")

WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")
M_WECHAT_APP_ID = os.getenv("M_WECHAT_APP_ID", "")
M_WECHAT_APP_SECRET = os.getenv("M_WECHAT_APP_SECRET", "")

# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "")  # 用于签名和验证 JWT 的密钥
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # 加密算法
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))  # JWT Token 过期时间

@app.get("/")
def read_root():
    return {"Hello": "我是Molly后端服务"}
@app.get("/backend/wechat_callback")
async def wechat_callback(app_id: str, code: str,state: Optional[str] = None) -> Dict[str, Any]:
    """
    处理微信授权回调
    Args:
        code: 微信授权返回的code
    Returns:
        Dict containing authentication response
    """
    WECHAT_APP_ID = ""
    WECHAT_APP_SECRET = ""
    if app_id == NEO_PRD_WECHAT_APP_ID:
        WECHAT_APP_ID = NEO_PRD_WECHAT_APP_ID
        WECHAT_APP_SECRET = NEO_PRD_WECHAT_APP_SECRET
    elif app_id == NEO_PRD_M_WECHAT_APP_ID:
        WECHAT_APP_ID = NEO_PRD_M_WECHAT_APP_ID
        WECHAT_APP_SECRET = NEO_PRD_M_WECHAT_APP_SECRET
    elif app_id == MOLLY_PRD_WECHAT_APP_ID:
        WECHAT_APP_ID = MOLLY_PRD_WECHAT_APP_ID
        WECHAT_APP_SECRET = MOLLY_PRD_WECHAT_APP_SECRET
    elif app_id == MOLLY_STG_WECHAT_APP_ID:
        WECHAT_APP_ID = MOLLY_STG_WECHAT_APP_ID
        WECHAT_APP_SECRET = MOLLY_STG_WECHAT_APP_SECRET
    elif app_id == MOLLY_STG_M_WECHAT_APP_ID:
        WECHAT_APP_ID = MOLLY_STG_M_WECHAT_APP_ID
        WECHAT_APP_SECRET = MOLLY_STG_M_WECHAT_APP_SECRET

    # 1. 使用 code 获取 access_token
    token_url = f"https://api.weixin.qq.com/sns/oauth2/access_token?appid={WECHAT_APP_ID}&secret={WECHAT_APP_SECRET}&code={code}&grant_type=authorization_code"
    async with httpx.AsyncClient() as client:
        response = await client.get(token_url)
        token_data = response.json()
        if "errcode" in token_data:
            return {
                "ok": "1",
                "failed": f"微信API错误: {token_data.get('errmsg', '未知错误')}"
            }

    # 获取unionid
    unionid = token_data.get("unionid")
    if not unionid:
        return {
            "ok": "1",
            "failed": "未获取到unionid"
        }

    # 2. 使用 access_token 获取用户信息
    user_info_url = f"https://api.weixin.qq.com/sns/userinfo?access_token={token_data['access_token']}&openid={token_data['openid']}"
    async with httpx.AsyncClient() as client:
        response = await client.get(user_info_url)
        user_info = response.json()

    if "errcode" in user_info:
        return {
            "ok": "1",
            "failed": user_info["errmsg"]
        }

    # 3. 验证邀请人（如果存在state）
    role = ""  
    inviter_unionid = None
    if state:
        # 4.1 验证邀请人是否存在且是主任医师
        inviter = await search_unionid_sql(state)
        if inviter and inviter.role == "chief":
            inviter_unionid = state
            logger.info(f"有效邀请: 用户 {unionid} 被 {inviter_unionid} 邀请")
        # 判断用户表是否已经存在记录
            user = await search_unionid_sql(unionid=unionid)
            if not user:
            # 创建 AddUserRequest 实例
                add_user_request = AddUserRequest(
                    unionid=user_info.get("unionid"),  # 用户统一标识（必填）
                    openid=user_info.get("openid"),    # 普通用户的标识（必填）
                    role="assistant",
                    nickname=user_info.get("nickname"),  # 普通用户昵称（可选）
                    province=user_info.get("province"),  # 普通用户个人资料填写的省份（可选）
                    city=user_info.get("city"),          # 普通用户个人资料填写的城市（可选）
                    country=user_info.get("country"),    # 国家，如中国为CN（可选）
                    headimgurl=user_info.get("headimgurl"),  # 用户头像 URL（可选）
                    created_by=inviter_unionid  ,     # 邀请人unionid
                    is_active=True,
                    phone=None,  # TODO 后面需要传入的参数
                    email=None  # TODO 后面需要传入的参数
                )
                role = "assistant"
                # 3. 入库存储用户
                try:
                    await add_user(request=add_user_request)
                    # await insert_demo_conversation(user_info.get("unionid"))
                except Exception as e:
                    logger.error(f"插入示例对话失败: {e}", exc_info=True)
                    return {
                        "ok":"1",
                        "failed": "插入示例对话失败"
                        }

        else:
            logger.warning(f"无效邀请人: state={state}")
            # 可以选择返回错误或忽略邀请
            return {"ok": "1", "failed": "无效邀请人"}
        
    else:
    # 判断用户表是否已经存在记录
        user = await search_unionid_sql(unionid=unionid)
        
        if not user:
        # 创建 AddUserRequest 实例
            add_user_request = AddUserRequest(
                unionid=user_info.get("unionid"),  # 用户统一标识（必填）
                openid=user_info.get("openid"),    # 普通用户的标识（必填）
                role="chief",
                nickname=user_info.get("nickname"),  # 普通用户昵称（可选）
                province=user_info.get("province"),  # 普通用户个人资料填写的省份（可选）
                city=user_info.get("city"),          # 普通用户个人资料填写的城市（可选）
                country=user_info.get("country"),    # 国家，如中国为CN（可选）
                headimgurl=user_info.get("headimgurl"),  # 用户头像 URL（可选）
                created_by=inviter_unionid  ,     # 邀请人unionid
                is_active=True,
                phone=None,  # TODO 后面需要传入的参数
                email=None  # TODO 后面需要传入的参数
            )
            role = "chief"
            # 3. 入库存储用户
            try:
                await add_user(request=add_user_request)
                # await insert_demo_conversation(user_info.get("unionid"))
            except Exception as e:
                logger.error(f"插入示例对话失败: {e}", exc_info=True)
                return {
                    "ok":"1",
                    "failed": "插入示例对话失败"
                    }
        else:
            role = user.role    
    # 生成自身系统的 JWT Token,并存入user_token表中
    system_token = await create_system_token(unionid=unionid, wechat_access_token=token_data['access_token'])

    # 返回成功响应
    return {
        "ok": 0,
        "failed": "",
        "system_token": system_token,
        "unionid": user_info.get("unionid"),
        "headimgurl": user_info.get("headimgurl"),
        "nickname": user_info.get("nickname"),
        "role": role
    }

#默认工具参数预测接口
@app.post("/backend/predict_antigen_chat")
async def backend_chat_with_files(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> StreamingResponse:
    """代理聊天接口，支持文件上传信息，流式转发到目标服务器"""

    async def generate_error_response(error_msg: str):
        """生成错误响应的辅助函数"""
        error_data = json.dumps({
            "type": "error",
            "content": error_msg
        })
        return StreamingResponse(
            iter([f"data: {error_data}\n\n"]),
            media_type="text/event-stream"
        )

    try:
        # 1. 解析和验证请求
        try:
            raw_body = await request.body()
            logger.info(f"Raw request body: {raw_body.decode('utf-8')}")

            body = await request.json()
            logger.info(f"Parsed JSON body: {json.dumps(body, ensure_ascii=False)}")

            user_input = PredictUserInputRequest(**body)
            logger.info(f"Validated model: {user_input.dict()}")
            
            # 判断前端是否传了parameters参数
            if 'parameters' not in body:
                logger.info("前端未传入parameters参数，将使用默认参数")
            else:
                logger.info(f"前端传入了parameters参数: {user_input.parameters}")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return await generate_error_response("Invalid JSON format")
        except ValidationError as e:
            logger.error(f"模型验证失败: {e.errors()}")
            return await generate_error_response(str(e.errors()))

        # 2. 验证token
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        # 3. 通过conversation_id查找会话和病人
        conversation_id = user_input.conversation_id
        patient_id = user_input.patient_id
        conversation = await db.get(ConversationModel, int(conversation_id))
        if not conversation:
            return await generate_error_response("会话不存在")
        patient = await db.get(PatientModel, int(patient_id))
        if not patient:
            return await generate_error_response("病人信息不存在")

        # === 新增：始终新建PredictionModel ===
        
        new_prediction = PredictionModel(
            patient_id=patient_id,
            result=None,
            summary=None
        )
        db.add(new_prediction)
        await db.commit()
        await db.refresh(new_prediction)
        prediction_id = new_prediction.id

        # 4. 处理HLA和CDR数据
        mhc_allele = None
        if patient.HLA_type:
            mhc_allele = patient.HLA_type

        cdr3 = []
        if patient.CDR_type:
            cdr3 = [cdr.strip() for cdr in patient.CDR_type.split(',') if cdr.strip()]

        # 5. 先插入一条用户消息
        await insert_message_sql(conversation_id=conversation_id, type='user',content="使用默认参数，开始预测")
        
        # 6. 更新工作流状态为pending
        # 查找对应stage的工作流记录（新抗原预测阶段，rank=3）
        workflow = await db.execute(
            select(WorkflowModel)
            .where(WorkflowModel.patient_id == int(patient_id))
            .where(WorkflowModel.stage == '新抗原预测')
            .where(WorkflowModel.rank == 3)
        )
        workflow = workflow.scalar_one_or_none()
        if workflow:
            workflow.status = 'pending'
            await db.commit()
        
        # === 关键：predict_id 一定用新建的 prediction_id ===
        agent_request = PredictUserInputAgentRequest(
            prompt="使用默认参数，开始预测",
            conversation_id=conversation_id,
            patient_id=patient_id,
            predict_id=prediction_id,
            file_path=user_input.file_path,
            mhc_allele=mhc_allele,
            cdr3=cdr3,
            parameters=user_input.parameters
        )
        #获取滑窗降重后的肽段数
        input_fasta = download_from_minio_uri(user_input.file_path)        
        sliding_window_from_file(input_fasta, [8,9,10,11], input_fasta)

        # 读取、去重、写回
        with open(input_fasta, 'r', encoding='utf-8') as f:
            fasta_content = f.read()
        deduped, total_before, total_after = deduplicate_fasta_by_sequence(fasta_content)
        print(f"滑窗得到去重前肽段总数: {total_before}")
        print(f"滑窗得到去重后肽段总数: {total_after}")
        # with open(input_fasta, 'w', encoding='utf-8') as f:
        #     f.write(deduped)
        # 定义完成回调
        async def on_complete():
            try:
                logger.info(f"开始执行on_complete回调，patient_id: {patient_id}")
                # 重新查询工作流记录
                workflow_result = await db.execute(
                    select(WorkflowModel)
                    .where(WorkflowModel.patient_id == int(patient_id))
                    .where(WorkflowModel.stage == '新抗原预测')
                    .where(WorkflowModel.rank == 3)
                )
                workflow_record = workflow_result.scalar_one_or_none()
                
                if workflow_record:
                    logger.info(f"找到工作流记录，当前状态: {workflow_record.status}")
                    workflow_record.status = 'completed'
                    workflow_record.completed_at = func.now()
                    workflow_record.completed_by = unionid
                    logger.info(f"设置状态为completed，准备提交...")
                    await db.commit()
                    logger.info(f"数据库提交完成")
                    logger.info(f"工作流状态已更新为completed，patient_id: {patient_id}")
                else:
                    logger.warning(f"未找到工作流记录，patient_id: {patient_id}")
            except Exception as e:
                logger.error(f"on_complete回调执行失败: {e}", exc_info=True)
        
        # 先插入 task_queue，celery_task_id 为空，获取主键id
        task_queue_id = await insert_task_queue_record(patient_id, conversation_id, total_after,",".join(map(str, [8,9,10,11])))
        # 发送 celery 任务，task_queue_id 作为 kwargs 传递
        result = celery_agent.send_task(
            "src.utils.celery_task_agent.run_and_consume_generator", 
            args=[
                agent_request.dict(), 
                conversation_id, 
                patient_id, 
                unionid
            ],
            kwargs={
                'task_queue_id': task_queue_id
            }
        )
        return {"ok": 0, "failed": ""}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("处理请求时发生未捕获的异常:")
        return await generate_error_response(str(e))

#用户自定义参数工具预测接口
@app.post("/backend/predict_antigen_with_custom_params")
async def predict_antigen_with_custom_params(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> StreamingResponse:
    """用户自定义参数工具预测接口，支持文件上传信息，流式转发到目标服务器"""

    async def generate_error_response(error_msg: str):
        """生成错误响应的辅助函数"""
        error_data = json.dumps({
            "type": "error",
            "content": error_msg
        })
        return StreamingResponse(
            iter([f"data: {error_data}\n\n"]),
            media_type="text/event-stream"
        )

    try:
        # 1. 解析和验证请求
        try:
            raw_body = await request.body()
            logger.info(f"Raw request body: {raw_body.decode('utf-8')}")

            body = await request.json()
            logger.info(f"Parsed JSON body: {json.dumps(body, ensure_ascii=False)}")

            user_input = CustomPredictUserInputRequest(**body)
            logger.info(f"Validated model: {user_input.dict()}")

            # 判断前端是否传了parameters参数
            if "parameters" not in body:
                logger.info("前端未传入parameters参数，将使用默认参数")
            else:
                logger.info(f"前端传入了parameters参数: {user_input.parameters}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return await generate_error_response("Invalid JSON format")
        except ValidationError as e:
            logger.error(f"模型验证失败: {e.errors()}")
            return await generate_error_response(str(e.errors()))

        # 2. 验证token
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        # 3. 通过conversation_id查找会话和病人
        conversation_id = await get_conversation_id_by_patient_and_type_sql(
            int(user_input.patient_id), "predict_neo_antigen"
        )
        patient_id = user_input.patient_id
        conversation = await db.get(ConversationModel, int(conversation_id))
        if not conversation:
            return await generate_error_response("会话不存在")
        patient = await db.get(PatientModel, int(patient_id))
        if not patient:
            return await generate_error_response("病人信息不存在")

        # === 新增：始终新建PredictionModel ===

        new_prediction = PredictionModel(
            patient_id=patient_id,
            result=None,
            summary=None
        )
        db.add(new_prediction)
        await db.commit()
        await db.refresh(new_prediction)
        prediction_id = new_prediction.id

        # 4. 处理HLA和CDR数据
        mhc_allele = None
        if patient.HLA_type:
            mhc_allele = patient.HLA_type

        cdr3 = []
        if patient.CDR_type:
            cdr3 = [cdr.strip() for cdr in patient.CDR_type.split(',') if cdr.strip()]

        # 5. 先插入一条用户消息
        await insert_message_sql(
            conversation_id=conversation_id,
            type="user",
            content="完成自定义参数收集，开始预测",
        )

        # 6. 更新工作流状态为pending
        # 查找对应stage的工作流记录（新抗原预测阶段，rank=3）
        workflow = await db.execute(
            select(WorkflowModel)
            .where(WorkflowModel.patient_id == int(patient_id))
            .where(WorkflowModel.stage == '新抗原预测')
            .where(WorkflowModel.rank == 3)
        )
        workflow = workflow.scalar_one_or_none()
        if workflow:
            workflow.status = 'pending'
            await db.commit()

        # === 关键：predict_id 一定用新建的 prediction_id ===
        if user_input.parameters['netchop']['peptide_length'] == []:
            user_input.parameters['netchop']['peptide_length'] = [-1]
            
        agent_request = PredictUserInputAgentRequest(
            prompt="完成自定义参数收集，开始预测",
            conversation_id=conversation_id,
            patient_id=patient_id,
            predict_id=prediction_id,
            file_path=user_input.parameters['netchop']['input_filename'],
            mhc_allele=mhc_allele,
            cdr3=cdr3,
            parameters=user_input.parameters
        )
        #获取滑窗降重后的肽段数
        input_fasta = download_from_minio_uri(user_input.parameters['netchop']['input_filename'])   
        window_sizes = [8, 9, 10, 11] if user_input.parameters['netchop']['peptide_length'] in ([-1]) else user_input.parameters['netchop']['peptide_length']
        sliding_window_from_file(input_fasta, window_sizes, input_fasta)

        # 读取、去重、写回
        with open(input_fasta, 'r', encoding='utf-8') as f:
            fasta_content = f.read()
        deduped, total_before, total_after = deduplicate_fasta_by_sequence(fasta_content)
        print(f"滑窗得到去重前肽段总数: {total_before}")
        print(f"滑窗得到去重后肽段总数: {total_after}")
        # with open(input_fasta, 'w', encoding='utf-8') as f:
        #     f.write(deduped)        
        #获取文件肽段数

        # 定义完成回调
        async def on_complete():
            try:
                logger.info(f"开始执行on_complete回调，patient_id: {patient_id}")
                # 重新查询工作流记录
                workflow_result = await db.execute(
                    select(WorkflowModel)
                    .where(WorkflowModel.patient_id == int(patient_id))
                    .where(WorkflowModel.stage == '新抗原预测')
                    .where(WorkflowModel.rank == 3)
                )
                workflow_record = workflow_result.scalar_one_or_none()

                if workflow_record:
                    logger.info(f"找到工作流记录，当前状态: {workflow_record.status}")
                    workflow_record.status = 'completed'
                    workflow_record.completed_at = func.now()
                    workflow_record.completed_by = unionid
                    logger.info(f"设置状态为completed，准备提交...")
                    await db.commit()
                    logger.info(f"数据库提交完成")
                    logger.info(f"工作流状态已更新为completed，patient_id: {patient_id}")
                else:
                    logger.warning(f"未找到工作流记录，patient_id: {patient_id}")
            except Exception as e:
                logger.error(f"on_complete回调执行失败: {e}", exc_info=True)

        # 先插入 task_queue，celery_task_id 为空，获取主键id
        task_queue_id = await insert_task_queue_record(patient_id, conversation_id, total_after,",".join(map(str, window_sizes)))
        # 发送 celery 任务，task_queue_id 作为 kwargs 传递
        result = celery_agent.send_task(
            "src.utils.celery_task_agent.run_and_consume_generator", 
            args=[
                agent_request.dict(), 
                conversation_id, 
                patient_id, 
                unionid
            ],
            kwargs={
                'task_queue_id': task_queue_id
            }
        )
        # 不再需要插入 task_queue，celery_task_id 由worker端补充
        return {"ok": 0, "failed": ""}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("处理请求时发生未捕获的异常:")
        return await generate_error_response(str(e))


# 存储每个会话的停止事件
stop_events: Dict[str, asyncio.Event] = {}


@app.post("/backend/chat_with_files")
async def backend_chat_with_files(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> StreamingResponse:
    """代理聊天接口，支持文件上传信息，流式转发到目标服务器"""

    async def generate_error_response(error_msg: str):
        """生成错误响应的辅助函数"""
        error_data = json.dumps({
            "type": "error",
            "content": error_msg
        })
        return StreamingResponse(
            iter([f"data: {error_data}\n\n"]),
            media_type="text/event-stream"
        )

    try:
        raw_body = await request.body()
        logger.info(f"Raw request body: {raw_body.decode('utf-8')}")

        body = await request.json()
        logger.info(
            f"Parsed JSON body: {json.dumps(body, ensure_ascii=False)}")

        user_input = UserInput(**body)
        logger.info(f"Validated model: {user_input.dict()}")

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {str(e)}")
        return await generate_error_response("Invalid JSON format")
    except ValidationError as e:
        logger.error(f"模型验证失败: {e.errors()}")
        return await generate_error_response(str(e.errors()))
    except Exception as e:
        logger.exception("未捕获的异常:")
        return await generate_error_response(str(e.errors()))
    # 提取并校验 token
    system_token = credentials.credentials  # 直接获取Token
    payload = decode_vaild(system_token,
                           SECRET_KEY, algorithms=[ALGORITHM])
    unionid: str = payload.get("sub")
    if unionid is None:
        raise HTTPException(status_code=401, detail="无效的用户认证")
    conversation_id = user_input.conversation_id
    prompt = user_input.prompt

    # 调用mysql_db.py中的函数更新会话title和更新时间
    await update_conversation_title_and_time(conversation_id, prompt)

    # 更新 conversation 和插入用户输入
    msg_id = await insert_user_input_chat(conversation_id, query=prompt)
    logger.info(f"Generated msg_id: {msg_id}")

    # 初始化停止事件
    stop_event = stop_events.setdefault(conversation_id, asyncio.Event())
    stop_event.clear()

    # 根据 conversation_id 从数据库查询所有文件
    # uploaded_files = await db.execute(
    #     select(FileModel).where(
    #         FileModel.conversation_id == conversation_id,
    #         FileModel.file_status == True,
    #         FileModel.file_type != "neo_default_file"
    #     )
    # )
    # uploaded_files = uploaded_files.scalars().all()

    # 构造 file_list
    file_groups = []
    # if uploaded_files:
    #     logger.info(
    #         f"Found {len(uploaded_files)} files for conversation_id: {conversation_id}")
    #     files = []
    #     for uploaded_file in uploaded_files:
    #         file_name, file_content = get_file_content(uploaded_file.file_path)
    #         logger.info(
    #             f"File: {file_name}, Content length: {len(file_content)}")
    #         files.append(FileInfo(
    #             file_name=file_name,
    #             file_content=file_content,
    #             file_path=uploaded_file.file_path,
    #             file_desc=uploaded_file.file_desc,
    #             file_origin=uploaded_file.file_origin
    #         ))
    #     if files:
    #         file_groups.append(
    #             FileGroup(conversation_id=conversation_id, files=files))
    #         logger.info(f"Files: {files}, file_groups: {file_groups}")
    # else:
    #     logger.warning(
    #         f"No files found in DB for conversation_id: {conversation_id}")
    # 更新 user_input.file_list
    user_input.file_list = file_groups
    logger.info(
        f"Final file_list length: {len(file_groups)} for conversation_id: {conversation_id}")
    return StreamingResponse(
        proxy_stream_generator(
            user_input, conversation_id, stop_event, stop_events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )


@app.post("/backend/stop")
async def stop(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    body = await request.body()
    try:
        # 提取并校验基础参数
        system_token = credentials.credentials
        data = json.loads(body.decode("utf-8"))
        conversation_id = data.get("conversation_id")

        # 参数校验
        if not system_token:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "ok": 1,
                    "failed": "Missing 'system_token' field"
                }
            )
        if not conversation_id:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "ok": 1,
                    "failed": "Missing 'conversation_id' field"
                }
            )
        # 校验token有效性
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if unionid is None:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "ok": 1,
                    "failed": "unionid不存在"
                }
            )
        # 设置停止事件
        if conversation_id in stop_events:
            stop_events[conversation_id].set()
        # 成功响应
        return {
            "ok": 0,
            "failed": ""
        }
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "ok": 1,
                "failed": "Invalid JSON format"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "ok": 1,
                "failed": f"Internal server error: {str(e)}"
            }
        )


app.include_router(upload_router, prefix="/backend")

app.include_router(extract_router, prefix="/backend")

app.include_router(tumor_normal_upload_router, prefix="/backend")

app.post("/backend/create_medical_records",
         tags=["病人信息"], summary="创建病历")(create_medical_records)

app.post("/backend/get_project_patients",
         tags=["病人数据"], summary="获取指定项目下的所有病人详细信息")(get_project_patients)

app.post("/backend/get_patient_detail",
         tags=["病人数据"], summary="获取指定病人详细信息（不含id/source_id/created_at）")(get_patient_detail)

app.post("/backend/create_project",
         tags=["项目管理"], summary="创建或更新项目")(create_project)

app.post("/backend/get_projects",
         tags=["项目管理"], summary="获取当前用户的所有项目列表")(get_projects_by_token)

app.post("/backend/get_patient_files",
         tags=["病人数据"], summary="获取指定病人所有文件的文件名、路径、类型和数量")(get_patient_files)

app.post("/backend/create_conversation", tags=["会话管理"], summary="新建会话")(create_conversation)

app.post("/backend/get_conversation_messages", tags=["会话管理"], summary="获取会话消息列表")(get_conversation_messages)

app.post("/backend/get_workflow_status", tags=["工作流"], summary="获取工作流状态")(get_workflow_status)

app.post("/backend/get_patient_prediction_details", tags=["预测详情"], summary="获取病人下所有预测详情")(get_patient_prediction_details)

app.post("/backend/handle_tool_input_output", tags=["agent服务器接口"], summary="处理agent服务器的工具输入输出参数")(handle_tool_input_output)

app.post("/backend/handle_ai_message", tags=["agent服务器接口"], summary="处理agent服务器的AI消息追加或新建")(handle_ai_message_url)

app.post("/backend/get_project_detail", tags=["项目管理"], summary="获取项目详情信息")(get_project_detail)

app.post("/backend/get_project_stage_stats", tags=["项目管理"], summary="获取项目阶段统计信息")(get_project_stage_stats)

# 注册任务队列状态接口
app.post("/backend/task_queue_status", tags=["任务队列"], summary="获取任务队列状态")(get_task_queue_status)

app.post("/backend/vcf_file_parse", tags=["文件处理"], summary="VCF文件解析")(vcf_file_parse)

app.post("/backend/excel_to_dictlist", tags=["文件处理"], summary="根据minio路径读取excel并返回字典列表")(excel_to_dictlist_api)

app.include_router(download_router, prefix="/backend")
app.include_router(display_router, prefix="/backend")
# app.include_router(weblogo_generate, prefix="/backend")
# app.include_router(files_migrate, prefix="/backend")
app.include_router(markdown_download_file, prefix="/backend")
app.include_router(delete_file_router, prefix="/backend")




# app.post("/query_user_info", tags=["用户数据"], summary="查询用户信息")(query_user_info)

app.post("/backend/delete_specific_session",
         tags=["会话数据"], summary="删除特定会话")(delete_specific_session)

app.post("/backend/delete_sessions",
         tags=["会话数据"], summary="删除全部会话")(delete_sessions)

app.post("/backend/search_specific_session",
         tags=["会话数据"], summary="查询单一会话")(search_specific_session)

app.post("/backend/search_sessions",
         tags=["会话数据"], summary="查询会话历史")(search_sessions)

app.post("/backend/add_sessions",
         tags=["会话数据"], summary="新建会话记录信息")(add_sessions)

app.post("/backend/get_new_session_id",
         tags=["会话数据"], summary="返回会话id")(get_new_session_id)

app.post("/backend/update_session_name",
         tags=["会话数据"], summary="更改会话名称")(update_session_name)

app.post("/backend/reset_session_messages",
         tags=["重置会话"], summary="初始化会话消息")(reset_conversation)











