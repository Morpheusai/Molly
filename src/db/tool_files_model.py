from sqlalchemy import Column, String, Text, DateTime, ForeignKey, func, CHAR
from sqlalchemy.orm import relationship

from src.utils.base import Base


class ToolFileModel(Base):
    """工具关联文件表"""
    __tablename__ = 'tool_files'

    id = Column(CHAR(36), primary_key=True, comment='主键ID')

    tool_id = Column(CHAR(36), ForeignKey('tool_class.id'),
                     nullable=False, comment='关联工具ID')

    file_url = Column(String(512), unique=True,
                      nullable=False, comment='文件存储路径')  # 设置唯一键

    tool_llm_content = Column(Text, comment='LLM生成的内容')

    create_time = Column(DateTime, server_default=func.now(), comment='创建时间')

    update_time = Column(DateTime, server_default=func.now(),
                         onupdate=func.now(), comment='更新时间')

    # 使用字符串形式的类名
    tool_kind = relationship('ToolClassModel', back_populates='files')

    def __repr__(self):
        return f"<ToolFile(id={self.id}, tool_id={self.tool_id})>"
