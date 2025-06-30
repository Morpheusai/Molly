from sqlalchemy import Column, Integer, String, Enum, TIMESTAMP, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.utils.base import Base

class WorkflowModel(Base):
    __tablename__ = 'workflows'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='工作流ID')
    patient_id = Column(Integer, ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, comment='所属患者id')
    stage = Column(String(32), nullable=False, comment='阶段（如病历上传、病历解析等）')
    status = Column(Enum('new', 'pending', 'completed'), nullable=False, default='new', comment='状态')
    started_by = Column(String(128), ForeignKey('users.unionid'), comment='开始者')
    started_at = Column(TIMESTAMP, nullable=True, comment='开始时间')
    completed_by = Column(String(128), ForeignKey('users.unionid'), comment='完成者')
    completed_at = Column(TIMESTAMP, nullable=True, comment='完成时间')
    notes = Column(Text, comment='附注')
    rank = Column(Integer, nullable=False, comment='排序')

    patient = relationship('PatientModel', back_populates='workflows')
    starter = relationship('UserModel', foreign_keys=[started_by], back_populates='workflows_started')
    completer = relationship('UserModel', foreign_keys=[completed_by], back_populates='workflows_completed') 