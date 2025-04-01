from sqlalchemy import Column, String, DateTime, ForeignKey, func, CHAR, Text
from sqlalchemy.orm import relationship

from src.utils.base import Base


class ToolModel(Base):
    """
    工具信息模型，表示工具调用的返回结果
    """
    __tablename__ = 'tool_msg'
    id = Column(CHAR(36), primary_key=True, comment='ID')

    message_id = Column(CHAR(36), ForeignKey(
        'message.id'), comment='关联的聊天记录ID')

    conversation_id = Column(CHAR(36), ForeignKey(
        'conversation.id'), comment='会话ID')

    tool_id = Column(String(128), comment='工具id')

    tool_name = Column(String(128), comment='工具名称')

    tool_args = Column(Text, comment='工具调用参数')

    tool_result = Column(Text, comment='工具返回结果')

    create_time = Column(DateTime, default=func.now(), comment='创建时间')

    tool_result_analysis = Column(Text,  default="", comment='对工具输出结果的分析描述')

    # 关联到MessageModel
    message = relationship('MessageModel', back_populates='tools')

    conversations = relationship('ConversationModel', back_populates='tools')

    def __repr__(self):
        return f"<Tool(id='{self.id}', tool_name='{self.tool_name}', tool_args='{self.tool_args}', tool_result='{self.tool_result}', create_time='{self.create_time}')>"
