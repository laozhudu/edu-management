"""
配置文件
"""

import os
import secrets
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 数据库
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "school_data.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# 缓存目录
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 导出目录
EXPORTS_DIR = PROJECT_ROOT / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

# 模板目录
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# 安全配置
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(48)

# 应用信息
APP_NAME = "教务管理系统"
APP_VERSION = "2.0.0"

# 安全配置
SECURITY_CONFIG = {
    "rate_limit_enabled": True,
    "rate_limit_window": 60,
    "rate_limit_max": 200,
    "headers": {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "X-Permitted-Cross-Domain-Policies": "none",
    },
    "csp": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://cdn.jsdelivr.net; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    ),
}
