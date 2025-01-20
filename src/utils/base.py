from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

import json

load_dotenv()

user = os.getenv("DB_USER", "")
host = os.getenv("DB_HOST", "")
port= int(os.getenv("DB_PORT", "-1"))
database = os.getenv("DB_NAME", "")
password = os.getenv("DB_PASSWORD", "")
encoded_password = quote_plus(password)

SQLALCHEMY_DATABASE_URI = f"mysql+asyncmy://{user}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4"

async_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URI,
    echo=True,
    pool_size=10,  # 连接池中保持的连接数
    max_overflow=20,  # 连接池外最多可以创建的连接数
    pool_timeout=30,  # 从连接池获取连接的超时时间（秒）
    pool_recycle=3600,  # 连接回收时间（秒），避免数据库断开连接
    pool_pre_ping=True,  # 每次从连接池获取连接时检查连接是否有效
)


AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

Base: DeclarativeMeta = declarative_base()





