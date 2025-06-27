from sqlalchemy import Column, BigInteger, Integer, Text, TIMESTAMP, ForeignKey, text
from sqlalchemy.orm import relationship
from src.utils.base import Base

class PredictionModel(Base):
    __tablename__ = 'predictions'
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='预测ID')
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False, comment='附属病历id')
    result = Column(Text, comment='预测结果')
    summary = Column(Text, comment='预测小结')
    create_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False, comment='创建时间')

    patient = relationship('PatientModel', back_populates='predictions')
    details = relationship('PredictionDetailModel', back_populates='prediction', cascade='all, delete-orphan') 