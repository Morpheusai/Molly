import os
import re
from fastapi import Body, HTTPException, APIRouter
from fastapi.responses import StreamingResponse
from minio.error import S3Error
from src.api.protocols import DownloadFileRequest
from src.utils.log import logger
from src.utils.jwt_util import decode_vaild  # 修正拼写错误
from src.utils.minio import minio_client

# 读取环境变量
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# 定义 MinIO 路径正则表达式(用于匹配)
MINIO_URL_PATTERN = re.compile(r"^minio://([\w-]+)/(.+)$")

router = APIRouter(tags=["file-download"])

@router.post("/download")
async def download_file(
    request: DownloadFileRequest = Body(...)
    ) -> StreamingResponse:
    """Download a file from MinIO after token validation.

    Args:
        request (DownloadFileRequest): Request body with file_path and system_token.

    Returns:
        StreamingResponse: The file content as a stream for direct download.
    """
    # 1. **验证 Token 并处理过期情况**
    try:
        payload = decode_vaild(request.system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="Invalid or missing unionid")
        
        # 检查 Token 是否过期
        if "exp" in payload:
            import time
            if payload["exp"] < time.time():
                raise HTTPException(status_code=401, detail="Token has expired")

    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    # 2. **解析 file_path**
    file_path = request.file_path
    match = MINIO_URL_PATTERN.match(file_path)
    
    if not match:
        logger.error(f"Invalid file_path format: {file_path}")
        raise HTTPException(status_code=400, detail="Invalid file path format. Expected 'minio://bucket_name/object_name'.")

    bucket_name, object_name = match.groups()

    # 3. **从 MinIO 下载文件**
    try:
        response = minio_client.get_object(bucket_name, object_name)
        file_stat = minio_client.stat_object(bucket_name, object_name)
        file_size = file_stat.size
        file_type = file_stat.content_type or "application/octet-stream"
        file_name = object_name.split("/")[-1]

        async def stream_file():
            try:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    yield chunk
            finally:
                response.close()
                response.release_conn()

        return StreamingResponse(
            stream_file(),
            media_type=file_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{file_name}\"",
                "Content-Length": str(file_size),
            }
        )
    except S3Error as minio_error:
        logger.error(f"MinIO download failed for {object_name}: {str(minio_error)}")
        raise HTTPException(status_code=404, detail=f"File not found: {str(minio_error)}")
    except Exception as e:
        logger.error(f"Unexpected error downloading {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
    