from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, func, CHAR
from sqlalchemy.orm import relationship
from utils.base import Base


class MessageModel(Base):
    """
    聊天记录模型，表示会话中的一条聊天记录
    """
    __tablename__ = 'message'
    id = Column(CHAR(36), primary_key=True, comment='聊天记录ID')

    conversation_id = Column(CHAR(36), ForeignKey('conversation.id'), comment='会话ID')

    query = Column(String(4096), comment='用户问题')

    response = Column(String(4096), comment='模型回答')
    
    create_time = Column(DateTime, default=func.now(), comment='创建时间')

    conversations = relationship('ConversationModel', back_populates='messages')

    def __repr__(self):
        return f"<Message(id='{self.id}', chat_type='{self.chat_type}', query='{self.query}', response='{self.response}', meta_data='{self.meta_data}', feedback_score='{self.feedback_score}', feedback_reason='{self.feedback_reason}', create_time='{self.create_time}')>"