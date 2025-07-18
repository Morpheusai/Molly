from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.api.protocols import DeleteFileRequest, DeleteFileResponse
from src.utils.mysql_db import delete_patient_file_sql, has_predict_neo_antigen_conversation_sql
from src.utils.session import get_async_db
from src.utils.jwt_util import decode_vaild
import os

router = APIRouter()
security = HTTPBearer()

# 获取SECRET_KEY和ALGORITHM
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

@router.post("/delete_patient_file", response_model=DeleteFileResponse, tags=["文件管理"], summary="删除测序文件")
async def delete_patient_file(
    request: DeleteFileRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    # 1. 校验token，确保用户身份合法
    system_token = credentials.credentials
    payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
    unionid = payload.get("sub")
    if unionid is None:
        raise HTTPException(status_code=401, detail="无效的用户认证")
    # 2. 判断能否删除
    has_predict = await has_predict_neo_antigen_conversation_sql(request.patient_id)
    if has_predict:
        return DeleteFileResponse(ok=0, failed="", can_delete=1)
    # 3. 调用数据库删除逻辑，进行伪删除（is_deleted=1）
    ok, msg = await delete_patient_file_sql(request.patient_id, request.file_path)
    if ok:
        return DeleteFileResponse(ok=0, failed="", can_delete=0)
    else:
        return DeleteFileResponse(ok=1, failed=msg, can_delete=0) 