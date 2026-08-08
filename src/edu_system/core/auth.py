"""
JWT 认证核心模块
- Access Token (15min) + Refresh Token (7天)
- HttpOnly Cookie 存储 Refresh Token
- 设备指纹 (UA + IP + Canvas) + 信任设备管理
- 依赖 python-jose + passlib
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from edu_system.config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# JWT 配置
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# 设备信任配置
DEVICE_TRUST_EXPIRE_DAYS = 30
DEVICE_FINGERPRINT_FIELDS = [
    "user_agent",
    "accept_language",
    "screen_resolution",
    "timezone",
    "canvas_fingerprint",
]


@dataclass
class TokenPair:
    """令牌对"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


@dataclass
class DeviceInfo:
    """设备信息"""

    device_id: str
    device_name: str
    fingerprint: str
    user_agent: str
    ip: str
    trusted: bool
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bool(pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return str(pwd_context.hash(password))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """创建访问令牌 (JWT)"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return str(jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM))


def create_refresh_token(data: dict) -> str:
    """创建刷新令牌 (JWT)"""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return str(jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM))


def decode_token(token: str) -> dict:
    """解码并验证令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise ValueError("Invalid token")
    else:
        return dict(payload)


def generate_device_fingerprint(request_data: dict[str, Any]) -> str:
    """生成设备指纹

    组合：User-Agent + Accept-Language + 屏幕分辨率 + 时区 + Canvas 指纹
    """
    parts = []
    for field in DEVICE_FINGERPRINT_FIELDS:
        value = request_data.get(field, "")
        parts.append(str(value))

    # 加入 IP 作为盐值
    ip = request_data.get("ip", "")
    parts.append(ip)

    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def generate_device_id() -> str:
    """生成设备 ID"""
    return secrets.token_urlsafe(16)


def create_token_pair(
    user_id: int,
    device_id: str | None = None,
    permissions: list[str] | None = None,
    roles: list[str] | None = None,
) -> TokenPair:
    """创建令牌对 (Access + Refresh)"""
    now = datetime.now(UTC)
    access_expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    access_payload = {
        "sub": str(user_id),
        "type": "access",
        "device_id": device_id,
        "iat": int(now.timestamp()),
        "exp": int(access_expire.timestamp()),
        "permissions": permissions or [],
        "roles": roles or [],
    }

    refresh_payload = {
        "sub": str(user_id),
        "type": "refresh",
        "device_id": device_id,
        "iat": int(now.timestamp()),
        "exp": int(refresh_expire.timestamp()),
    }

    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def refresh_access_token(refresh_token: str) -> tuple[str, int]:
    """使用 Refresh Token 刷新 Access Token

    Returns:
        (new_access_token, expires_in_seconds)
    """
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise ValueError("Not a refresh token")

    user_id = int(payload["sub"])
    device_id = payload.get("device_id")

    token_pair = create_token_pair(user_id, device_id)
    return token_pair.access_token, token_pair.expires_in


def verify_refresh_token(refresh_token: str) -> dict:
    """验证 Refresh Token 有效性，返回 payload"""
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise ValueError("Not a refresh token")

    return payload


# 设备信任管理相关（数据库操作需在 Service 层实现）
# 这里只定义接口和数据结构


class DeviceTrustService:
    """设备信任管理服务 (需配合数据库使用)"""

    @staticmethod
    def register_trusted_device(
        user_id: int,
        device_name: str,
        fingerprint: str,
        user_agent: str,
        ip: str,
    ) -> DeviceInfo:
        """注册受信设备"""
        device_id = generate_device_id()
        now = datetime.utcnow()
        expires_at = now + timedelta(days=DEVICE_TRUST_EXPIRE_DAYS)

        return DeviceInfo(
            device_id=device_id,
            device_name=device_name,
            fingerprint=fingerprint,
            user_agent=user_agent,
            ip=ip,
            trusted=True,
            created_at=now,
            expires_at=expires_at,
        )

    @staticmethod
    def verify_device_trust(
        user_id: int,
        fingerprint: str,
        user_agent: str,
        ip: str,
    ) -> DeviceInfo | None:
        """验证设备是否受信 (需查数据库)"""
        # 实际实现需查询 device_trusts 表
        return None

    @staticmethod
    def revoke_device_trust(user_id: int, device_id: str) -> bool:
        """撤销设备信任"""
        # 实际实现需更新数据库
        return True

    @staticmethod
    def list_trusted_devices(user_id: int) -> list[DeviceInfo]:
        """列出用户的受信设备"""
        # 实际实现需查询数据库
        return []


def get_current_user_id_from_token(token: str) -> int | None:
    """从 Access Token 获取用户 ID"""
    try:
        payload = decode_token(token)
        if payload.get("type") == "access":
            return int(payload["sub"])
    except (ValueError, KeyError):
        pass
    return None


def get_device_id_from_token(token: str) -> str | None:
    """从 Token 获取设备 ID"""
    try:
        payload = decode_token(token)
        return payload.get("device_id")
    except ValueError:
        return None
