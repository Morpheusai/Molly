import os
import uuid

from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.future import select

from src.api.protocols import BaseResponse
from src.db.user_token_model import UserTokenModel
from src.utils.session import with_async_session

load_dotenv()

# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "")  # 用于签名和验证 JWT 的密钥
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # 加密算法
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))  # JWT Token 过期时间

# 生成 JWT Token,并添加到数据库中


@with_async_session
async def create_system_token(session, unionid: str, wechat_access_token: str):
    expire = datetime.now(timezone.utc) + \
        timedelta(hours=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": unionid, "exp": expire}
    system_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # 查询是否已存在该 unionid 的记录
    existing_token = await session.execute(
        select(UserTokenModel).where(UserTokenModel.unionid == unionid)
    )
    existing_token = existing_token.scalar_one_or_none()

    if existing_token:
        # 如果存在，更新相关字段
        existing_token.wechat_access_token = wechat_access_token
        existing_token.system_token = system_token
        existing_token.expires_at = expire
        existing_token.updata_time = datetime.now()
    else:
        # 如果不存在，创建新记录
        db_token = UserTokenModel(
            id=str(uuid.uuid4()),
            unionid=unionid,
            wechat_access_token=wechat_access_token,
            system_token=system_token,
            expires_at=expire,
            updata_time=datetime.now(),
            create_time=datetime.now()
        )
        session.add(db_token)

    try:
        await session.commit()
        if existing_token:
            await session.refresh(existing_token)
        else:
            await session.refresh(db_token)
        return system_token
    except Exception as e:
        await session.rollback()
        return BaseResponse(
            ok=1,
            failed=str(e)
        )

# 解码并验证 JWT Token


def decode_vaild(token: str, secret_key: str, algorithms: list = None):
    try:
        payload = jwt.decode(token, secret_key, algorithms)
        return payload
    except JWTError:
        return {
            "ok": 1,
            "failed": "用户状态失效"
        }
