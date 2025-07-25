import httpx

from fastapi import Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from fastapi import HTTPException

from src.utils.mysql_db import *
from src.utils.session import get_async_db
from .protocols import *
from src.utils.jwt_util import decode_vaild
from src.utils import logger
from src.api.protocols import (
    CreateConversationRequest,
    CreateConversationResponse,
    PredictionDetailListResponse,
    PredictionDetailItem,
    HandleAIMessageRequest,
    HandleAIMessageResponse,
    GetProjectDetailRequest,
    GetProjectDetailResponse,
    ProjectDetailInfo,
    GetProjectStageStatsRequest,
    GetProjectStageStatsResponse,
    ProjectFullListResponse,
    ProjectFullInfo,
    PatientFullListResponse,
    PatientFullInfo,
    TaskQueueStatusResponse,
    TaskQueueStatusItem,
    DeleteSessionRequest,
    QuerySingleSessionRequest,
    VcfParseRequest, VcfParseResponse
)
from src.config import g_config 
from src.db import WorkflowModel
from src.api.protocols import UploadTumorNormalFilesResponse
from src.utils.utils import read_excel_from_minio_to_dictlist, read_excel_from_minio_to_dictlist_fasta



# from src.demo.insert_guide_demo import insert_guide_demo

security = HTTPBearer()

#用户注册
async def add_user(
        request: AddUserRequest = None,
):
    return await add_user_sql(request)


# 创建病历
async def create_medical_records(
        session: AsyncSession = Depends(get_async_db),
        request: CreateMedicalRecordRequest = Body(...),
        credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    创建新的病历记录
    Args:
        request: 创建病历请求对象（需包含project_id等字段）
        credentials: HTTP认证凭据
        session: 数据库会话
    Returns:
        CreateMedicalRecordResponse实例
    """
    try:
        # 验证token
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if unionid is None:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        # 创建病历记录
        result = await create_medical_records_sql(session, request, unionid)
        
        # 如果创建病历成功，创建工作流记录
        if result.ok == 0 and result.patient_id and request.patient_id=="":
            # 创建3个不同stage的工作流记录
            workflow_stages = [
                {'stage': '病历上传', 'rank': 1, 'status': 'completed'},
                {'stage': '测序数据', 'rank': 2, 'status': 'new'},
                {'stage': '新抗原预测', 'rank': 3, 'status': 'new'}
            ]
            workflows = []
            
            for stage_info in workflow_stages:
                workflow = WorkflowModel(
                    patient_id=result.patient_id,
                    stage=stage_info['stage'],
                    rank=stage_info['rank'],
                    status=stage_info['status'],
                    started_by=unionid,
                    started_at=func.now()
                )
                workflows.append(workflow)
            
            # 批量添加所有工作流记录
            session.add_all(workflows)
            await session.commit()
            
        return result
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"创建病历失败: {e}", exc_info=True)
        return CreateMedicalRecordResponse(
            ok=1,
            failed=str(e),
            patient_id=None
        )

# 查询用户下所有病人及其文件信息
async def get_user_patients_info(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserPatientsFilesResponse:
    """
    通过token获取unionid，返回该用户下所有病人及其文件信息
    """
    try:
        # 1. 从header中获取token
        system_token = credentials.credentials
        # 2. 解码token，获取unionid
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        # 3. 查询数据库，获取病人及文件信息
        data = await get_patients_by_unionid_sql(unionid)
        # 4. 组装响应数据
        patients = []
        for p in data:
            files = [FileBriefInfo(**f) for f in p['files']]
            patients.append(PatientWithFilesInfo(
                patient_id=p['patient_id'],
                medical_record_number=p['medical_record_number'],
                name=p['name'],
                gender=p['gender'],
                birth_date=p['birth_date'],
                phone=p['phone'],
                email=p['email'],
                hospital=p['hospital'],
                blood_type=p['blood_type'],
                tumor_type=p['tumor_type'],
                HLA_type=p['HLA_type'],
                CDR_type=p['CDR_type'],
                treatment_state=p['treatment_state'],
                additional_info=p['additional_info'],
                status=p['status'],
                source_id=p['source_id'],
                created_at=p['created_at'],
                files=files
            ))
        return UserPatientsFilesResponse(ok=0, failed="", patients=patients)
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"查询用户病人及文件信息失败: {e}", exc_info=True)
        return UserPatientsFilesResponse(ok=1, failed=str(e), patients=[])

# 查询用户下所有病人简要信息（id和姓名）
async def get_all_patients(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> PatientBriefListResponse:
    """
    通过token获取unionid，返回该用户下所有病人的id和姓名
    """
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        # 查询数据库，获取病人id和姓名
        data = await get_patients_brief_by_unionid_sql(unionid)
        return PatientBriefListResponse(ok=0, failed="", data=data)
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"查询用户病人简要信息失败: {e}", exc_info=True)
        return PatientBriefListResponse(ok=1, failed=str(e))

async def get_patient_detail(
    request: PatientDetailRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> PatientDetailResponse:
    """
    输入病人id和token，返回该病人的详细信息（去除id、source_id、created_at）
    """
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        data = await get_patient_detail_by_id_sql(request.patient_id)
        if not data:
            return PatientDetailResponse(ok=1, failed="未找到该病人")
        return PatientDetailResponse(ok=0, failed="", data=PatientDetailInfo(**data))
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"查询病人详细信息失败: {e}", exc_info=True)
        return PatientDetailResponse(ok=1, failed=str(e))

# 创建或更新项目
async def create_project(
        session: AsyncSession = Depends(get_async_db),
        request: CreateProjectRequest = Body(...),
        credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    创建新项目或更新现有项目
    Args:
        request: 创建项目请求对象（如果包含project_id则更新，否则创建）
        credentials: HTTP认证凭据
        session: 数据库会话
    Returns:
        CreateProjectResponse实例
    """
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        # 直接传递所有字段
        return await create_project_sql(session, request, unionid)
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"创建或更新项目失败: {e}", exc_info=True)
        return CreateProjectResponse(ok=1, failed=str(e), project_id=None)

