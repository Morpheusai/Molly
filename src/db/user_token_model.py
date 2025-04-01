from sqlalchemy import Column, String, Text, TIMESTAMP, CHAR, DateTime
from sqlalchemy.sql import func

from src.utils.base import Base


class UserToken(Base):
    __tablename__ = "user_tokens"

    id = Column(CHAR(36), primary_key=True, comment='主键ID')

    unionid = Column(String(255), nullable=False, comment='普通用户的标识，对当前开发者账号唯一')

    wechat_access_token = Column(
        Text, nullable=False, comment='微信的access_token')

    system_token = Column(Text, nullable=False, comment='系统生成的token')

    expires_at = Column(TIMESTAMP, nullable=False, comment='token过期时间')

    updata_time = Column(DateTime, default=func.now(), comment='更新时间')

    create_time = Column(DateTime, default=func.now(), comment='创建时间')

    def __repr__(self):
        return (
            f"<UserToken(id='{self.id}', unionid='{self.unionid}', "
            f"wechat_access_token='{self.wechat_access_token}', "
            f"system_token='{self.system_token}', expires_at='{self.expires_at}', "
            f"create_time='{self.create_time}')>"
        )
