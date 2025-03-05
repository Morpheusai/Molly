import os
from fastapi import APIRouter, Body, HTTPException
from minio.error import S3Error

from src.api.protocols import DownloadFileRequest
from src.utils.log import logger
from src.utils.jwt_util import decode_vaild
from src.utils.minio import minio_client, bucket_netmhcpan_results
from src.api.protocols import DisplayResponse
# 假设这些变量已在文件顶部定义
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

router = APIRouter(tags=["file-display"])

@router.post("/display")
async def display_router(
    request: DownloadFileRequest = Body(...),
):
    """Return file content as text from MinIO after token validation.

    Args:
        request (DownloadFileRequest): Request body with file_path and system_token.

    Returns:
        str: The file content as a string.
    """
    # 1. 验证 token
    try:
        payload = decode_vaild(request.system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="Invalid or missing unionid")
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    
    bucket_netmhcpan_results = "netmhcpan-results"

    # 2. 解析 file_path
    file_path = request.file_path
    if not file_path.startswith(f"minio://{bucket_netmhcpan_results}/"):
        logger.error(f"Invalid file_path format: {file_path}")
        raise HTTPException(status_code=400, detail=f"Invalid file path, expected minio://{bucket_netmhcpan_results}/...")

    object_name = file_path.replace(f"minio://{bucket_netmhcpan_results}/", "")
    file_name = object_name.split("/")[-1]

    # 3. 从 MinIO 一次性读取文件内容
    try:
        response = minio_client.get_object(bucket_netmhcpan_results, object_name)
        file_stat = minio_client.stat_object(bucket_netmhcpan_results, object_name)
        file_size = file_stat.size

        # 一次性读取文件内容
        file_content = response.read()
        response.close()
        response.release_conn()

        # 4. 解码文件内容
        try:
            text_content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            logger.error(f"Failed to decode file content: {file_path}")
            raise HTTPException(status_code=500, detail="Failed to decode file content")

        # 5. 查找目标行并截取内容
        target_line = "# Rank Threshold for Weak binding peptides   2.000"
        target_index = text_content.find(target_line)
        if target_index == -1:
            logger.error(f"Target line not found in file: {file_path}")
            raise HTTPException(status_code=404, detail="Target line not found in file")

        # 截取目标行之后的内容
        content_target = text_content[target_index + len(target_line):]

        # 6. 直接返回内容
        return DisplayResponse(
            ok=0,
            failed="",
            content_target=content_target
        )

    except S3Error as minio_error:
        logger.error(f"MinIO download failed for {object_name}: {str(minio_error)}")
        raise HTTPException(status_code=404, detail=f"File not found: {str(minio_error)}")
    except Exception as e:
        logger.error(f"Unexpected error downloading {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")