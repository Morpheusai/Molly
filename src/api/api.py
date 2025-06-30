from fastapi import Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from src.utils.mysql_db import *
# from src.utils.mysql_db import search_sessions_sql
from src.utils.session import get_async_db
from src.utils.session import with_async_session
from .protocols import *
from src.utils.jwt_util import decode_vaild
from src.utils import logger
from src.api.protocols import  CreateConversationRequest, CreateConversationResponse, PredictionDetailListResponse, PredictionDetailItem
from src.utils.mysql_db import create_conversation_sql, get_conversation_id_by_patient_and_type_sql
from src.db import PatientModel, WorkflowModel
from fastapi import APIRouter


# from src.demo.insert_guide_demo import insert_guide_demo

security = HTTPBearer()

#用户注册
async def add_user(
        request: AddUserRequest = None,
):
    return await add_user_sql(request)

# #查询用户信息
# async def query_user_info(
#         request: QueryUserInfoRequest = Body(...),
#         session: AsyncSession = Depends(get_async_db)
# ):
#     return await query_user_info_sql(session,request)

# #删除单一会话
# async def delete_specific_session(
#         request: DeleteSessionRequest = Body(...),
#         credentials: HTTPAuthorizationCredentials = Depends(security),
#         session: AsyncSession = Depends(get_async_db)
# ):
#     return await delete_specific_session_sql(session,credentials,request)

# #清空所有会话
# async def delete_sessions(
#         credentials: HTTPAuthorizationCredentials = Depends(security),
#         session: AsyncSession = Depends(get_async_db)
# ):
#    return await delete_sessions_sql(session,credentials)

# #查询单一会话
# async def search_specific_session(
#         request: QuerySingleSessionRequest = Body(...),
#         credentials: HTTPAuthorizationCredentials = Depends(security),
#         session: AsyncSession = Depends(get_async_db)
# ):
#     return await search_specific_session_sql(session,credentials,request)

# #查询会话历史
# async def search_sessions(
#         # request: SessionsRequest = Body(...),
#         credentials: HTTPAuthorizationCredentials = Depends(security),
#         session: AsyncSession = Depends(get_async_db)
# ):
#     return await search_sessions_sql(session,credentials)


# #新建会话记录
# async def add_sessions(
#         session: AsyncSession = Depends(get_async_db),
#         credentials: HTTPAuthorizationCredentials = Depends(security),
#         request: AddSessionRequest = Body(...)        
# ):
#     return await add_sessions_sql(session,credentials,request)

# #返回会话id
# async def get_new_session_id(
#         credentials: HTTPAuthorizationCredentials = Depends(security),
# ):
#     return await get_new_session_id_sql(credentials)



# # 使用 UPSERT 操作更新或插入 conversation 记录
# async def upsert_conversation(
#         conversation_id: str,      
#         unionid: str,
#         prompt:str
# ):
#     return await upsert_conversation_sql(conversation_id, unionid,prompt)

# #更改会话名称
# async def update_session_name(
#         session: AsyncSession = Depends(get_async_db),
#         credentials: HTTPAuthorizationCredentials = Depends(security),
#         request: UpdateSessionRequest = Body(...)        
# ):
#     return await update_session_name_sql(session,credentials,request)

# #插入demo示例
# async def insert_demo_conversation(
#         user_id: str
# ):
#     return await insert_guide_demo(user_id)


# # 使用 update 操作更新uploadfiles的file_type字段值
# async def update_uploadfiles_file_type(
#         file_paths: list[str],      
#         conversation_id: str,
# ):
#         return await update_uploadfiles_file_type_sql(file_paths,conversation_id)

# # 
# async def reset_conversation(
#         session: AsyncSession = Depends(get_async_db),
#         credentials: HTTPAuthorizationCredentials = Depends(security),
#         request: ResetConversationRequest = Body(...)
# ):
#         return await reset_conversation_sql(session,credentials,request)

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
            return CreateMedicalRecordResponse(
                ok=1,
                failed="无效的用户认证",
                patient_id=None
            )
        # 创建病历记录
        result = await create_medical_records_sql(session, request, unionid)
        
        # 如果创建病历成功，创建工作流记录
        if result.ok == 0 and result.patient_id:
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
            return UserPatientsFilesResponse(ok=1, failed="无效的用户认证", patients=[])
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
            return PatientBriefListResponse(ok=1, failed="无效的用户认证")
        # 查询数据库，获取病人id和姓名
        data = await get_patients_brief_by_unionid_sql(unionid)
        return PatientBriefListResponse(ok=0, failed="", data=data)
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
            return PatientDetailResponse(ok=1, failed="无效的用户认证")
        data = await get_patient_detail_by_id_sql(request.patient_id)
        if not data:
            return PatientDetailResponse(ok=1, failed="未找到该病人")
        return PatientDetailResponse(ok=0, failed="", data=PatientDetailInfo(**data))
    except Exception as e:
        logger.error(f"查询病人详细信息失败: {e}", exc_info=True)
        return PatientDetailResponse(ok=1, failed=str(e))

