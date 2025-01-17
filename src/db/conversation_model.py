
from sqlalchemy import Column, String, CHAR, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from utils.base import Base
from db.message_model import MessageModel

class ConversationModel(Base):
    __tablename__ = 'conversation'

    # 主键字段
    id = Column(CHAR(36), primary_key=True, comment='会话ID')  # 会话 ID

    # 外键字段
    user_id = Column(String(255), ForeignKey('user.user_id'), comment='微信用户ID')  # 微信用户 ID

    # 会话信息字段
    request_id = Column(String(255), nullable=True, comment='请求ID')  # 请求 ID
    session_title = Column(String(255), comment='会话标题')            # 会话标题

    # 时间字段
    create_time = Column(DateTime, default=func.now(), comment='创建时间')  # 创建时间

    # 关系字段
    users = relationship('UserModel', back_populates='conversations')

    messages = relationship('MessageModel', back_populates='conversations')

    def __repr__(self):
        return f"<Conversation(id='{self.id}', user_id='{self.user_id}', session_title='{self.session_title}')>"