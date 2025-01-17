from sqlalchemy import Column, String, CHAR, DateTime,func
from sqlalchemy.orm import relationship
from utils.base import Base
from db.conversation_model import ConversationModel
class UserModel(Base):
    __tablename__ = 'user'

    # 主键字段
    id = Column(CHAR(36), primary_key=True, comment='用户ID')  # 用户ID

    # 请求相关字段
    request_id = Column(String(255), nullable=True, comment='请求ID')  # 请求 ID
    user_id = Column(String(255), unique=True, comment='微信用户ID')   # 微信用户 ID
    user_name = Column(String(255), comment='微信名')                 # 微信名

    # 用户信息字段
    phone = Column(String(20), unique=True, nullable=True, comment='用户电话')   # 用户电话
    email = Column(String(255), unique=True, nullable=True, comment='用户邮箱')  # 用户邮箱

    create_time = Column(DateTime, default=func.now(), comment='创建时间')       #创建时间

    # 关系字段（如果需要）
    conversations = relationship('ConversationModel', back_populates='users')

    def __repr__(self):
        return f"<User(id='{self.id}', user_id='{self.user_id}', user_name='{self.user_name}')>"