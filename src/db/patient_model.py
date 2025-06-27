from sqlalchemy import Column, Integer, String, Enum, Date, Text, TIMESTAMP, ForeignKey, text
from sqlalchemy.orm import relationship
from src.utils.base import Base

class PatientModel(Base):
    """患者信息模型"""
    __tablename__ = 'patients'
    
    # 基本信息
    id = Column(Integer, primary_key=True, autoincrement=True)  # 患者ID，自增主键
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)  # 关联的项目ID
    source_id = Column(Integer, nullable=True, comment='源文件ID')  # 源文件ID
    medical_record_number = Column(String(50))  # 病历号
    name = Column(String(64))  # 患者姓名
    gender = Column(Enum('male', 'female', 'other'))  # 性别：男/女/其他
    birth_date = Column(Date)  # 出生日期
    phone = Column(String(20))  # 联系电话
    email = Column(String(100))  # 电子邮箱
    hospital = Column(String(64))  # 就诊医院
    
    # 医疗信息
    blood_type = Column(Enum('A', 'B', 'AB', 'O', 'unknown'))  # 血型：A/B/AB/O/未知
    tumor_type = Column(String(32))  # 肿瘤类型/癌种
    HLA_type = Column(String(64))  # HLA分型结果
    CDR_type = Column(String(64))  # CDR(互补决定区)数据
    treatment_state = Column(String(64))  # 治疗阶段状态
    additional_info = Column(Text)  # 附加信息/备注
    clinical_medication = Column(Text)  # 临床用药记录
    clinical_diagnosis = Column(Text)  # 临床诊断信息
    
    # 状态和时间信息
    status = Column(Enum('new', 'pending', 'completed'), nullable=False, default='new')  # 状态：新建/处理中/已完成
    created_by = Column(String(128), ForeignKey('users.unionid'), nullable=False, comment='创建者用户ID')  # 创建者（医生）ID
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))  # 创建时间
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))  # 更新时间

    # 关联关系
    project = relationship('ProjectModel', back_populates='patients')  # 关联项目
    creator = relationship('UserModel', back_populates='patients')  # 关联创建者
    files = relationship('FileModel', back_populates='patient', cascade='all, delete-orphan')  # 关联文件
    predictions = relationship('PredictionModel', back_populates='patient', cascade='all, delete-orphan')  # 关联预测结果
    prediction_details = relationship('PredictionDetailModel', back_populates='patient', cascade='all, delete-orphan')  # 关联预测详情
    conversations = relationship('ConversationModel', back_populates='patient', cascade='all, delete-orphan')  # 关联对话记录
    workflows = relationship('WorkflowModel', back_populates='patient', cascade='all, delete-orphan')  # 关联工作流 