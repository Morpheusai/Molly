import os
import re

from fastapi import Body, HTTPException, APIRouter,Depends,Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from minio.error import S3Error

from src.api.protocols import DownloadFileRequest
from src.utils.log import logger
from src.utils.minio import minio_client


# 定义 MinIO 路径正则表达式(用于匹配)
MINIO_URL_PATTERN = re.compile(r"^minio://([\w-]+)/(.+)$")

router = APIRouter(tags=["markdown-file-download"])
security = HTTPBearer()

@router.get("/markdown_download")
async def markdown_download_file(
    file_path: str = Query(..., description="MinIO文件路径，格式: minio://bucket/object"),
) -> StreamingResponse:
    """Download a file from MinIO after token validation.

    Args:
        request (DownloadFileRequest): Request body with file_path and system_token.

    Returns:
        StreamingResponse: The file content as a stream for direct download.
    """

    # 1. **解析 file_path**
    match = MINIO_URL_PATTERN.match(file_path)

    if not match:
        logger.error(f"Invalid file_path format: {file_path}")
        return {
            "ok": 1,
            "failed": "Invalid file path format. Expected 'minio://bucket_name/object_name'."
        }      

    bucket_name, object_name = match.groups()

    # 2. **从 MinIO 下载文件**
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
                "Content-Disposition": f"attachment; filename*=UTF-8''{file_name}",
                "Content-Length": str(file_size),
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except S3Error as minio_error:
        logger.error(
            f"MinIO download failed for {object_name}: {str(minio_error)}")

        return {
            "ok": 1,
            "failed": f"File not found: {str(minio_error)}"
        }         
    except Exception as e:
        logger.error(f"Unexpected error downloading {file_path}: {str(e)}")

        return {
            "ok": 1,
            "failed": f"Download failed: {str(e)}"
        }    
