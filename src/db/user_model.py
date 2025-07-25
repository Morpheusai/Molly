from sqlalchemy import Column, String, Enum, Boolean, TIMESTAMP, ForeignKey, func, text
from sqlalchemy.orm import relationship
from src.utils.base import Base

class UserModel(Base):
    __tablename__ = 'users'
    unionid = Column(String(128), primary_key=True, comment='微信UnionID，主键')
    openid = Column(String(128), unique=True, nullable=False, comment='微信OpenID，唯一')
    role = Column(Enum('chief', 'assistant'), nullable=False, comment='角色（主任医师/助手）')
    is_active = Column(Boolean, default=True, comment='是否可用')
    nickname = Column(String(64), comment='昵称')
    phone = Column(String(20), comment='手机号')
    email = Column(String(100), comment='邮箱')
    city = Column(String(64), comment='城市')
    province = Column(String(64), comment='省份')
    country = Column(String(64), comment='国家')
    headimgurl = Column(String(512), comment='头像url')
    created_by = Column(String(128), ForeignKey('users.unionid'), comment='创建者ID，主任医师创建助手时记录')
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"), comment='更新时间')

    # 关系同前
    created_users = relationship('UserModel', remote_side=[unionid], backref='creator', foreign_keys=[created_by])
    user_tokens = relationship('UserTokenModel', back_populates='user', cascade='all, delete-orphan')
    projects = relationship('ProjectModel', back_populates='creator', cascade='all, delete-orphan')
    patients = relationship('PatientModel', back_populates='creator', cascade='all, delete-orphan')
    files = relationship('FileModel', back_populates='uploader', cascade='all, delete-orphan')
    workflows_started = relationship('WorkflowModel', foreign_keys='WorkflowModel.started_by', back_populates='starter')
    workflows_completed = relationship('WorkflowModel', foreign_keys='WorkflowModel.completed_by', back_populates='completer')
    project_members = relationship('ProjectMemberModel', back_populates='user', cascade='all, delete-orphan')
    conversations = relationship('ConversationModel', back_populates='user', cascade='all, delete-orphan')