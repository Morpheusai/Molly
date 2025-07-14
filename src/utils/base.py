import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
from sqlalchemy import create_engine

load_dotenv()

user = os.getenv("DB_USER", "")
host = os.getenv("DB_HOST", "")
port = int(os.getenv("DB_PORT", "-1"))
database = os.getenv("DB_NAME", "")
password = os.getenv("DB_PASSWORD", "")
encoded_password = quote_plus(password)

SQLALCHEMY_DATABASE_URI = f"mysql+asyncmy://{user}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4"
SYNC_SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4"

if os.getenv("IS_CELERY_WORKER") == "1":
    # Celery worker 不创建全局 engine
    AsyncSessionLocal = None
else:
    async_engine = create_async_engine(
        SQLALCHEMY_DATABASE_URI,
        echo=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
    AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

Base: DeclarativeMeta = declarative_base()

def get_async_session_local():
    if os.getenv("IS_CELERY_WORKER") == "1":
        engine = create_async_engine(
            SQLALCHEMY_DATABASE_URI,
            echo=True,
            pool_size=2,         # 连接池最大连接数，建议调小
            max_overflow=2,      # 超过pool_size后最大可创建的临时连接数，建议调小
            pool_timeout=30,
            pool_recycle=1800,   # 连接最大复用时间（秒），建议缩短
            pool_pre_ping=True,
        )
        return sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    else:
        return AsyncSessionLocal

# 同步数据库连接
sync_engine = create_engine(
    SYNC_SQLALCHEMY_DATABASE_URI,
    echo=True,
    pool_size=5,         # 连接池最大连接数，建议调小
    max_overflow=5,      # 超过pool_size后最大可创建的临时连接数，建议调小
    pool_timeout=30,
    pool_recycle=1800,   # 连接最大复用时间（秒），建议缩短
    pool_pre_ping=True,
)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)

def get_sync_session_local():
    return SyncSessionLocal

