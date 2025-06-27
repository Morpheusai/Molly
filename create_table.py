import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

# 确保所有模型都被导入，以便 Base.metadata 能够感知到它们
from src.db import *
from src.utils.base import Base, async_engine

async def create_tables():
    try:
        # 按照依赖顺序删除表（如果需要重建）
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            print("Dropped all tables successfully!")
        
        # 使用 Base.metadata.create_all 一次性创建所有表
        # SQLAlchemy 会自动处理表之间的依赖关系
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("All tables created successfully!")
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_tables())