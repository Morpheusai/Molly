import os

from fastapi import APIRouter, Body, HTTPException,Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from minio.error import S3Error
from openpyxl import load_workbook
from io import BytesIO

from src.api.api import update_uploadfiles_file_type
from src.api.protocols import MigrateFileRequest,QuerySessionResponse
from src.utils.log import logger
from src.utils.jwt_util import decode_vaild
from src.utils.minio import minio_client, bucket_netmhcpan_results
# 假设这些变量已在文件顶部定义
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

router = APIRouter(tags=["files-migrate"])
security = HTTPBearer()

@router.post("/files_migrate")
async def migrate_router(
    request: MigrateFileRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    迁移文件类型并返回完整会话数据
    
    Args:
        request: 包含file_paths和conversation_id的请求体
        credentials: JWT认证凭证
        
    Returns:
        QuerySessionResponse: 包含会话消息、文件和neo_files的完整响应
    """


    # 1. 验证 token
    try:
        # 提取并校验 token
        system_token = credentials.credentials  # 直接获取Token
        payload = decode_vaild(system_token,
                               SECRET_KEY, algorithms=[ALGORITHM])
        unionid = payload.get("sub")
        if not unionid:
            return {
                "ok": 1,
                "failed": "Invalid or missing unionid"
            }
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        return {
            "ok": 1,
            "failed": f"Invalid token: {str(e)}"
        }

    try:
        # 2.使用 update 操作更新uploadfiles的file_type字段值，并输出完整会话信息。
        return await update_uploadfiles_file_type(request.file_paths,request.conversation_id)
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        return QuerySessionResponse(
            ok=1,
            failed=str(e),
            conversation_id=request.conversation_id,
            session_title="",
            chat_type="",
            chats=[],
            files=[],
            neo_files=[]
        )