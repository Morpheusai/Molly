from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, text
from sqlalchemy.orm import relationship
from src.utils.base import Base

class ProjectModel(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='项目ID')
    name = Column(String(64), comment='项目名称')
    created_by = Column(String(128), ForeignKey('users.unionid'), nullable=False, comment='创建者用户ID')
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"), comment='更新时间')

    creator = relationship('UserModel', back_populates='projects')
    patients = relationship('PatientModel', back_populates='project', cascade='all, delete-orphan') 