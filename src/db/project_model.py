from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, text, Enum
from sqlalchemy.orm import relationship
from src.utils.base import Base

class ProjectModel(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='项目ID')
    name = Column(String(64), comment='项目名称')
    created_by = Column(String(128), ForeignKey('users.unionid'), nullable=False, comment='创建者用户ID')
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"), comment='更新时间')
    project_code = Column(String(32), nullable=True, comment='项目编号')
    short_name = Column(String(64), comment='项目简称')
    description = Column(String(256), comment='项目简介')
    project_type = Column(Enum('IIT', '注册试验', '探索性研究'), nullable=False, comment='项目类型')
    indication = Column(String(128), comment='适应症')
    study_phase = Column(Enum('I期', 'II期', 'III期', '未指定', 'IIT'), nullable=False, comment='研究分期')
    is_multicenter = Column(Enum('是', '否'), nullable=False, comment='是否多中心')
    registration_number = Column(String(64), comment='注册号')
    registration_platform_url = Column(String(256), comment='注册平台链接')
    principal_investigator = Column(String(64), comment='项目负责人')
    pi_email = Column(String(100), comment='项目负责人邮箱')
    doctor_enrollment_count = Column(Integer, nullable=False, server_default=text("1"), comment='医生入组人数')
    patient_enrollment_count = Column(Integer, nullable=False, comment='患者入组人数')
    hospital = Column(String(128), nullable=True, comment='所属医院')
    phone = Column(String(32), nullable=True, comment='手机号')
    status = Column(Integer, nullable=False, server_default=text("0"), comment='项目状态：0-保存草稿，1-创建立项')

    creator = relationship('UserModel', back_populates='projects')
    patients = relationship('PatientModel', back_populates='project', cascade='all, delete-orphan')
    members = relationship('ProjectMemberModel', back_populates='project', cascade='all, delete-orphan') 