# 查询用户下所有项目
async def get_projects_by_token(
    session: AsyncSession = Depends(get_async_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> ProjectFullListResponse:
    """
    通过token获取unionid，返回该用户下所有项目详细信息
    """
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        data = await get_projects_by_unionid_sql(session,unionid)
        projects = [ProjectFullInfo(**p) for p in data]
        return ProjectFullListResponse(ok=0, failed="", projects=projects)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"查询项目列表失败: {e}", exc_info=True)
        return ProjectFullListResponse(ok=1, failed=str(e), projects=[])

# 查询项目下所有病人简要信息（id和姓名）
async def get_project_patients(
    request: GetProjectPatientsRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> PatientFullListResponse:
    """
    输入项目id和token，返回该项目下所有病人详细信息
    """
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        # 查询数据库，获取该项目下病人所有字段
        data = await get_patients_brief_by_project_sql(request.project_id)
        return PatientFullListResponse(ok=0, failed="", data=[PatientFullInfo(**p) for p in data])
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"查询项目下病人简要信息失败: {e}", exc_info=True)
        return PatientFullListResponse(ok=1, failed=str(e), data=[])

async def get_patient_files(
    request: PatientDetailRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> PatientFilesResponse:
    """
    输入病人id和token，返回该病人所有文件的文件名、路径、类型和数量
    """
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        
        # 调用数据库函数，传入file_type
        data = await get_patient_files_sql(request.patient_id, request.file_type)
        
        files = [FileInfo(
            file_name=f["file_name"],
            file_path=f["file_path"],
            file_type=f["file_type"],
            file_desc=f["file_desc"],
            file_source=f["file_source"]
        ) for f in data["files"]]
        return PatientFilesResponse(ok=0, failed="", files=files, total=data["total"])
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"查询病人文件失败: {e}", exc_info=True)
        return PatientFilesResponse(ok=1, failed=str(e), files=[], total=0)

# 新增：创建会话接口
async def create_conversation(
    request: CreateConversationRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CreateConversationResponse:
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        # 如果病人id为空，通过unionid创建会话表，conversation_type赋值为qa_predict_neo
        if not request.patient_id:
            conversation_id = await get_conversation_id_by_unionid_and_type_sql(unionid, "qa_predict_neo")
            if conversation_id:
                return CreateConversationResponse(ok=0, failed="", conversation_id=conversation_id)

            # 创建会话
            result = await create_conversation_sql(
                patient_id=None,  # 
                unionid=unionid,
                conversation_type=request.conversation_type,
                title=request.title
            )
            if result["ok"] != 0:
                return CreateConversationResponse(ok=1, failed=result["failed"], conversation_id=None)
            return CreateConversationResponse(ok=0, failed="", conversation_id=result["conversation_id"])

        # 新增逻辑：如果已存在predict_neo_antigen类型的会话，直接返回
        if request.conversation_type == "predict_neo_antigen":
            conversation_id = await get_conversation_id_by_patient_and_type_sql(int(request.patient_id), "predict_neo_antigen")
            if conversation_id:
                return CreateConversationResponse(ok=0, failed="", conversation_id=conversation_id)

        # 创建会话
        result = await create_conversation_sql(
            patient_id=int(request.patient_id),
            unionid=unionid,
            conversation_type=request.conversation_type,
            title=request.title
        )
        if result["ok"] != 0:
            return CreateConversationResponse(ok=1, failed=result["failed"], conversation_id=None)
        return CreateConversationResponse(ok=0, failed="", conversation_id=result["conversation_id"])
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"创建会话失败: {e}", exc_info=True)
        return CreateConversationResponse(ok=1, failed=str(e), conversation_id=None)

async def get_conversation_messages(
    request: GetConversationMessagesRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_db),
) -> ConversationMessagesResponse:
    """
    获取指定病人和会话类型下的所有消息记录。
    Args:
        request: 包含 patient_id 和 conversation_type 的请求体。
        credentials: 用户认证凭据，用于验证用户身份。
        session: 数据库会话
    Returns:
        返回一个包含消息列表的响应对象。
    """
    try:
        # 1. 验证用户token
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        # 2. 查找conversation_id
        conversation_id = await get_conversation_id_by_patient_and_type_sql(request.patient_id, request.conversation_type)
        if not conversation_id:
            return ConversationMessagesResponse(ok=0, failed="未找到对应会话", conversation_id=None, messages=[])
        # 3. 从数据库获取消息数据
        messages_data = await get_messages_by_conversation_id_sql(conversation_id)
        # 4. 将原始数据转换为Pydantic模型列表
        messages = [MessageInfo(**msg) for msg in messages_data]
        # 5. 返回成功响应
        return ConversationMessagesResponse(ok=0, failed="", conversation_id=conversation_id, messages=messages)
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"获取会话消息失败: {e}", exc_info=True)
        return ConversationMessagesResponse(ok=1, failed=str(e), conversation_id=None, messages=[])

