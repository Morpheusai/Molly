import os

from src.utils.minio import upload_file_to_minio,download_from_minio_uri


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