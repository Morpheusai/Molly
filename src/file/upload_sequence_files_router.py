import aiofiles
import asyncio
import base64
import hashlib
import httpx
import json
import os
import uuid
import re

from dotenv import load_dotenv
from fastapi import APIRouter, File, UploadFile, HTTPException, Body, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from minio.error import S3Error
from pathlib import Path
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Dict, Optional

from src.api.protocols import DescRequest, DescResponse
from src.config import g_config
from src.db.file_model import FileModel
from src.db.workflows_model import WorkflowModel
from src.utils.base import get_async_session_local
from src.utils.log import logger
from src.utils.jwt_util import decode_vaild
from src.utils.minio import minio_client, bucket_molly

load_dotenv()

# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "")  # 用于签名和验证 JWT 的密钥
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # 加密算法
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))  # JWT Token 过期时间

UPLOAD_DIR = Path(g_config["temp"]["upload_files_dir"])
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 5))
MAX_FILES_PER_CONVERSATION = int(os.getenv("MAX_FILES_PER_CONVERSATION", 5))

target_desc_url = g_config["url"]["target_desc_url"]

router = APIRouter(tags=["file-upload"])
security = HTTPBearer()

# 确保 MinIO 存储桶存在
if not minio_client.bucket_exists(bucket_molly):
    minio_client.make_bucket(bucket_molly)

