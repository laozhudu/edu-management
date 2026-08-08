"""
授权许可服务 — 安装授权码 + 使用许可校验（M6 Sprint 7）

机制：
- 安装授权码：由安装方生成（基于机器特征），用户输入后激活
- 激活信息持久化到 settings 表（license_activated / license_code / license_expires）
- 许可校验：startup/API 层调用 check_license()，未激活/过期则拒绝关键操作
- 宽松模式：本地开发默认不强制（可通过环境变量 EDU_LICENSE_REQUIRED=1 开启）
"""

import hashlib
import hmac
import socket
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from edu_system.database import get_session
from edu_system.models import Setting

# settings 表键名
KEY_ACTIVATED = "license_activated"
KEY_CODE = "license_code"
KEY_EXPIRES = "license_expires"
KEY_MACHINE_ID = "license_machine_id"

# 默认许可时长（天），激活时生效
DEFAULT_LICENSE_DAYS = 365

# 授权码签名密钥（发布版内置；开源版可留空=不校验签名仅校验格式）
_SECRET = "edu-system-2026-license-key"


def get_machine_id() -> str:
    """生成稳定的机器特征 ID（MAC 地址 + 主机名哈希）"""
    try:
        mac = uuid.getnode()
        host = socket.gethostname()
        raw = f"{mac}:{host}:{uuid.getnode()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]
    except Exception:
        return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:24]


def generate_license_code(machine_id: str | None = None, days: int = DEFAULT_LICENSE_DAYS) -> str:
    """生成授权码：mach_id.days.signature（签名=HMAC-SHA256 前16位）"""
    mid = machine_id or get_machine_id()
    payload = f"{mid}.{days}"
    sig = hmac.new(_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload}.{sig}"


def verify_license_code(code: str, machine_id: str | None = None) -> dict:
    """校验授权码，返回 {valid, reason, days, expires}"""
    mid = machine_id or get_machine_id()
    parts = code.strip().split(".")
    if len(parts) != 3:
        return {"valid": False, "reason": "授权码格式错误"}
    code_mid, days_str, sig = parts
    try:
        days = int(days_str)
    except ValueError:
        return {"valid": False, "reason": "授权码天数无效"}

    # 校验机器绑定（授权码携带的机器 ID 必须匹配当前机器）
    if code_mid != mid:
        return {"valid": False, "reason": "授权码与本机不匹配"}

    # 校验签名（_SECRET 为空时跳过签名校验）
    if _SECRET:
        expected = hmac.new(
            _SECRET.encode(), f"{code_mid}.{days_str}".encode(), hashlib.sha256
        ).hexdigest()[:16]
        if not hmac.compare_digest(expected, sig):
            return {"valid": False, "reason": "授权码签名无效"}

    expires = datetime.now() + timedelta(days=days)
    return {"valid": True, "reason": "ok", "days": days, "expires": expires.isoformat()}


class LicenseService:
    """授权许可服务"""

    def __init__(self, session: Session | None = None):
        self.session = session or get_session()

    # ===== 激活 =====

    def activate(self, code: str) -> dict:
        """激活：校验授权码并写入 settings"""
        result = verify_license_code(code)
        if not result["valid"]:
            return {"success": False, **result}

        mid = get_machine_id()
        self._set(KEY_ACTIVATED, "1")
        self._set(KEY_CODE, code.strip())
        self._set(KEY_EXPIRES, result["expires"])
        self._set(KEY_MACHINE_ID, mid)
        self.session.commit()
        return {"success": True, "message": "授权成功", "expires": result["expires"]}

    # ===== 查询 =====

    def get_status(self) -> dict:
        """获取授权状态"""
        activated = self._get(KEY_ACTIVATED) == "1"
        expires_str = self._get(KEY_EXPIRES)
        code = self._get(KEY_CODE)
        mid = self._get(KEY_MACHINE_ID)

        status = {
            "activated": activated,
            "code": code or "",
            "machine_id": mid or get_machine_id(),
            "expires": expires_str,
            "days_left": None,
        }
        if activated and expires_str:
            try:
                expires = datetime.fromisoformat(expires_str)
                days_left = max(0, (expires - datetime.now()).days)
                status["days_left"] = days_left
                status["expired"] = days_left <= 0
            except ValueError:
                status["expired"] = True
        return status

    # ===== 校验 =====

    def check_license(self, required: bool = False) -> dict:
        """许可校验：required=True 时未激活/过期返回拒绝

        开发环境宽松模式：EDU_LICENSE_REQUIRED 未设置时仅警告不拒绝。
        """
        import os

        status = self.get_status()
        hard_required = required or os.environ.get("EDU_LICENSE_REQUIRED") == "1"

        if not status["activated"]:
            return {
                "allowed": not hard_required,
                "reason": "未激活" if hard_required else "未激活（宽松模式）",
                **status,
            }
        if status.get("expired"):
            return {
                "allowed": not hard_required,
                "reason": "许可已过期" if hard_required else "许可已过期（宽松模式）",
                **status,
            }
        return {"allowed": True, "reason": "ok", **status}

    # ===== 内部辅助 =====

    def _get(self, key: str) -> str | None:
        row = self.session.query(Setting).filter(Setting.key == key).first()
        return row.value if row else None

    def _set(self, key: str, value: str):
        row = self.session.query(Setting).filter(Setting.key == key).first()
        if row:
            row.value = value
        else:
            self.session.add(Setting(key=key, value=value))
