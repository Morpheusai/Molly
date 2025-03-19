import base64
import os
import re
import uuid
import weblogo

from fastapi import APIRouter, HTTPException
from minio.error import S3Error
from pathlib import Path
from weblogo import LogoData, LogoOptions, LogoFormat

from src.api.protocols import WebLogoRequest
from src.config import g_config
from src.utils.jwt_util import decode_vaild
from src.utils.log import logger
from src.utils.minio import minio_client, bucket_weblogo

TEMP_DIR = g_config["temp"]["weblogo_peptide_sequence_dir"]
TEMP_OUTPUT_IMAGE_DIR = g_config["temp"]["weblogo_output_tmp_image_dir"]
DOWNLOADER_PREFIX = g_config["download"]["output_download_url_prefix"]
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(TEMP_OUTPUT_IMAGE_DIR, exist_ok=True)

SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

router = APIRouter(tags=["weblogo_generate"])

@router.post("/generate_weblogo")
async def generate_weblogo_endpoint(request: WebLogoRequest):
    """
    接口：
    1. 解析 markdown_content 提取 Peptide Sequence
    2. 生成 WebLogo 并返回 base64 png 格式
    """
    try:
        # 验证 token
        payload = decode_vaild(request.system_token, SECRET_KEY, algorithms=[ALGORITHM])
        unionid = payload.get("sub")
        if not unionid:
            raise HTTPException(status_code=401, detail="Invalid or missing unionid")
        
        png_output = generate_weblogo(request.peptide_sequences)

        return {
            "ok": 0,
            "message": "WebLogo generated successfully!",
            "png": png_output
        }

    except HTTPException as e:
        return {
            "ok": 1,
            "failed": e.detail
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "ok": 1,
            "failed": f"Unexpected error: {str(e)}"
        }
    
def generate_weblogo(peptide_sequences: list, logo_type: str = 'png', logo_title: str = "Sequence Motif Analysis", color_scheme: str = "auto"):
    """
    使用 WebLogo 生成序列 Logo 图像。

    参数:
    peptide_sequences (list): 输入的氨基酸或核苷酸序列列表。
    logo_type (str): 输出图像格式，可选 'png', 'jpg', 'eps', 'pdf', 'svg'，默认为 'png'。
    logo_title (str): 图像标题。
    color_scheme (str): 颜色方案，可选 "auto" 或 WebLogo 提供的颜色方案。

    返回:
    str: base64 编码 png 。
    """
    temp_txt_path = Path(TEMP_DIR) / f"{uuid.uuid4().hex}_peptides.txt"
    output_image_name = f"{uuid.uuid4().hex}_weblogo.{logo_type}"
    temp_output_image_path = Path(TEMP_OUTPUT_IMAGE_DIR) / output_image_name
    try:
        
        temp_txt_path.write_text("\n".join(peptide_sequences))

        # 读取序列数据
        with open(temp_txt_path, 'r') as f:
            sequences = weblogo.read_seq_data(f)

        # 创建 WebLogo 输入数据对象
        data = LogoData.from_seqs(sequences)

        # 设置 Logo 生成选项
        options = LogoOptions()
        options.logo_title = logo_title
        options.small_fontsize = 8
        options.title_fontsize = 12
        options.color_scheme = weblogo.std_color_schemes.get(color_scheme, weblogo.std_color_schemes["auto"])
        options.unit_name = "bits"
        options.show_yaxis = True
        options.yaxis_label = "Information (bits)"
        options.yaxis_scale = 2.0
        options.show_xaxis = True
        options.xaxis_label = "Position"
        options.fineprint = "Created by Neo"
        options.show_fineprint = True
        options.stack_width = 10.5
        options.resolution = 300

        # 生成 Logo 格式
        format = LogoFormat(data, options)

        if logo_type.lower() != 'png':
            raise ValueError("当前仅支持 PNG 格式给前端渲染")

        # 生成 Logo 图像
        if logo_type.lower() == 'png':
            logo = weblogo.png_formatter(data, format)
        elif logo_type.lower() in ('jpg', 'jpeg'):
            logo = weblogo.jpeg_formatter(data, format)
        elif logo_type.lower() == 'eps':
            logo = weblogo.eps_formatter(data, format)
        elif logo_type.lower() == 'pdf':
            logo = weblogo.pdf_formatter(data, format)
        elif logo_type.lower() == 'svg':
            logo = weblogo.svg_formatter(data, format)  # 处理 SVG 格式
        else:
            raise ValueError(f"不支持的图像格式: {logo_type}")
        
        with open(temp_output_image_path, "wb") as f:
            f.write(logo)
            
        file_url, error = upload_to_minio(str(temp_output_image_path), output_image_name)
        file_path = file_url if not error else f"{DOWNLOADER_PREFIX}{output_image_name}"
        if file_path.startswith("minio://"):
            logger.info(f"minio上传成功")
            temp_output_image_path.unlink(missing_ok=True)

        base64_string = base64.b64encode(logo).decode('utf-8')
        base64_data = f"data:image/png;base64,{base64_string}"
        logger.info(f"WebLogo PNG Base64 数据已生成")
        temp_txt_path.unlink(missing_ok=True)

        return base64_data

    except Exception as e:
        print(f"生成 WebLogo 时出错: {e}")
        return None

def upload_to_minio(file_path: str, output_filename: str):
    try:
        if not minio_client.bucket_exists(bucket_weblogo):
            minio_client.make_bucket(bucket_weblogo)

        minio_client.fput_object(
            bucket_weblogo,
            output_filename,
            file_path
        )
        return f"minio://{bucket_weblogo}/{output_filename}", None
    except S3Error as e:
        return None, f"上传 MinIO 失败: {e}"