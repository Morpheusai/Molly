import asyncio

from src.utils.base import Base, get_async_session_local

# 确保所有模型都被导入，以便 Base.metadata 能够感知到它们
from src.db import *

async def create_tables():
    # 获取异步engine
    AsyncSessionLocal = get_async_session_local()
    async_engine = AsyncSessionLocal.kw['bind'] if hasattr(AsyncSessionLocal, 'kw') and 'bind' in AsyncSessionLocal.kw else AsyncSessionLocal().bind
    try:
        # 按照依赖顺序删除表（如果需要重建）
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            print("Dropped all tables successfully!")
        # 创建所有表
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("All tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_tables())