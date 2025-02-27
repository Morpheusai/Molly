import os
from fastapi import Body, HTTPException, APIRouter
from fastapi.responses import StreamingResponse

from minio.error import S3Error
from src.api.protocols import DownloadFileRequest
from src.utils.log import logger
from src.utils.jwt_util import decode_vaild
from src.utils.minio import minio_client, bucket_netmhcpan_results

# 假设这些变量已在文件顶部定义
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
# minio_client = Minio(...)  # 已有 MinIO 配置
# bucket_name = os.getenv("MINIO_BUCKET_NAME", "molly")

router = APIRouter(tags=["file-download"])

@router.post("/download")
async def download_file(
    request: DownloadFileRequest = Body(...),
) -> StreamingResponse:
    """Download a file from MinIO after token validation.

    Args:
        request (DownloadFileRequest): Request body with file_path and system_token.

    Returns:
        StreamingResponse: The file content as a stream for direct download.
    """
    # 验证 token
    try:
        payload = decode_vaild(request.system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="Invalid or missing unionid")
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    # 解析 file_path
    file_path = request.file_path
    if not file_path.startswith(f"minio://{bucket_netmhcpan_results}/"):
        logger.error(f"Invalid file_path format: {file_path}")
        raise HTTPException(status_code=400, detail=f"Invalid file path, expected minio://{bucket_netmhcpan_results}/...")

    object_name = file_path.replace(f"minio://{bucket_netmhcpan_results}/", "")
    file_name = object_name.split("/")[-1]

    # 从 minio 下载文件
    try:
        response = minio_client.get_object(bucket_netmhcpan_results, object_name)
        file_stat = minio_client.stat_object(bucket_netmhcpan_results, object_name)
        file_size = file_stat.size
        file_type = file_stat.content_type or "application/octet-stream"

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