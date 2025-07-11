from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, text, UniqueConstraint
from sqlalchemy.orm import relationship
from src.utils.base import Base

class ProjectMemberModel(Base):
    __tablename__ = 'project_members'
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    user_id = Column(String(128), ForeignKey('users.unionid'), nullable=False)
    role = Column(String(32), default='member', comment='成员角色')
    joined_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), comment='加入时间')

    project = relationship('ProjectModel', back_populates='members')
    user = relationship('UserModel', back_populates='project_members')

    __table_args__ = (
        UniqueConstraint('project_id', 'user_id', name='uix_project_user'),
    ) 