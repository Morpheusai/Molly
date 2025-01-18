from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
import os

import json

def load_config(config_path=None):
    if config_path is None:
        # 获取当前脚本所在目录的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建 config.json 的完整路径
        config_path = os.path.join(current_dir, '../..', 'config', 'config.json')
    
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        return config_data
    except FileNotFoundError:
        print(f"配置文件 {config_path} 未找到。")
        return {}
    except json.JSONDecodeError:
        print(f"读取配置文件 {config_path} 时发生错误，可能是格式错误。")
        return {}

config_data=load_config()
mysql_config = config_data.get('msyql', {})

user = mysql_config.get('user', 'default_user')
host = mysql_config.get('host', 'default_host')
port=mysql_config.get('port', 'default_host')
database = mysql_config.get('database', 'default_database')
password = mysql_config.get('password', 'default_password')
encoded_password = quote_plus(password)
""
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