async def get_workflow_status(
    request: GetWorkflowStatusRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> GetWorkflowStatusResponse:
    """
    获取指定病人的所有工作流状态
    """
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        
        data = await get_workflow_status_by_patient_id_sql(request.patient_id)
        if not data:
            return GetWorkflowStatusResponse(ok=1, failed="未找到该病人的工作流信息", data=None)
        
        # 将数据转换为WorkflowStatusInfo列表
        workflow_status_list = [WorkflowStatusInfo(**item) for item in data]
        return GetWorkflowStatusResponse(ok=0, failed="", data=workflow_status_list)
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"获取工作流状态失败: {e}", exc_info=True)
        return GetWorkflowStatusResponse(ok=1, failed=str(e), data=None)

# 新增：获取病人下所有PredictionDetailModel详情
async def get_patient_prediction_details(
    request: PatientDetailRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> PredictionDetailListResponse:
    """
    输入病人id和token，返回该病人下所有预测表及其细节，分组展示
    """
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        data = await get_prediction_groups_by_patient_id_sql(request.patient_id)
        groups = [PredictionGroup(
            prediction_id=group["prediction_id"],
            create_time=group["create_time"],
            prediction_details=[PredictionDetailItem(**item) for item in group["prediction_details"]]
        ) for group in data]
        
        # 计算flag值：时间最新的PredictionGroup中最大rank对应的flag值
        flag = 0
        if groups:
            latest_group = groups[0]  # 按时间降序，第一个就是最新的
            if latest_group.prediction_details:
                # 找到最大rank的PredictionDetailItem
                max_rank_detail = max(latest_group.prediction_details, key=lambda x: x.rank)
                flag = max_rank_detail.flag
        
        return PredictionDetailListResponse(ok=0, failed="", details=groups, flag=flag)
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"查询病人PredictionGroup失败: {e}", exc_info=True)
        return PredictionDetailListResponse(ok=1, failed=str(e), details=[], flag=0)

# 新增：处理工具输入输出参数
async def handle_tool_input_output(
    request: ToolInputOutputRequest = Body(...)
) -> ToolInputOutputResponse:
    """
    处理工具输入输出参数（无token验证）
    Args:
        request: 工具输入输出请求对象
    Returns:
        ToolInputOutputResponse实例
    """
    try:
        # 验证工具名称
        valid_tools = ["BigMHC_IM", "NetChop", "NetCTLpan", "NetMHCPan"]
        if request.tool_name not in valid_tools:
            return ToolInputOutputResponse(ok=1, failed=f"无效的工具名称，支持的工具：{', '.join(valid_tools)}", predict_detail_id=None)
        
        # 验证mode值
        if request.mode not in [0, 1]:
            return ToolInputOutputResponse(ok=1, failed="无效的mode值，只能是0（输入参数）或1（输出结果）", predict_detail_id=None)
        
        # 处理工具输入输出
        result = await handle_tool_input_output_sql(request)
        return result
        
    except Exception as e:
        logger.error(f"处理工具输入输出失败: {e}", exc_info=True)
        return ToolInputOutputResponse(ok=1, failed=str(e), predict_detail_id=None)

