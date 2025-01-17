from sqlalchemy import Column, String, CHAR, DateTime,func,Integer
from sqlalchemy.orm import relationship
from utils.base import Base
from db.conversation_model import ConversationModel
class UserModel(Base):
    __tablename__ = 'user'

    unionid = Column(String(128), primary_key=True, comment='用户统一标识。针对一个微信开放平台账号下的应用，同一用户的unionid是唯一的')
    
    openid = Column(String(128), unique=True, nullable=False, comment='普通用户的标识，对当前开发者账号唯一')
    
    nickname = Column(String(64), comment='普通用户昵称')
    
    sex = Column(Integer, comment='普通用户性别，1为男性，2为女性')
    
    province = Column(String(64), comment='普通用户个人资料填写的省份')
    
    city = Column(String(64), comment='普通用户个人资料填写的城市')
    
    country = Column(String(64), comment='国家，如中国为CN')
    
    headimgurl = Column(String(512), comment='用户头像，最后一个数值代表正方形头像大小')
    
    privilege = Column(String(512), comment='用户特权信息，json数组，如微信沃卡用户为（chinaunicom）')

    create_time = Column(DateTime, default=func.now(), comment='创建时间')

    # 关系字段
    conversations = relationship('ConversationModel', back_populates='users')

    def __repr__(self):
        return f"<unionid='{self.unionid}', User( openid='{self.openid}', nickname='{self.nickname}', sex={self.sex}, province='{self.province}', city='{self.city}', country='{self.country}', headimgurl='{self.headimgurl}', privilege={self.privilege}, )>"