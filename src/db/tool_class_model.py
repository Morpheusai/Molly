from sqlalchemy import Column, String, DateTime, func, CHAR
from sqlalchemy.orm import relationship

from src.utils.base import Base


class ToolClassModel(Base):
    """工具基本信息表"""
    __tablename__ = 'tool_class'

    id = Column(CHAR(36), primary_key=True, comment='主键ID')
    
    tool_name = Column(String(128), nullable=False, comment='工具名称')
    
    tool_desc = Column(String(512), comment='工具描述')
    
    create_time = Column(DateTime, server_default=func.now(), comment='创建时间')
    
    update_time = Column(DateTime, server_default=func.now(),
                         onupdate=func.now(), comment='更新时间')

    # 使用字符串形式的类名
    files = relationship('ToolFileModel', back_populates='tool_kind')

    def __repr__(self):
        return f"<Tool(id={self.id}, name={self.tool_name})>"
