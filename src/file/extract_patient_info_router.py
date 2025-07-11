import httpx
import json
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict
import aiofiles
import asyncio
import hashlib
import os
import uuid
from pathlib import Path
from minio.error import S3Error
from src.db.file_model import FileModel
from src.utils.base import get_async_session_local
from src.utils.jwt_util import decode_vaild
from src.utils.minio import minio_client, bucket_molly
import base64

from src.api.protocols import PatientInfoRequest, PatientInfoResponse, DescRequest, DescResponse
from src.utils.log import logger
from src.config import g_config

router = APIRouter(tags=["patient-info"])
security = HTTPBearer()

# 配置提取服务的URL
EXTRACT_SERVICE_URL = g_config["url"]["target_extract_patient_info_url"]
target_desc_url = g_config["url"]["target_desc_url"]

# request_descagent函数实现（与upload_sequence_files_router.py一致）
async def request_descagent(file_name: str, file_data: bytes, content_type: str) -> str:
    """请求DescAgent服务获取文件描述"""
    import json
    import httpx
    from src.api.protocols import DescRequest, DescResponse
    text_types = {"text/plain", "application/json", "text/csv", "application/x-fasta","patient_info_file"}
    is_text_candidate = (
        content_type in text_types or file_name.lower().endswith(".fas")
    )
    if is_text_candidate:
        try:
            file_content = file_data.decode("utf-8")
            if logger:
                logger.debug(f"File {file_name} decoded as text: {file_content[:50]}...")
        except UnicodeDecodeError:
            if logger:
                logger.warning(f"File {file_name} is not valid UTF-8 text, using Base64")
            file_content = base64.b64encode(file_data).decode("utf-8")
    else:
        file_content = base64.b64encode(file_data).decode("utf-8")
    request_data = DescRequest(file_name=file_name, file_content=file_content).dict()
    if logger:
        logger.info(f"发送到DescAgent的数据: {json.dumps(request_data, ensure_ascii=False)}")
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=30.0)) as client:
        try:
            response = await client.post(target_desc_url, json=request_data)
            if response.status_code != 200:
                error = response.text
                if logger:
                    logger.error(f"DescAgent error: {response.status_code} {error}")
                return f"DescAgent error: {response.status_code} {error}"
            result = DescResponse(**response.json())
            return result.file_description
        except httpx.ConnectError as e:
            if logger:
                logger.error(f"Connection error to DescAgent: {str(e)}")
            return "Connection failed to DescAgent"
        except Exception as e:
            if logger:
                logger.error(f"Unexpected error requesting DescAgent: {str(e)}", exc_info=True)
            return f"Unexpected error: {str(e)}"

@router.post("/extract_patient_info_from_file", response_model=PatientInfoResponse)
async def extract_patient_info_from_file(
    file: UploadFile = File(...),
    # patient_id: str = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """
    从上传的文件中提取病人信息，并将文件存储到MinIO和file表。
    """
    # 校验token，获取unionid
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if unionid is None:
            raise HTTPException(status_code=401, detail="unionid不存在")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Token验证失败: {str(e)}")
        raise HTTPException(status_code=401, detail=f"无效的token: {str(e)}")

    # 读取文件内容
    content = await file.read()
    try:
        file_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="文件编码格式不正确，请上传UTF-8编码的文本文件"
        )

    # 保存文件到本地临时目录
    UPLOAD_DIR = Path(g_config["temp"]["upload_files_dir"])
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    object_name = f"{uuid.uuid4()}_{file.filename}"
    minio_file_path = f"minio://{bucket_molly}/{object_name}"
    local_file_path = UPLOAD_DIR / object_name
    try:
        async with aiofiles.open(local_file_path, "wb") as local_file:
            await local_file.write(content)

        # 计算文件hash
        loop = asyncio.get_event_loop()
        file_hash = await loop.run_in_executor(None, lambda: hashlib.sha256(content).hexdigest())

        # 上传到MinIO
        await asyncio.get_running_loop().run_in_executor(
            None, minio_client.fput_object, bucket_molly, object_name, str(local_file_path)
        )

        # 获取文件描述
        file_desc = await request_descagent(file.filename, content, file.content_type)
        logger.info(f'DescAgent return file_desc:{file_desc}')

        # 写入数据库
        AsyncSessionLocal = get_async_session_local()
        async with AsyncSessionLocal() as session:
            file_info = {
                "file_name": file.filename,
                "file_size": len(content),
                "file_type": "patient_info_file",
                "file_path": minio_file_path,
                "file_hash": file_hash,
                "file_status": True,
                "file_source": 0,
                "file_desc": file_desc,
            }
            uploaded_file = FileModel(
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
            await session.refresh(uploaded_file)  # 刷新以获取自动生成的ID

        # 删除本地临时文件
        local_file_path.unlink(missing_ok=True)
    except S3Error as minio_error:
        logger.error(f"MinIO上传失败: {str(minio_error)}")
        raise HTTPException(status_code=500, detail=f"MinIO上传失败: {str(minio_error)}")
    except Exception as e:
        logger.error(f"文件处理或数据库写入失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文件处理或数据库写入失败: {str(e)}")

    # 继续调用提取服务
    try:
        request_data = PatientInfoRequest(patient_info=file_content)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                EXTRACT_SERVICE_URL,
                json=request_data.dict()
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"提取服务返回错误: {response.text}"
                )
            result = response.json()
            structured_info = result.get("structured_info", {})
            structured_info['source_id'] = uploaded_file.id
            return PatientInfoResponse(
                content=file_content,
                structured_info=structured_info
            )
    except Exception as e:
        logger.error(f"提取病人信息时发生错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提取病人信息时发生错误: {str(e)}")

@router.post("/extract_patient_info", response_model=PatientInfoResponse)
async def extract_patient_info(
    request: PatientInfoRequest
) -> Dict:
    """
    从文本中提取病人信息。
    
    Args:
        request (PatientInfoRequest): 包含病人信息文本的请求
        
    Returns:
        Dict: 包含结构化病人信息的响应
    """
    try:
        # 调用提取服务
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    EXTRACT_SERVICE_URL,
                    json=request.dict()
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"提取服务返回错误: {response.text}"
                    )
                
                # 解析响应
                result = response.json()
                return PatientInfoResponse(structured_info=result["structured_info"])
                
            except httpx.ConnectError as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"无法连接到提取服务: {str(e)}"
                )
            except Exception as e:
                logger.error(f"提取病人信息时发生错误: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"处理请求时发生错误: {str(e)}"
                )
                
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"处理请求时发生错误: {str(e)}"
        ) 