import aiofiles
import base64
import hashlib
import uuid
import os

from pathlib import Path
from dotenv import load_dotenv
from fastapi import APIRouter, File, UploadFile, Body, Depends, HTTPException, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.future import select
from sqlalchemy import func

from src.api.api import upload_tumor_normal_files_api
from src.api.protocols import BaseResponse
from src.api.protocols import UploadTumorNormalFilesResponse
from src.config import g_config
from src.db.workflows_model import WorkflowModel
from src.utils.base import get_async_session_local
from src.utils.jwt_util import decode_vaild
from src.utils import logger
from src.utils.minio import upload_file_to_minio, bucket_molly
from src.utils.utils import get_file_desc
from src.utils.mysql_db import insert_or_update_patient_file_sql


load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "")  # 用于签名和验证 JWT 的密钥
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # 加密算法

router = APIRouter(tags=["file-upload-tumor-normal"])
security = HTTPBearer()

UPLOAD_DIR = Path(g_config["temp"]["upload_files_dir"])
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 5))
target_desc_url = g_config["url"]["target_desc_url"]

async def get_file_info_and_upload(file: UploadFile, file_type: str):
    object_name = f"{uuid.uuid4()}_{file.filename}"
    minio_file_path = f"minio://{bucket_molly}/{object_name}"
    local_file_path = UPLOAD_DIR / object_name
    file_data = await file.read()
    file_size_mb = len(file_data) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制: {MAX_FILE_SIZE_MB} MB")
    file_hash = hashlib.sha256(file_data).hexdigest()
    async with aiofiles.open(local_file_path, "wb") as local_file:
        await local_file.write(file_data)
    # 使用封装的 upload_file_to_minio 方法上传到 MinIO
    upload_file_to_minio(str(local_file_path), bucket_molly, object_name)
    file_desc = await get_file_desc(file.filename, file_data, file.content_type)
    local_file_path.unlink()
    return {
        "file_name": file.filename,
        "file_size": len(file_data),
        "file_type": file_type,
        "file_path": minio_file_path,
        "file_hash": file_hash,
        "file_desc": file_desc
    }



@router.post("/upload_tumor_normal_files", response_model=UploadTumorNormalFilesResponse)
async def upload_tumor_normal_files(
    patient_id: int = Form(...),
    normal_file: UploadFile = File(...),
    tumor_file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UploadTumorNormalFilesResponse:
    # 校验token
    try:
        system_token = credentials.credentials
        payload = decode_vaild(system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid: str = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="无效的用户认证")

        # 处理normal_file（上传并入库，但不影响response）
        normal_info = await get_file_info_and_upload(normal_file, "normal_file")
        await insert_or_update_patient_file_sql(
            patient_id=patient_id,
            unionid=unionid,
            file_name=normal_info["file_name"],
            file_type=normal_info["file_type"],
            file_size=normal_info["file_size"],
            file_path=normal_info["file_path"],
            file_hash=normal_info["file_hash"],
            file_desc=normal_info["file_desc"],
        )
        # 处理tumor_file（上传并入库，并用其信息组装response）
        tumor_info = await get_file_info_and_upload(tumor_file, "tumor_file")

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

        return await upload_tumor_normal_files_api(
            patient_id=patient_id,
            unionid=unionid,
            tumor_file_name=tumor_info["file_name"],
            tumor_file_type=tumor_info["file_type"],
            tumor_file_size=tumor_info["file_size"],
            tumor_file_path=tumor_info["file_path"],
            tumor_file_hash=tumor_info["file_hash"],
            tumor_file_desc=tumor_info["file_desc"],
            normal_file_path=normal_info["file_path"]
        )
    except HTTPException as e:
        raise e    
    except Exception as e:
        logger.error(f"上传文件失败: {e}", exc_info=True)
        return BaseResponse(ok=1, failed=str(e))