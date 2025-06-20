import os

from fastapi import APIRouter, Body, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.api.api import delete_uploadfiles
from src.api.protocols import DeleteFileRequest,BaseResponse
from src.utils.log import logger
# 假设这些变量已在文件顶部定义
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

router = APIRouter(tags=["delete-file"])
security = HTTPBearer()

@router.post("/delete_file")
async def delete_file(
    request: DeleteFileRequest = Body(...),
    # credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """删除指定会话中的文件

    Args:
        conversation_id (str): 会话ID
        file_path (str): 文件路径
        credentials (HTTPAuthorizationCredentials): JWT认证信息

    Returns:
        dict: 删除操作的结果
    """

    try:
        # 2.使用 delete 操作删除指定会话中的文件                    
        return await delete_uploadfiles(request)
    except Exception as e:
        logger.error(f"Delete file failed: {str(e)}", exc_info=True)
        return BaseResponse(
            ok = 1,
            failed = f"Failed to delete file: {str(e)}"

        )