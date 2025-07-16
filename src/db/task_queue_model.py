from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, BigInteger, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.utils.base import Base
from datetime import datetime, timezone

class TaskQueueModel(Base):
    __tablename__ = 'task_queue'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    celery_task_id = Column(String(64), nullable=True, unique=True, comment='celery任务ID')
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False, comment='病人ID')
    conversation_id = Column(BigInteger, ForeignKey('conversations.id'), nullable=False, comment='会话ID')
    status = Column(Enum('queued', 'running', 'completed', 'failed'), nullable=False, default='queued', comment='任务状态')
    estimated_time = Column(Float, nullable=False, default=10.0, comment='任务单独执行所需时间（秒）')
    created_at = Column(DateTime, default=lambda: datetime.now(), comment='创建时间')
    updated_at = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now(), comment='更新时间')
    started_at = Column(DateTime, nullable=True, comment='开始执行时间')
    completed_at = Column(DateTime, nullable=True, comment='完成时间')

    patient = relationship('PatientModel', back_populates='tasks')
    conversation = relationship('ConversationModel', back_populates='tasks') 