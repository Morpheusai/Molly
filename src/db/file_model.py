from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Text, Boolean, SmallInteger, text
from sqlalchemy.orm import relationship
from src.utils.base import Base

class FileModel(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='文件ID')
    patient_id = Column(Integer, ForeignKey('patients.id', ondelete='CASCADE'), nullable=True, comment='所属病历id')
    upload_by = Column(String(128), ForeignKey('users.unionid'), nullable=False, comment='上传者-医生id')
    file_name = Column(String(128), comment='文件名')
    file_type = Column(String(32), comment='文件类型（病历、测序...）')
    file_size = Column(Integer, comment='文件大小（字节）')
    file_desc = Column(String(255), comment='文件描述')
    file_path = Column(String(128), comment='文件路径')
    file_hash = Column(String(64), comment='文件hash')
    file_status = Column(SmallInteger, comment='文件状态')
    file_source = Column(String(128), comment='文件来源') #0代表用户上传，1表示系统中间生成文件，01代表fasta文件是由vcf文件转换而来得到的，02代表fasta文件是由用户上传得到的
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    is_deleted = Column(SmallInteger, default=0, comment='是否删除（伪删除）')

    patient = relationship('PatientModel', back_populates='files')
    uploader = relationship('UserModel', back_populates='files') 