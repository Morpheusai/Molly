import os
import httpx

import pandas as pd
from typing import List,Tuple

from src.utils.minio import upload_file_to_minio,download_from_minio_uri
import mimetypes
import hashlib
import base64
from src.config import g_config

target_desc_url = g_config["url"]["target_desc_url"]

#从minio路径获取肽段数
def count_peptides(fasta_path: str) -> int:
    """
    计算 FASTA 字符串中的肽段数量（即 '>' 开头的行数）。
    
    Args:
        fasta_path (str): 肽段的minio路径
    
    Returns:
        int: 肽段数量
    """
    fasta_path=download_from_minio_uri(fasta_path)
    with open(fasta_path, 'r', encoding='utf-8') as f:
        fasta_str = f.read()

    os.remove(fasta_path)
    return sum(1 for line in fasta_str.strip().split('\n') if line.startswith('>'))


#获取滑窗肽段文件
def sliding_window_from_file(input_file: str, window_sizes: List[int], output_file: str) -> None:
    """
    从 FASTA 文件读取序列，进行滑窗切割，并输出到新的 FASTA 文件。
    标识头格式：>原标识_子序列_子序列长度

    参数:
        input_file: 输入 FASTA 文件路径（.fasta 或 .fsa）。
        window_sizes: 滑窗长度的列表（如 [8, 9, 10]）。
        output_file: 输出 FASTA 文件路径。
    """
    # 读取输入文件
    with open(input_file, 'r') as f:
        fasta_content = f.read()

    # 解析原始 FASTA，允许同名头，全部保留
    peptides = []
    current_id = None
    current_seq = []

    for line in fasta_content.split('\n'):
        line = line.strip()
        if line.startswith('>'):
            if current_id is not None:
                peptides.append((current_id, ''.join(current_seq)))
            current_id = line[1:]  # 去掉 '>'
            current_seq = []
        else:
            if line:  # 忽略空行
                current_seq.append(line)

    if current_id is not None:  # 添加最后一条序列
        peptides.append((current_id, ''.join(current_seq)))

    # 生成滑窗子序列并格式化为 FASTA
    output_lines = []
    for peptide_id, seq in peptides:
        for window in window_sizes:
            if window > len(seq):
                continue  # 跳过无效窗口
            for i in range(len(seq) - window + 1):
                subseq = seq[i:i+window]
                # 新标识符格式：>原标识_子序列_子序列长度
                header = f">{peptide_id}_{subseq}_{window}"
                output_lines.append(header)
                output_lines.append(subseq)

    # 写入输出文件
    with open(output_file, 'w') as f:
        f.write('\n'.join(output_lines))


#肽段文件降重，输入字符串
def deduplicate_fasta_by_sequence(fasta_str: str) -> Tuple[str, int, int]:
    lines = fasta_str.strip().split('\n')
    seen_seq = set()
    result = []
    total_before = 0
    total_after = 0
    i = 0
    while i < len(lines):
        if lines[i].startswith('>'):
            total_before += 1
            desc = lines[i]
            i += 1
            # 合并多行序列，直到下一个描述行或文件结束
            seq_parts = []
            while i < len(lines) and not lines[i].startswith('>'):
                seq_parts.append(lines[i].strip())  # 移除行首尾空格
                i += 1
            seq = ''.join(seq_parts)  # 合并为连续序列
            if seq not in seen_seq:
                seen_seq.add(seq)
                result.append(desc)
                result.append(seq)  # 注意：此处改为单行序列输出
                total_after += 1
        else:
            i += 1
    # 输出时每个序列单独一行（即使输入是多行）
    return '\n'.join(result), total_before, total_after

async def get_file_desc(file_name: str, file_data: bytes, content_type: str) -> str:
    text_types = {"text/plain", "application/json", "text/csv", "application/x-fasta","sequence_file"}
    is_text_candidate = (
        content_type in text_types or
        file_name.lower().endswith(".fas") or
        file_name.lower().endswith(".vcf") 
    )
    if is_text_candidate:
        try:
            file_content = file_data.decode("utf-8")
        except UnicodeDecodeError:
            file_content = base64.b64encode(file_data).decode("utf-8")
    else:
        file_content = base64.b64encode(file_data).decode("utf-8")
    request_data = {"file_name": file_name, "file_content": file_content}
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=30.0)) as client:
        try:
            response = await client.post(target_desc_url, json=request_data)
            if response.status_code != 200:
                return f"DescAgent error: {response.status_code} {response.text}"
            return response.json().get("file_description", "")
        except Exception as e:
            return f"DescAgent调用失败: {str(e)}"


