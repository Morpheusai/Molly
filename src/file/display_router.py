import os

from fastapi import APIRouter, Body, HTTPException,Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from minio.error import S3Error
from openpyxl import load_workbook
import base64
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
security = HTTPBearer()

@router.post("/display")
async def display_router(
    request: DownloadFileRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Return file content as text from MinIO after token validation.

    Args:
        request (DownloadFileRequest): Request body with file_path and system_token.

    Returns:
        str: The file content as a string.
    """

    # 1. 验证 token
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
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

    # 2. 解析 file_path
    file_path = request.file_path
    if not file_path.startswith("minio://"):
        logger.error(f"Invalid file_path format: {file_path}")
        return {
            "ok": 1,
            "failed": "Invalid file path, expected minio://bucket_name/object_path"
        }

    try:
        # 提取 bucket_name 和 object_name
        path_without_prefix = file_path[len("minio://"):]
        first_slash_index = path_without_prefix.find("/")
        
        if first_slash_index == -1:
            return {
                "ok": 1,
                "failed": "Invalid file path format: missing bucket name or object name"
            }

        bucket_name = path_without_prefix[:first_slash_index]
        object_name = path_without_prefix[first_slash_index + 1:]
        
        logger.info(f"Extracted bucket_name: {bucket_name}, object_name: {object_name}")

        # 3. 从 MinIO 获取文件
        response = minio_client.get_object(bucket_name, object_name)
        file_content = response.read()
        response.close()
        response.release_conn()

        # 4. 根据文件扩展名处理不同文件类型
        file_extension = object_name.lower().split('.')[-1] if '.' in object_name else ''
        
        
        if file_extension in ['xlsx', 'xls']:
            # 处理Excel文件
            workbook = load_workbook(BytesIO(file_content))
            sheet = workbook.active
            data = []
            for row in sheet.iter_rows(values_only=True):
                data.append(row)
            content = "\n".join(["\t".join(
                [str(item) if item is not None else "" for item in row]) for row in data])
        
        elif file_extension == 'pdf':
            # 返回PDF原始内容（包括二进制数据）
            content = base64.b64encode(file_content).decode('utf-8')

        
        elif file_extension in ['txt', 'csv', 'log', 'json', 'xml', 'svg', 'html']:
            # 处理文本文件
            try:
                content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                # 尝试其他编码
                try:
                    content = file_content.decode('gbk')
                except Exception as e:
                    logger.error(f"Failed to decode text file: {str(e)}")
                    return {
                        "ok": 1,
                        "failed": f"Failed to decode text file: {str(e)}"
                    }
        
        elif file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp']:
            # 处理图片文件 - 返回Base64编码
            content = base64.b64encode(file_content).decode('utf-8')
        
        else:
            # 默认处理为二进制文件或未知类型
            content = base64.b64encode(file_content).decode('utf-8')

        # 5. 返回响应
        return DisplayResponse(
            ok=0,
            failed="",
            content_target=content,
        )

    except S3Error as minio_error:
        logger.error(f"MinIO download failed: {str(minio_error)}")
        return {
            "ok": 1,
            "failed": f"File not found: {str(minio_error)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "ok": 1,
            "failed": f"Processing failed: {str(e)}"
        }