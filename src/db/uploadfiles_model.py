from sqlalchemy import Column, String, CHAR, Integer, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from src.utils.base import Base
import uuid
class UploadedFile(Base):
    __tablename__ = 'uploaded_files'

    # 主键字段
    id = Column(CHAR(36), primary_key=True, default=uuid.uuid4, comment='文件ID')

    # 外键字段
    conversation_id = Column(CHAR(36), ForeignKey('conversation.id'), nullable=False, comment='会话ID')

    # 文件信息字段
    file_name = Column(String(255), comment='文件名')
    file_type = Column(String(50), comment='文件类型')
    file_size = Column(Integer, comment='文件大小')
    # file_content = Column(CustomLargeBinary, comment='文件内容（存储二进制内容）')
    file_path = Column(String(255), comment='文件路径（MinIO路径）')

    file_hash = Column(String(64), comment='文件内容哈希值，用于比较文件内容是否相同')  # 通常SHA256是64个字符
    file_status = Column(Boolean, default=False, comment='文件状态，True表示上传成功可读取，False表示不可用')

    # 时间字段
    create_time = Column(DateTime, default=func.now(), comment='创建时间')

    # 关系字段
    conversation = relationship('ConversationModel', back_populates='uploaded_files')

    def __repr__(self):
        return (f"<UploadedFile(id='{self.id}', file_name='{self.file_name}', "
                f"file_path='{self.file_path}', file_hash='{self.file_hash}', "
                f"file_status='{self.file_status}')>")