async def read_excel_from_minio_to_dictlist_fasta(minio_uri: str, bucket_name: str):
    """
    从MinIO下载Excel文件并转为字典列表，并返回excel和fasta文件的详细信息
    :param minio_uri: MinIO文件地址（如minio://bucket/path/to/file.xlsx）
    :return: {
        'excel_data': List[dict],
        'source_file_info': {...},
        'fasta_file_info': {...}
    }
    """
    # 下载文件到本地
    local_path = download_from_minio_uri(minio_uri)
    # 读取Excel
    df = pd.read_excel(local_path)
    # 转为字典列表
    result = df.to_dict(orient="records")

    # 生成fasta内容
    fasta_lines = []
    for _, row in df.iterrows():
        ref_pep = str(row['Reference_Peptide'])
        consequence = str(row['Consequence'])
        aa_change = str(row['AA_Change']).replace('>', '-')
        mut_context = str(row['mut_context'])
        fasta_id = f">{ref_pep}_{consequence}_{aa_change}"
        fasta_lines.append(fasta_id)
        fasta_lines.append(mut_context)
    fasta_content = "\n".join(fasta_lines)

    # 保存fasta文件
    fasta_path = os.path.splitext(local_path)[0] + ".fasta"
    with open(fasta_path, 'w', encoding='utf-8') as f:
        f.write(fasta_content)

    # 上传fasta到minio
    fasta_minio_path = upload_file_to_minio(fasta_path, bucket_name, os.path.basename(fasta_path))

    # 获取源文件信息
    with open(local_path, 'rb') as f:
        source_data = f.read()
    source_file_name = os.path.basename(local_path)
    source_file_size = len(source_data)
    source_file_type = "vcf_excel"
    source_file_hash = hashlib.sha256(source_data).hexdigest()
    # 获取描述
    try:
        source_file_desc = await get_file_desc(source_file_name, source_data, source_file_type)
    except Exception as e:
        source_file_desc = f"DescAgent调用失败: {str(e)}"
    source_file_info = {
        "file_name": source_file_name,
        "file_size": source_file_size,
        "file_type": source_file_type,
        "file_path": minio_uri,
        "file_hash": source_file_hash,
        "file_desc": source_file_desc,
        "file_source": "1"
    }

    # 获取fasta文件信息
    with open(fasta_path, 'rb') as f:
        fasta_data = f.read()
    fasta_file_name = os.path.basename(fasta_path)
    fasta_file_size = len(fasta_data)
    fasta_file_type = "sequence_file"
    fasta_file_hash = hashlib.sha256(fasta_data).hexdigest()
    try:
        fasta_file_desc = await get_file_desc(fasta_file_name, fasta_data, fasta_file_type)
    except Exception as e:
        fasta_file_desc = f"DescAgent调用失败: {str(e)}"
    fasta_file_info = {
        "file_name": fasta_file_name,
        "file_size": fasta_file_size,
        "file_type": fasta_file_type,
        "file_path": fasta_minio_path,
        "file_hash": fasta_file_hash,
        "file_desc": fasta_file_desc,
        "file_source": "01"  
    }

    # 删除本地文件
    os.remove(local_path)
    os.remove(fasta_path)
    return {
        "excel_data": result,
        "source_file_info": source_file_info,
        "fasta_file_info": fasta_file_info
    }


async def read_excel_from_minio_to_dictlist(minio_uri: str):
    """
    从MinIO下载Excel文件并转为字典列表，并返回excel的list[dict]
    :param minio_uri: MinIO文件地址（如minio://bucket/path/to/file.xlsx）
    :return: {
        'excel_data': List[dict],
        'source_file_info': {...},
        'fasta_file_info': {...}
    }
    """
    # 下载文件到本地
    local_path = download_from_minio_uri(minio_uri)
    # 读取Excel
    df = pd.read_excel(local_path)
    # 转为字典列表
    result = df.to_dict(orient="records")

    # 删除本地文件
    os.remove(local_path)
    return {
        "excel_data": result
    }