from sqlalchemy import Column, BigInteger, Integer, SmallInteger, String, Text, TIMESTAMP, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship
from src.utils.base import Base

class PredictionDetailModel(Base):
    __tablename__ = 'prediction_details'
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='预测详情ID')
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False, comment='附属病历id')
    prediction_id = Column(BigInteger, ForeignKey('predictions.id'), nullable=False, comment='附属预测id')
    rank = Column(SmallInteger, nullable=False, comment='调用顺序')
    tool_name = Column(String(64), nullable=False, comment='工具名')
    tool_parameters = Column(Text, comment='工具调用参数(JSON字符串)')
    tool_output = Column(Text, comment='工具输出(JSON字符串)')
    status = Column(String(32), nullable=False, default='pending', comment='工具状态')
    start_time = Column(DateTime, nullable=False, comment='调用开始时间')
    end_time = Column(DateTime, comment='调用结束时间')
    elapsed_time = Column(Integer, comment='调用耗时')
    error_message = Column(String(255), comment='错误信息')
    create_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False, comment='创建时间')

    patient = relationship('PatientModel', back_populates='prediction_details')
    prediction = relationship('PredictionModel', back_populates='details') 