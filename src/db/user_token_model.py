from sqlalchemy import Column, String, Text, TIMESTAMP, DateTime, ForeignKey, CHAR, text
from sqlalchemy.orm import relationship
from src.utils.base import Base

class UserTokenModel(Base):
    __tablename__ = 'user_tokens'
    id = Column(CHAR(36), primary_key=True, comment='主键ID')
    unionid = Column(String(128), ForeignKey('users.unionid', ondelete='CASCADE'), nullable=False, comment='微信UnionID')
    wechat_access_token = Column(Text, nullable=False, comment='微信的access_token')
    system_token = Column(Text, nullable=False, comment='系统生成的token')
    expires_at = Column(TIMESTAMP, nullable=False, comment='token过期时间')
    updata_time = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"), comment='更新时间')
    create_time = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')

    user = relationship('UserModel', back_populates='user_tokens') 