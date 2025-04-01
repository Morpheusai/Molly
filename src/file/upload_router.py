import aiofiles
import asyncio
import base64
import hashlib
import httpx
import json
import os
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter, File, UploadFile, HTTPException, Body
from minio.error import S3Error
from pathlib import Path
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Dict, Optional

from src.api.protocols import DescRequest, DescResponse
from src.config import g_config
from src.db.uploadfiles_model import UploadedFile
from src.utils.base import AsyncSessionLocal
from src.utils.log import logger
from src.utils.mysql_db import upsert_conversation_sql
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

# Ensure MinIO bucket exists
if not minio_client.bucket_exists(bucket_molly):
    minio_client.make_bucket(bucket_molly)


@router.post("/upload")
async def upload_attachments(
    files: List[UploadFile] = File(...),
    conversation_id: str = Body(...),
    system_token: str = Body(..., description="系统token"),
    session_title: str = Body(default="file chat"),
) -> Dict:
    """Upload multiple files to MinIO concurrently with independent sessions.

    Args:
        files (List[UploadFile]): List of files to upload.
        conversation_id (str): The conversation ID associated with the files.

    Returns:
        dict: A dictionary containing a message and list of file metadata or errors.
    """
    # Define a helper function to process each file with its own session
    sem = asyncio.Semaphore(10)

    try:
        payload = decode_vaild(system_token, SECRET_KEY,
                               algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if unionid is None:
            raise HTTPException(status_code=401, detail="unionid不存在")
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    # 确保 conversation 存在
    try:
        await upsert_conversation_sql(conversation_id, unionid, session_title)
    except Exception as e:
        logger.error(
            f"Failed to upsert conversation {conversation_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize conversation: {str(e)}")

    async def process_file(file: UploadFile):
        async with sem, AsyncSessionLocal() as session:
            return await upload_attachment(file, conversation_id, session)

    tasks = [process_file(file) for file in files]
    attachment_info_list = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理返回结果
    response = {
        "ok": 0,
        "message": "Attachments processed",
        "attachments_info": []
    }
    has_errors = False
    for info in attachment_info_list:
        if isinstance(info, Exception):
            has_errors = True
            response["attachments_info"].append({"error": str(info)})
        else:
            # Check if the file already exists in the session
            if "message" in info and info["message"] == "File content already exists in this conversation":
                has_errors = True
                # No need to add info again, as it's already handled
                response["attachments_info"].append(info)
            else:
                response["attachments_info"].append(info)
    if has_errors:
        response["ok"] = 1
        response["message"] = "Some attachments failed to process"
    return response


async def calculate_file_hash(file_data: bytes) -> str:
    """Calculate the SHA-256 hash of file content asynchronously.

    Args:
        file_data (bytes): The content of the file to hash.

    Returns:
        str: The hexadecimal SHA-256 hash of the file content.
    """
    loop = asyncio.get_event_loop()
    # Move synchronized hash calculations to the thread pool
    hash_value = await loop.run_in_executor(None, lambda: hashlib.sha256(file_data).hexdigest())
    return hash_value


async def insert_file_info_to_db(session: AsyncSession, conversation_id: str, file_info: dict) -> None:
    """Insert file metadata into the database.

    Args:
        session (AsyncSession): The active database session.
        conversation_id (str): The ID of the conversation associated with the file.
        file_info (dict): Metadata of the file to insert.

    Raises:
        HTTPException: If the database insertion fails.
    """
    try:
        uploaded_file = UploadedFile(
            id=file_info['file_id'],  # file id
            conversation_id=conversation_id,  # 会话id
            file_name=file_info['file_name'],  # 文件名
            file_type=file_info['file_type'],  # 文件类型
            file_size=file_info['file_size'],  # 文件大小
            file_path=file_info['file_path'],  # minio文件路径
            file_hash=file_info['file_hash'],  # 文件内容哈希值
            file_status=file_info['file_status'],  # 文件状态
            file_origin=file_info['file_origin'],  # 用户上传
            file_desc=file_info['file_desc']  # 文件内容概述
        )
        session.add(uploaded_file)
        await session.commit()
        logger.debug(
            f"Inserted file {file_info['file_name']} into database with status: {file_info['file_status']}")
    except Exception as e:
        await session.rollback()
        logger.error(
            f"Failed to insert file {file_info['file_name']} into database: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Database insert failed: {str(e)}")


async def check_existing_file(session: AsyncSession, conversation_id: str, file_hash: str) -> Optional[UploadedFile]:
    """Check if a file with the same hash exists in the given conversation.

    Args:
        session (AsyncSession): The active database session.
        conversation_id (str): The conversation ID to check.
        file_hash (str): The hash of the file content to search for.

    Returns:
        Optional[UploadedFile]: The existing file if found, otherwise None.
    """
    query = select(UploadedFile).where(
        UploadedFile.conversation_id == conversation_id,
        UploadedFile.file_hash == file_hash,
        UploadedFile.file_status == True,  # 只检查成功上传的文件(包括agent输出，用户上传)
        UploadedFile.file_origin == 0
    )
    result = await session.execute(query)
    existing_file = result.scalars().first()
    return existing_file


async def check_file_count(session: AsyncSession, conversation_id: str) -> int:
    """查询当前会话的已上传文件数量"""
    query = select(func.count()).select_from(UploadedFile).where(
        UploadedFile.conversation_id == conversation_id)
    result = await session.execute(query)
    return result.scalar()


async def upload_to_minio(bucket: str, object_name: str, file_path: Path) -> None:
    """Upload a local file to MinIO asynchronously.

    Args:
        bucket (str): The MinIO bucket name.
        object_name (str): The name of the object in MinIO.
        file_path (Path): Path to the local file.

    Raises:
        S3Error: If the upload to MinIO fails.
    """
    loop = asyncio.get_running_loop()

    try:
        await loop.run_in_executor(None, minio_client.fput_object, bucket, object_name, str(file_path))
        logger.info(
            f"Uploaded file {file_path} to MinIO successfully as {object_name}")
    except S3Error as e:
        logger.error(f"MinIO upload failed for {file_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during MinIO upload: {str(e)}")
        raise


async def upload_attachment(file: UploadFile, conversation_id: str, session: AsyncSession) -> Dict:
    """Upload a single file to MinIO asynchronously and store its metadata.

    Args:
        file (UploadFile): The file to upload.
        conversation_id (str): The conversation ID associated with the file.
        session (AsyncSession): The active database session.

    Returns:
        dict: Metadata of the uploaded file or information about an existing file.

    Raises:
        HTTPException: If file processing or MinIO upload fails.
    """
    file_id = str(uuid.uuid4())
    object_name = f"{file_id}_{file.filename}"
    minio_file_path = f"minio://{bucket_molly}/{object_name}"
    local_file_path = UPLOAD_DIR / object_name
    try:
        # 检查同一会话下的上传文件数量
        file_count = await check_file_count(session, conversation_id)
        if file_count >= MAX_FILES_PER_CONVERSATION:
            raise HTTPException(
                status_code=413,
                detail=f"File limit exceeded: Maximum {MAX_FILES_PER_CONVERSATION} files allowed per conversation"
            )

        file_data = await file.read()
        file_size_mb = len(file_data) / (1024 * 1024)
        # 检查文件大小是否超过限制
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=413,  # 413 Payload Too Large
                detail=f"File size exceeds limit of {MAX_FILE_SIZE_MB} MB"
            )

        # 计算文件哈希值
        file_hash = await calculate_file_hash(file_data)

        # Check if a file with the same content already exists in the current session
        if existing_file := await check_existing_file(session, conversation_id, file_hash):
            # If the file already exists, return a prompt message
            return {
                "message": "File content already exists in this conversation",
                "file_id": existing_file.id,
                "file_name": existing_file.file_name,
                "file_path": existing_file.file_path,
                "file_hash": existing_file.file_hash,
                "file_status": existing_file.file_status,
                "file_origin": existing_file.file_origin,
                "file_desc": existing_file.file_desc
            }
        # 文件保存本地
        async with aiofiles.open(local_file_path, "wb") as local_file:
            await local_file.write(file_data)
        # local_file_path.write_bytes(file_data)

        # Prepare file metadata
        file_info = {
            "file_id": file_id,
            "file_name": file.filename,
            "file_size": len(file_data),
            "file_type": file.content_type,
            "file_path": str(local_file_path),  # 默认是本地地址，成功时改为 minio路径
            "file_hash": file_hash,
            "file_status": False,  # 默认失败，成功时改为 True
            "file_origin": 0,
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
        file_info["file_desc"] = file_desc

        # 上传成功，插入数据库
        await insert_file_info_to_db(session, conversation_id, file_info)

        # 删除本地文件
        local_file_path.unlink()

    except S3Error as minio_error:
        # MinIO 上传失败，记录日志并插入失败状态
        logger.error(
            f"MinIO upload failed for file {file.filename}: {str(minio_error)}")
        await insert_file_info_to_db(session, conversation_id, file_info)
        raise HTTPException(
            status_code=500, detail=f"MinIO upload failed: {str(minio_error)}")
    except HTTPException:
        raise
    except Exception as e:
        # 其他异常（例如文件读取失败、哈希计算失败）
        logger.error(
            f"Unexpected error processing file {file.filename}: {str(e)}")
        await insert_file_info_to_db(session, conversation_id, file_info)
        raise HTTPException(
            status_code=500, detail=f"File processing failed: {str(e)}")

    return file_info


async def request_descagent(file_name: str, file_data: bytes, content_type: str) -> str:
    """Request a file description from the DescAgent server, optimized for handling .fas files.

    Args:
        file_name (str): The name of the file, used to identify it in the request and check its extension.
        file_data (bytes): The raw content of the file in bytes, to be processed and sent to the DescAgent.
        content_type (str): The MIME type of the file, used to determine if it’s likely a text file.

    Returns:
        str: The file description returned by the DescAgent server, or an error message if the request fails.

    Raises:
        None explicitly, but logs errors and returns error strings for connection or unexpected issues.
    """
    # 定义可能的文本类型，包括 .fas 文件
    text_types = {"text/plain", "application/json",
                  "text/csv", "application/x-fasta"}

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