@router.post("/upload_sequence_files")
async def upload_attachments(
    files: List[UploadFile] = File(...),
    patient_id: int = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """并发上传多个文件到 MinIO，使用独立的会话。

    参数:
        files (List[UploadFile]): 要上传的文件列表。
        patient_id (int): 患者ID。
        unionid (str): 用户ID。
        credentials (HTTPAuthorizationCredentials): JWT认证信息。

    返回:
        dict: 包含消息和文件元数据列表或错误信息的字典。
    """
    # 定义辅助函数，使用独立的会话处理每个文件
    sem = asyncio.Semaphore(10)

    try:
        # 提取并校验 token
        system_token = credentials.credentials  # 直接获取Token        
        payload = decode_vaild(system_token, SECRET_KEY,
                               algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if unionid is None:
            raise HTTPException(status_code=401, detail="无效的用户认证")
    except HTTPException as e:
        raise e 
    except Exception as e:
        logger.error(f"Token验证失败: {str(e)}")
        return {
            "ok": 1,
            "failed": f"无效的token: {str(e)}"
        }      

    async def process_file(file: UploadFile):
        async with sem, get_async_session_local()() as session:
            return await upload_attachment(file, patient_id, unionid, session)

    tasks = [process_file(file) for file in files]
    attachment_info_list = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理返回结果
    response = {
        "ok": 0,
        "message": "附件处理完成",
        "attachments_info": []
    }
    has_errors = False
    for info in attachment_info_list:
        if isinstance(info, Exception):
            has_errors = True
            response["attachments_info"].append({"error": str(info)})
        else:
            # 检查文件是否已存在于会话中
            if "message" in info and info["message"] == "File content already exists in this conversation":
                has_errors = True
                # 无需再次添加信息，因为已经处理过
                response["attachments_info"].append(info)
            else:
                response["attachments_info"].append(info)
    
    # 如果上传成功，更新工作流状态
    if not has_errors:
        async with get_async_session_local()() as session:
            # 查找对应stage的工作流记录（测序数据阶段，rank=2）
            result = await session.execute(
                select(WorkflowModel)
                .where(WorkflowModel.patient_id == patient_id)
                .where(WorkflowModel.stage == '测序数据')
                .where(WorkflowModel.rank == 2)
            )
            workflow = result.scalar_one_or_none()
            
            if workflow:
                workflow.status = 'completed'
                workflow.completed_at = func.now()
                await session.commit()
                logger.info(f"Workflow for patient {patient_id} stage '测序数据' (rank=2) completed")

    if has_errors:
        response["ok"] = 1
        response["message"] = "部分附件处理失败"
    return response


async def calculate_file_hash(file_data: bytes) -> str:
    """异步计算文件内容的 SHA-256 哈希值。

    参数:
        file_data (bytes): 要计算哈希值的文件内容。

    返回:
        str: 文件内容的十六进制 SHA-256 哈希值。
    """
    loop = asyncio.get_event_loop()
    # 将同步哈希计算移到线程池中
    hash_value = await loop.run_in_executor(None, lambda: hashlib.sha256(file_data).hexdigest())
    return hash_value


async def insert_file_info_to_db(session: AsyncSession, patient_id: int, unionid: str, file_info: dict) -> FileModel:
    """将文件元数据插入数据库。

    参数:
        session (AsyncSession): 活动的数据库会话。
        patient_id (int): 患者ID。
        unionid (str): 上传者用户ID。
        file_info (dict): 要插入的文件元数据。

    返回:
        FileModel: 包含新插入文件信息的 FileModel 对象。

    异常:
        Exception: 如果数据库插入失败。
    """
    try:
        uploaded_file = FileModel(
            patient_id=patient_id,
            upload_by=unionid,
            file_name=file_info['file_name'],
            file_type=file_info['file_type'],
            file_size=file_info['file_size'],
            file_path=file_info['file_path'],
            file_hash=file_info['file_hash'],
            file_status=file_info['file_status'],
            file_source=file_info['file_source'],
            file_desc=file_info['file_desc'],
            is_deleted=False
        )
        session.add(uploaded_file)
        await session.commit()
        await session.refresh(uploaded_file)
        logger.debug(
            f"文件 {file_info['file_name']} 已插入数据库，ID: {uploaded_file.id}，状态: {file_info['file_status']}")
        return uploaded_file
    except Exception as e:
        await session.rollback()
        logger.error(
            f"文件 {file_info['file_name']} 插入数据库失败: {str(e)}")
        # Re-raise the exception to be handled by the caller
        raise e


async def check_existing_file(session: AsyncSession, patient_id: int, file_hash: str) -> Optional[FileModel]:
    """检查给定患者中是否存在具有相同哈希值的文件。

    参数:
        session (AsyncSession): 活动的数据库会话。
        patient_id (int): 患者ID。
        file_hash (str): 要搜索的文件内容哈希值。

    返回:
        Optional[FileModel]: 如果找到则返回现有文件，否则返回None。
    """
    query = select(FileModel).where(
        FileModel.patient_id == patient_id,
        FileModel.file_hash == file_hash,
        FileModel.file_status == True,
        FileModel.is_deleted == False,
        FileModel.file_source == 0
    )
    result = await session.execute(query)
    existing_file = result.scalars().first()
    return existing_file


async def check_file_count(session: AsyncSession, patient_id: int) -> int:
    """查询当前患者的已上传文件数量"""
    query = select(func.count()).select_from(FileModel).where(
        FileModel.patient_id == patient_id,
        FileModel.is_deleted == False
    )
    result = await session.execute(query)
    return result.scalar()


async def upload_to_minio(bucket: str, object_name: str, file_path: Path) -> None:
    """异步将本地文件上传到 MinIO。

    参数:
        bucket (str): MinIO 存储桶名称。
        object_name (str): MinIO 中的对象名称。
        file_path (Path): 本地文件路径。

    异常:
        S3Error: 如果上传到 MinIO 失败。
    """
    loop = asyncio.get_running_loop()

    try:
        await loop.run_in_executor(None, minio_client.fput_object, bucket, object_name, str(file_path))
        logger.info(
            f"文件 {file_path} 已成功上传到 MinIO，对象名: {object_name}")
    except S3Error as e:
        logger.error(f"MinIO 上传失败 {file_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"MinIO 上传过程中发生意外错误: {str(e)}")
        raise

def is_valid_fasta_content(content: str) -> tuple[bool, str]:
    """验证文件内容是否符合FASTA格式。
    参数:
        content (str): 文件内容
    返回:
        tuple[bool, str]: (是否有效, 错误信息)
    """

    # 统一换行符为\n，同时按照行来切分
    items = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    
    standard_amino_acids = set('ACDEFGHIKLMNPQRSTVWY')
    # 特殊氨基酸代码
    special_amino_acids = set('BJOUXZ')
    # 所有有效的氨基酸代码
    valid_amino_acids = standard_amino_acids.union(special_amino_acids)

    for icount, item in enumerate(items):
        # 去除行首和行尾的空白字符
        sequence = item.strip()
        if item.startswith('>'):
            # 检查头部格式
            if len(item) == 1:
                return False, f"第{icount}行，缺少必要的序列注释: {item}"
        else:
            invalid_chars = set(char.upper() for char in sequence if char.upper() not in valid_amino_acids)
            if invalid_chars:
                return False, f"序列{item}包含无效的氨基酸代码：{', '.join(sorted(invalid_chars))}。有效的氨基酸代码包括：标准氨基酸(A-Z)和特殊氨基酸(B,J,O,U,X,Z)"

    return True, ""

async def validate_fasta_file(file_data: bytes) -> tuple[bool, str]:
    """验证上传的文件是否为有效的FASTA文件。
    参数:
        file_data (bytes): 文件内容

    返回:
        tuple[bool, str]: (是否有效, 错误信息)
    """
    try:
        content = file_data.decode('utf-8')
    except UnicodeDecodeError:
        return False, "文件不是有效的文本文件，无法解码为UTF-8格式"

    is_valid, error_message = is_valid_fasta_content(content)
    if not is_valid:
        return False, f"文件格式不符合FASTA标准：{error_message}"

    return True, ""

async def upload_attachment(file: UploadFile, patient_id: int, unionid: str, session: AsyncSession) -> Dict:
    """异步上传单个文件到 MinIO 并存储其元数据。

    参数:
        file (UploadFile): 要上传的文件。
        patient_id (int): 患者ID。
        unionid (str): 上传者用户ID。
        session (AsyncSession): 活动的数据库会话。

    返回:
        Dict: 包含上传结果信息的字典。
    """
    # 检查文件扩展名
    if not file.filename.lower().endswith(('.fasta', '.fsa')):
        return {
            "ok": 1,
            "failed": "只支持.fasta和.fsa格式的文件"
        }

    object_name = f"{uuid.uuid4()}_{file.filename}"
    minio_file_path = f"minio://{bucket_molly}/{object_name}"
    local_file_path = UPLOAD_DIR / object_name
    try:
        # 检查同一患者下的上传文件数量
        file_count = await check_file_count(session, patient_id) 
        if file_count >= MAX_FILES_PER_CONVERSATION:
            return {
                "ok": 1,
                "failed": f"File limit exceeded: Maximum {MAX_FILES_PER_CONVERSATION} files allowed per patient"
            }          

        file_data = await file.read()
        file_size_mb = len(file_data) / (1024 * 1024)
        # 检查文件大小是否超过限制
        if file_size_mb > MAX_FILE_SIZE_MB:
            return {
                "ok": 1,
                "failed": f"File size exceeds limit of {MAX_FILE_SIZE_MB} MB"
            }

        # 验证FASTA文件格式
        is_valid, error_message = await validate_fasta_file(file_data)
        if not is_valid:
            return {
                "ok": 1,
                "failed": error_message
            }

        # 计算文件哈希值
        file_hash = await calculate_file_hash(file_data)

        # Check if a file with the same content already exists for this patient
        if existing_file := await check_existing_file(session, patient_id, file_hash): 
            # If the file already exists, return a prompt message
            return {
                "message": "File content already exists for this patient",
                "file_id": existing_file.id,
                "file_name": existing_file.file_name,
                "file_path": existing_file.file_path,
                "file_hash": existing_file.file_hash,
                "file_status": existing_file.file_status,
                "file_source": existing_file.file_source,
                "file_desc": existing_file.file_desc
            }

        # 文件保存本地
        async with aiofiles.open(local_file_path, "wb") as local_file:
            await local_file.write(file_data)

        # Prepare file metadata
        file_info = {
            "file_name": file.filename,
            "file_size": len(file_data),
            "file_type": "sequence_file",
            "file_path": str(local_file_path),  # 默认是本地地址，成功时改为 minio路径
            "file_hash": file_hash,
            "file_status": False,  # 默认失败，成功时改为 True
            "file_source": "02",  # 02表示fasta文件是由用户上传得到的
            "file_desc": "",
        }

        # Upload to MinIO asynchronously
        await upload_to_minio(
            bucket=bucket_molly,
            object_name=object_name,
            file_path=local_file_path
        )

        file_info["file_status"] = True  # 上传成功
        file_info["file_path"] = minio_file_path
        logger.info(f"Uploaded file {file.filename} to MinIO successfully")

        # 请求DescAgent获取file_desc
        file_desc = await request_descagent(file.filename, file_data, file.content_type)
        logger.info(f'DescAgent return file_desc:{file_desc}')
        #TODO
        file_info["file_desc"] = file_desc
        # file_info["file_desc"] = "123"

        # 上传成功，插入数据库
        inserted_file = await insert_file_info_to_db(session, patient_id, unionid, file_info)
        file_info["file_id"] = inserted_file.id

        # 删除本地文件
        local_file_path.unlink()

    except S3Error as minio_error:
        # MinIO 上传失败，记录日志并插入失败状态
        logger.error(
            f"MinIO upload failed for file {file.filename}: {str(minio_error)}")
        try:
            await insert_file_info_to_db(session, patient_id, unionid, file_info)
        except Exception as db_error:
            logger.error(f"Failed to insert failure record for {file.filename}: {db_error}")
        return {
            "ok": 1,
            "failed": f"MinIO upload failed: {str(minio_error)}"
        }

    except HTTPException:
        raise
    except Exception as e:
        # 其他异常（例如文件读取失败、哈希计算失败）
        logger.error(
            f"Unexpected error processing file {file.filename}: {str(e)}")
        try:
            await insert_file_info_to_db(session, patient_id, unionid, file_info)
        except Exception as db_error:
            logger.error(f"Failed to insert failure record for {file.filename}: {db_error}")
        return {
            "ok": 1,
            "failed": f"File processing failed: {str(e)}"
        }

    return file_info




async def request_descagent(file_name: str, file_data: bytes, content_type: str) -> str:
    """Request a file description from the DescAgent server, optimized for handling .fas files.

    Args:
        file_name (str): The name of the file, used to identify it in the request and check its extension.
        file_data (bytes): The raw content of the file in bytes, to be processed and sent to the DescAgent.
        content_type (str): The MIME type of the file, used to determine if it's likely a text file.

    Returns:
        str: The file description returned by the DescAgent server, or an error message if the request fails.

    Raises:
        None explicitly, but logs errors and returns error strings for connection or unexpected issues.
    """
    # 定义可能的文本类型，包括 .fas 文件
    text_types = {"text/plain", "application/json",
                  "text/csv", "application/x-fasta","sequence_file"}

    # 检查文件扩展名和类型
    is_text_candidate = (
        content_type in text_types or
        file_name.lower().endswith(".fas")
    )

    if is_text_candidate:
        try:
            # 尝试将文件内容解码为字符串
            file_content = file_data.decode("utf-8")
            logger.debug(
                f"File {file_name} decoded as text: {file_content[:50]}...")
        except UnicodeDecodeError:
            logger.warning(
                f"File {file_name} is not valid UTF-8 text, using Base64")
            file_content = base64.b64encode(file_data).decode("utf-8")
    else:
        # 非文本文件直接用Base64
        file_content = base64.b64encode(file_data).decode("utf-8")

    # 构造请求数据
    request_data = DescRequest(
        file_name=file_name, file_content=file_content).dict()
    logger.info(
        f"发送到DescAgent的数据: {json.dumps(request_data, ensure_ascii=False)}")

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=30.0)) as client:
        try:
            response = await client.post(
                target_desc_url,
                json=request_data
            )
            if response.status_code != 200:
                error = response.text
                logger.error(
                    f"DescAgent error: {response.status_code} {error}")
                return f"DescAgent error: {response.status_code} {error}"

            result = DescResponse(**response.json())
            return result.file_description

        except httpx.ConnectError as e:
            logger.error(f"Connection error to DescAgent: {str(e)}")
            return "Connection failed to DescAgent"
        except Exception as e:
            logger.error(
                f"Unexpected error requesting DescAgent: {str(e)}", exc_info=True)
            return f"Unexpected error: {str(e)}"