# 创建项目
async def create_project(
        session: AsyncSession = Depends(get_async_db),
        request: CreateProjectRequest = Body(...),
        credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    创建新的项目
    Args:
        request: 创建项目请求对象
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
            return CreateProjectResponse(ok=1, failed="无效的用户认证", project_id=None)
        return await create_project_sql(session, request, unionid)
    except Exception as e:
        logger.error(f"创建项目失败: {e}", exc_info=True)
        return CreateProjectResponse(ok=1, failed=str(e), project_id=None)

# 查询用户下所有项目
async def get_projects_by_token(
    session: AsyncSession = Depends(get_async_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> ProjectListResponse:
    """
    通过token获取unionid，返回该用户下所有项目名称
    """
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            return ProjectListResponse(ok=1, failed="无效的用户认证", projects=[])
        data = await get_projects_by_unionid_sql(session,unionid)
        projects = [ProjectInfo(**p) for p in data]
        return ProjectListResponse(ok=0, failed="", projects=projects)
    except Exception as e:
        logger.error(f"查询项目列表失败: {e}", exc_info=True)
        return ProjectListResponse(ok=1, failed=str(e), projects=[])

# 查询项目下所有病人简要信息（id和姓名）
async def get_project_patients(
    request: GetProjectPatientsRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> PatientBriefListResponse:
    """
    输入项目id和token，返回该项目下所有病人的id和姓名
    """
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            return PatientBriefListResponse(ok=1, failed="无效的用户认证")
        # 查询数据库，获取该项目下病人id和姓名
        data = await get_patients_brief_by_project_sql(request.project_id)
        return PatientBriefListResponse(ok=0, failed="", data=data)
    except Exception as e:
        logger.error(f"查询项目下病人简要信息失败: {e}", exc_info=True)
        return PatientBriefListResponse(ok=1, failed=str(e))

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
            return PatientFilesResponse(ok=1, failed="无效的用户认证")
        data = await get_patient_files_sql(request.patient_id)
        files = [FileInfo(**f) for f in data["files"]]
        return PatientFilesResponse(ok=0, failed="", files=files, total=data["total"])
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
            return CreateConversationResponse(ok=1, failed="无效的用户认证", conversation_id=None)
        # 新增逻辑：如果已存在predict_neo_antigen类型的会话，直接返回
        if request.conversation_type == "predict_neo_antigen":
            conversation_id = await get_conversation_id_by_patient_and_type_sql(int(request.patient_id), "predict_neo_antigen")
            if conversation_id:
                return CreateConversationResponse(ok=0, failed="", conversation_id=conversation_id)
        # 创建会话
        result = await create_conversation_sql(
            patient_id=int(request.patient_id),
            conversation_type=request.conversation_type,
            title=request.title
        )
        if result["ok"] != 0:
            return CreateConversationResponse(ok=1, failed=result["failed"], conversation_id=None)
        return CreateConversationResponse(ok=0, failed="", conversation_id=result["conversation_id"])
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
            return ConversationMessagesResponse(ok=1, failed="无效的用户认证", messages=[])
        # 2. 查找conversation_id
        conversation_id = await get_conversation_id_by_patient_and_type_sql(request.patient_id, request.conversation_type)
        if not conversation_id:
            return ConversationMessagesResponse(ok=0, failed="未找到对应会话", messages=[])
        # 3. 从数据库获取消息数据
        messages_data = await get_messages_by_conversation_id_sql(conversation_id)
        # 4. 将原始数据转换为Pydantic模型列表
        messages = [MessageInfo(**msg) for msg in messages_data]
        # 5. 返回成功响应
        return ConversationMessagesResponse(ok=0, failed="", messages=messages)
    except Exception as e:
        logger.error(f"获取会话消息失败: {e}", exc_info=True)
        return ConversationMessagesResponse(ok=1, failed=str(e), messages=[])

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
            return GetWorkflowStatusResponse(ok=1, failed="无效的用户认证")
        
        data = await get_workflow_status_by_patient_id_sql(request.patient_id)
        if not data:
            return GetWorkflowStatusResponse(ok=1, failed="未找到该病人的工作流信息", data=None)
        
        # 将数据转换为WorkflowStatusInfo列表
        workflow_status_list = [WorkflowStatusInfo(**item) for item in data]
        return GetWorkflowStatusResponse(ok=0, failed="", data=workflow_status_list)
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
            return PredictionDetailListResponse(ok=1, failed="无效的用户认证", details=[])
        data = await get_prediction_groups_by_patient_id_sql(request.patient_id)
        groups = [PredictionGroup(
            prediction_id=group["prediction_id"],
            create_time=group["create_time"],
            prediction_details=[PredictionDetailItem(**item) for item in group["prediction_details"]]
        ) for group in data]
        return PredictionDetailListResponse(ok=0, failed="", details=groups)
    except Exception as e:
        logger.error(f"查询病人PredictionGroup失败: {e}", exc_info=True)
        return PredictionDetailListResponse(ok=1, failed=str(e), details=[])

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