from sqlalchemy import Column, BigInteger, Integer, String, TIMESTAMP, SmallInteger, ForeignKey, text
from sqlalchemy.orm import relationship
from src.utils.base import Base

class ConversationModel(Base):
    __tablename__ = 'conversations'
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='对话ID')
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False, comment='附属病历id')
    type = Column(String(50), comment='类型')
    title = Column(String(255), comment='对话标题，可自动生成')
    is_deleted = Column(SmallInteger, default=0, comment='是否删除（伪删除）')
    create_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False, comment='创建时间')

    patient = relationship('PatientModel', back_populates='conversations')
    messages = relationship('MessageModel', back_populates='conversation', cascade='all, delete-orphan') 
    tasks = relationship('TaskQueueModel', back_populates='conversation', cascade='all, delete-orphan')  # 关联任务队列 