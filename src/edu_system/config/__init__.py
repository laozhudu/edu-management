"""
配置管理
使用 pydantic-settings 管理配置
"""

import secrets
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础
    APP_NAME: str = "教务管理系统"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "sqlite:///data/school_data.db"

    # 安全（SECRET_KEY 生产环境须用环境变量注入；未注入时自动生成随机密钥）
    SECRET_KEY: str = Field(
        default="",
        description="JWT 签名密钥，生产环境必须通过环境变量 SECRET_KEY 注入",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 服务器
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # 路径
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    STATIC_DIR: Path = PROJECT_ROOT / "static"
    DATA_DIR: Path = PROJECT_ROOT / "data"
    LOG_DIR: Path = PROJECT_ROOT / "logs"
    CACHE_DIR: Path = PROJECT_ROOT / "data" / "cache"
    STORAGE_DIR: Path = PROJECT_ROOT / "data" / "storage"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# 单例
settings = Settings()

# 导出常用路径
PROJECT_ROOT = settings.PROJECT_ROOT
STATIC_DIR = settings.STATIC_DIR
DATA_DIR = settings.DATA_DIR
LOG_DIR = settings.LOG_DIR
CACHE_DIR = settings.CACHE_DIR
STORAGE_DIR = settings.STORAGE_DIR

# 兼容旧代码：导出模块级常量
APP_NAME = settings.APP_NAME
APP_VERSION = settings.APP_VERSION
DEBUG = settings.DEBUG
DATABASE_URL = settings.DATABASE_URL
# 从 DATABASE_URL 解析数据库文件路径
DB_PATH = str(DATABASE_URL).replace("sqlite:///", "").replace("sqlite://", "")
SECRET_KEY = settings.SECRET_KEY or secrets.token_urlsafe(48)
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS
HOST = settings.HOST
PORT = settings.PORT
CORS_ORIGINS = settings.CORS_ORIGINS

# 确保目录存在
for d in [DATA_DIR, LOG_DIR, CACHE_DIR, STORAGE_DIR, STATIC_DIR]:
    d.mkdir(parents=True, exist_ok=True)
