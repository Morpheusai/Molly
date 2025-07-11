import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

load_dotenv()

user = os.getenv("DB_USER", "")
host = os.getenv("DB_HOST", "")
port = int(os.getenv("DB_PORT", "-1"))
database = os.getenv("DB_NAME", "")
password = os.getenv("DB_PASSWORD", "")
encoded_password = quote_plus(password)

SQLALCHEMY_DATABASE_URI = f"mysql+asyncmy://{user}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4"

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
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
        )
        return sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    else:
        return AsyncSessionLocal

