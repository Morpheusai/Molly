
from sqlalchemy import Column, String, CHAR, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from utils.base import Base
from db.message_model import MessageModel

class ConversationModel(Base):
    __tablename__ = 'conversation'

    # 主键字段
    id = Column(CHAR(36), primary_key=True, comment='会话ID')

    # 外键字段
    user_id = Column(String(255), ForeignKey('user.unionid'), comment='微信用户unionid') 

    # 会话信息字段
    session_title = Column(String(255), comment='会话标题') 
    
    #聊天类型字段
    chat_type = Column(String(50), comment="聊天类型")

    # 时间字段
    create_time = Column(DateTime, default=func.now(), comment='创建时间')

    # 关系字段
    users = relationship('UserModel', back_populates='conversations')

    messages = relationship('MessageModel', back_populates='conversations')

    def __repr__(self):
        return f"<Conversation(id='{self.id}', user_id='{self.user_id}', session_title='{self.session_title}')>"