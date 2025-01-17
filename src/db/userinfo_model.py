from sqlalchemy import Column, Integer, String, JSON, CHAR
from sqlalchemy.orm import relationship
from utils.base import Base


class UserInfo(Base):
    """
    微信用户信息模型，表示微信用户的基本信息
    """
    __tablename__ = 'userinfo'
    
    id = Column(CHAR(36), primary_key=True, comment='用户ID')
    
    openid = Column(String(128), unique=True, nullable=False, comment='普通用户的标识，对当前开发者账号唯一')
    
    nickname = Column(String(128), comment='普通用户昵称')
    
    sex = Column(Integer, comment='普通用户性别，1为男性，2为女性')
    
    province = Column(String(64), comment='普通用户个人资料填写的省份')
    
    city = Column(String(64), comment='普通用户个人资料填写的城市')
    
    country = Column(String(64), comment='国家，如中国为CN')
    
    headimgurl = Column(String(512), comment='用户头像，最后一个数值代表正方形头像大小')
    
    privilege = Column(JSON, comment='用户特权信息，json数组，如微信沃卡用户为（chinaunicom）')
    
    unionid = Column(String(128), unique=True, comment='用户统一标识。针对一个微信开放平台账号下的应用，同一用户的unionid是唯一的')

    def __repr__(self):
        return f"<User(id='{self.id}', openid='{self.openid}', nickname='{self.nickname}', sex={self.sex}, province='{self.province}', city='{self.city}', country='{self.country}', headimgurl='{self.headimgurl}', privilege={self.privilege}, unionid='{self.unionid}')>"