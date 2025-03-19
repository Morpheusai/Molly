import os

from fastapi import APIRouter, Body, HTTPException
from minio.error import S3Error
from openpyxl import load_workbook
from io import BytesIO

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
    
    # bucket_netmhcpan_results = "netmhcpan-results"

    # 2. 解析 file_path
    file_path = request.file_path
    if not file_path.startswith(f"minio://"):
        logger.error(f"Invalid file_path format: {file_path}")
        raise HTTPException(status_code=400, detail=f"Invalid file path, expected minio://{bucket_netmhcpan_results}/...")

    # 2. 提取 bucket_name 和 object_name
    try:
        # 去掉 minio:// 前缀
        path_without_prefix = file_path[len("minio://"):]
        
        # 找到第一个斜杠的位置，用于分割 bucket_name 和 object_name
        first_slash_index = path_without_prefix.find("/")
        
        if first_slash_index == -1:
            raise ValueError("Invalid file path format: missing bucket name or object name")
        
        # 提取 bucket_name 和 object_name
        bucket_name = path_without_prefix[:first_slash_index]
        object_name = path_without_prefix[first_slash_index + 1:]
        
        # 打印提取结果（可选）
        logger.info(f"Extracted bucket_name: {bucket_name}, object_name: {object_name}")
        
    except Exception as e:
        logger.error(f"Failed to parse file_path: {file_path}, error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to parse file path: {str(e)}")    


    # 3. 从 MinIO 一次性读取文件内容
    try:
        response = minio_client.get_object(bucket_name, object_name)
        # file_stat = minio_client.stat_object(bucket_name, object_name)
        # file_size = file_stat.size

        # 一次性读取文件内容
        file_content = response.read()
        response.close()
        response.release_conn()

        # 4. 解码文件内容

        if bucket_name == "netmhcpan-results":
            # 如果 bucket_name 是 netmhcpan-results，直接返回整个文件内容
            workbook = load_workbook(BytesIO(file_content))
            sheet = workbook.active  # 获取第一个工作表
            
            # 将工作表内容转换为列表
            data = []
            for row in sheet.iter_rows(values_only=True):
                data.append(row)
            content_target = "\n".join(["\t".join([str(item) if item is not None else "" for item in row]) for row in data])    
            # content_target = data
        elif bucket_name == "esm-results":
            try:
                text_content = file_content.decode("utf-8")
            except UnicodeDecodeError:
                logger.error(f"Failed to decode file content: {file_path}")
                raise HTTPException(status_code=500, detail="Failed to decode file content")
                # 如果 bucket_name 是 esm_result，直接返回整个文件内容
            content_target = text_content
        else:
            # 如果 bucket_name 不是上述两种情况，可以抛出异常或设置默认值
            raise HTTPException(status_code=400, detail=f"Unsupported bucket name: {bucket_name}")
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