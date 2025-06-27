from sqlalchemy import Column, BigInteger, Integer, Enum, Text, JSON, SmallInteger, TIMESTAMP, ForeignKey, text
from sqlalchemy.orm import relationship
from src.utils.base import Base

class MessageModel(Base):
    __tablename__ = 'messages'
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='消息ID')
    conversation_id = Column(BigInteger, ForeignKey('conversations.id'), nullable=False, comment='附属会话id')
    type = Column(Enum('user', 'assistant'), nullable=False, comment='消息类型')
    content = Column(Text, nullable=False, comment='内容')
    meta_data = Column(JSON, comment='元数据')
    feedback_like = Column(Integer, comment='点赞数')
    feedback_dislike = Column(Integer, comment='点踩数')
    is_deleted = Column(SmallInteger, default=0, comment='是否删除')
    create_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False, comment='创建时间')

    conversation = relationship('ConversationModel', back_populates='messages')
    questions = relationship('QuestionModel', back_populates='message', cascade='all, delete-orphan') 