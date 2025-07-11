from contextlib import asynccontextmanager
from functools import wraps
from src.utils.base import get_async_session_local





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


def with_async_session(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        async with async_session_scope() as session:
            return await f(session, *args, **kwargs)
    return wrapper


async def get_async_db():
    AsyncSessionLocal = get_async_session_local()
    async with AsyncSessionLocal() as db:
        yield db
