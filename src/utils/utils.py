import os

from typing import List,Tuple

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