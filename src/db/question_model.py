from sqlalchemy import Column, BigInteger, SmallInteger, String, TIMESTAMP, ForeignKey, text
from sqlalchemy.orm import relationship
from src.utils.base import Base

class QuestionModel(Base):
    __tablename__ = 'questions'
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='扩展问ID')
    message_id = Column(BigInteger, ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, comment='消息id')
    rank = Column(SmallInteger, nullable=False, comment='排列顺序')
    content = Column(String(500), nullable=False, comment='内容')
    is_used = Column(SmallInteger, default=0, comment='是否被点击')
    create_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False, comment='创建时间')

    message = relationship('MessageModel', back_populates='questions') 