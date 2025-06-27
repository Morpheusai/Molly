from sqlalchemy import Column, BigInteger, String, Text, JSON, TIMESTAMP, text
from src.utils.base import Base

class ToolModel(Base):
    __tablename__ = 'tools'
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='工具ID')
    name = Column(String(32), nullable=False, comment='工具名称')
    description = Column(Text, comment='工具功能描述')
    parameters = Column(JSON, comment='工具参数说明')
    example = Column(Text, comment='工具示例')
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"), comment='更新时间') 