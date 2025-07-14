from contextlib import asynccontextmanager
from functools import wraps
from src.utils.base import get_async_session_local, get_sync_session_local
from src.utils import logger





@asynccontextmanager
async def async_session_scope():
    AsyncSessionLocal = get_async_session_local()
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()
        logger.info("[async_session_scope] session closed")


def with_async_session(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        async with async_session_scope() as session:
            return await f(session, *args, **kwargs)
    return wrapper


async def get_async_db():
    AsyncSessionLocal = get_async_session_local()
    db = AsyncSessionLocal()
    logger.info("[get_async_db] session created")
    try:
        yield db
    finally:
        await db.close()
        logger.info("[get_async_db] session closed")

# 同步数据库会话管理
def with_sync_session(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        SyncSessionLocal = get_sync_session_local()
        session = SyncSessionLocal()
        try:
            result = f(session, *args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            logger.info("[with_sync_session] session closed")
    return wrapper
