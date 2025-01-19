from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from utils.base import Base

class UserToken(Base):
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True, comment='主键ID')

    unionid = Column(String(255), unique=True, index=True, comment='普通用户的标识，对当前开发者账号唯一')

    wechat_access_token = Column(Text, nullable=False, comment='微信的access_token')

    system_token = Column(Text, nullable=False, comment='系统生成的token')

    expires_at = Column(TIMESTAMP, nullable=False, comment='token过期时间')

    create_time = Column(TIMESTAMP, default=func.now(), comment='创建时间')

    def __repr__(self):
        return (
            f"<UserToken(id='{self.id}', openid='{self.openid}', "
            f"wechat_access_token='{self.wechat_access_token}', "
            f"system_token='{self.system_token}', expires_at='{self.expires_at}', "
            f"created_at='{self.created_at}')>"
        )