# 新增：处理AI消息接口
async def handle_ai_message_url(
    request: HandleAIMessageRequest = Body(...)
) -> HandleAIMessageResponse:
    """
    处理AI消息：如果最新消息不是assistant则新建，否则追加内容。
    Args:
        request: HandleAIMessageRequest
    Returns:
        HandleAIMessageResponse
    """
    try:
        result = await handle_ai_message_sql(request)
        return result
    except Exception as e:
        logger.error(f"处理AI消息失败: {e}", exc_info=True)
        return HandleAIMessageResponse(ok=1, failed=str(e), message_id=None, content=None)

# 展示项目内容信息接口
async def get_project_detail(
    request: GetProjectDetailRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_db),
) -> GetProjectDetailResponse:
    """
    输入token和project_id，返回项目详情（包含所有字段信息）
    """
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        data = await get_project_detail_by_id_sql(request.project_id)
        if not data:
            return GetProjectDetailResponse(ok=1, failed="未找到该项目", data=None)
        return GetProjectDetailResponse(ok=0, failed="", data=ProjectDetailInfo(**data))
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"查询项目详情失败: {e}", exc_info=True)
        return GetProjectDetailResponse(ok=1, failed=str(e), data=None)

# 项目阶段统计接口
async def get_project_stage_stats(
    request: GetProjectStageStatsRequest = Body(...),
    session: AsyncSession = Depends(get_async_db),
) -> GetProjectStageStatsResponse:
    """
    输入项目id，输出病人资料和测序数据的覆盖率与阶段进展
    """
    try:
        data = await get_project_stage_stats_sql(request.project_id)
        if not data:
            return GetProjectStageStatsResponse(ok=1, failed="未找到该项目或统计失败", data=None)
        return GetProjectStageStatsResponse(ok=0, failed="", data=data)
    except Exception as e:
        logger.error(f"项目阶段统计失败: {e}", exc_info=True)
        return GetProjectStageStatsResponse(ok=1, failed=str(e), data=None)


async def get_task_queue_status(
    request: TaskQueueStatusRequest = Body(...)
) -> TaskQueueStatusResponse:
    """
    获取该病人下所有任务的排队顺序和预计等待时间（POST请求，参数通过Body传递）
    """
    tasks = await get_task_queue_status_sql(request.conversation_id)
    return TaskQueueStatusResponse(ok=0, failed="", tasks=[TaskQueueStatusItem(**t) for t in tasks])


#删除单一会话
async def delete_specific_session(
        request: DeleteSessionRequest = Body(...),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_async_db)
):
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        return await delete_specific_session_sql(session,request,unionid)
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"删除单一会话: {e}", exc_info=True)
        return BaseResponse(ok=1, failed=str(e))
    
#清空所有会话
async def delete_sessions(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_async_db)
):
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        return await delete_sessions_sql(session,unionid)
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"删除所有会话: {e}", exc_info=True)
        return BaseResponse(ok=1, failed=str(e))
    

#查询单一会话
async def search_specific_session(
        request: QuerySingleSessionRequest = Body(...),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_async_db)
):
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        return await search_specific_session_sql(session,request)
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"查询单一会话: {e}", exc_info=True)
        return BaseResponse(ok=1, failed=str(e))
    

#查询会话历史
async def search_sessions(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_async_db)
):
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        return await search_sessions_sql(session,unionid)
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"查询单一会话: {e}", exc_info=True)
        return BaseResponse(ok=1, failed=str(e))
    
#新建会话记录
async def add_sessions(
        session: AsyncSession = Depends(get_async_db),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        request: AddSessionRequest = Body(...)        
):
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        return await add_sessions_sql(session,request,unionid) 
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"新建会话失败: {e}", exc_info=True)
        return BaseResponse(ok=1, failed=str(e))
    
#返回会话id
async def get_new_session_id(
        credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        return await get_new_session_id_sql(unionid)

    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"新建会话失败: {e}", exc_info=True)
        return BaseResponse(ok=1, failed=str(e))
    
#更改会话名称
async def update_session_name(
        session: AsyncSession = Depends(get_async_db),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        request: UpdateSessionRequest = Body(...)        
):
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        return await update_session_name_sql(session,request,unionid)
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"更改会话失败: {e}", exc_info=True)
        return BaseResponse(ok=1, failed=str(e))
    

async def reset_conversation(
        session: AsyncSession = Depends(get_async_db),
        credentials: HTTPAuthorizationCredentials = Depends(security),
        request: ResetConversationRequest = Body(...)
):
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        return await reset_conversation_sql(session,request,unionid)    
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"新建会话失败: {e}", exc_info=True)
        return BaseResponse(ok=1, failed=str(e))

async def upload_tumor_normal_files_api(
    patient_id: int,
    unionid: str,
    tumor_file_name: str,
    tumor_file_type: str,
    tumor_file_size: int,
    tumor_file_path: str,
    tumor_file_hash: str,
    tumor_file_desc: str,
    normal_file_path: str
) -> UploadTumorNormalFilesResponse:
    inserted_file = await insert_patient_file_sql(
        patient_id=patient_id,
        unionid=unionid,
        file_name=tumor_file_name,
        file_type=tumor_file_type,
        file_size=tumor_file_size,
        file_path=tumor_file_path,
        file_hash=tumor_file_hash,
        file_desc=tumor_file_desc
    )
    return UploadTumorNormalFilesResponse(
        ok=0,
        failed="",
        tumor_file_name=inserted_file.file_name,
        tumor_created_at=str(inserted_file.created_at),
        tumor_file_size=inserted_file.file_size,
        tumor_file_desc=inserted_file.file_desc,
        normal_file_path=normal_file_path,
        tumor_file_path=tumor_file_path
    )

async def vcf_file_parse(
    request: VcfParseRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_db)
) -> VcfParseResponse:
    """
    VCF文件解析接口：
    1. 调用外部vcfswitch服务，获取excel的minio路径
    2. 用read_excel_from_minio_to_dictlist_fasta处理excel，得到list和fasta minio路径
    3. 两个文件都入库
    4. 返回excel的list和fasta的minio路径
    """
    try:
        # 1. 获取unionid
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        target_url = g_config["url"]["target_vcfswitch_url"]
        # 2. 调用外部vcfswitch
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                target_url,
                json={
                    "normal_file": request.normal_file,
                    "tumor_file": request.tumor_file
                }
            )
            if resp.status_code != 200:
                return VcfParseResponse(ok=1, failed=f"vcfswitch服务异常: {resp.text}")
            data = resp.json()
            excel_minio_path = data.get("url")
            if not excel_minio_path:
                return VcfParseResponse(ok=1, failed="vcfswitch未返回excel路径")

        # 3. 处理excel，得到list和fasta minio路径
        bucket_name = excel_minio_path.split("/")[2]  # minio://bucket/xxx
        result = await read_excel_from_minio_to_dictlist_fasta(excel_minio_path, bucket_name)
        excel_data = result["excel_data"]
        source_file_info = result["source_file_info"]
        fasta_file_info = result["fasta_file_info"]

        # 4. 两个文件都入库
        await insert_patient_file_sql(
            patient_id=request.patient_id,
            unionid=unionid,
            file_name=source_file_info["file_name"],
            file_type=source_file_info["file_type"],
            file_size=source_file_info["file_size"],
            file_path=source_file_info["file_path"],
            file_hash=source_file_info["file_hash"],
            file_desc=source_file_info["file_desc"],
            file_source=source_file_info["file_source"]
        )
        await insert_patient_file_sql(
            patient_id=request.patient_id,
            unionid=unionid,
            file_name=fasta_file_info["file_name"],
            file_type=fasta_file_info["file_type"],
            file_size=fasta_file_info["file_size"],
            file_path=fasta_file_info["file_path"],
            file_hash=fasta_file_info["file_hash"],
            file_desc=fasta_file_info["file_desc"],
            file_source=fasta_file_info["file_source"]
        )

        # 5. 返回
        return VcfParseResponse(
            ok=0,
            failed="",
            excel_data=excel_data,
            fasta_file_minio_path=fasta_file_info["file_path"]
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        return VcfParseResponse(ok=1, failed=str(e), excel_data=[], fasta_file_minio_path="")

# 新增：根据minio路径读取excel并返回字典列表
async def excel_to_dictlist_api(
    request: ExcelToDictListRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> ExcelToDictListResponse:
    try:
        # 校验token
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")
        # 调用工具函数
        result = await read_excel_from_minio_to_dictlist(request.excel_minio_uri)
        return ExcelToDictListResponse(ok=0, failed="", excel_data=result["excel_data"])
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"excel_to_dictlist_api失败: {e}", exc_info=True)
        return ExcelToDictListResponse(ok=1, failed=str(e), excel_data=[])