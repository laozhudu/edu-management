"""
Feature Flag 系统
- JSON 文件配置 + 热加载（文件修改自动重载）
- 支持角色灰度、百分比灰度、校区灰度
- @feature_flag 装饰器保护接口
- 无数据库、热加载、~40 行核心代码
"""

import json
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

from edu_system.core.context import get_current_context


class FeatureFlags:
    """Feature Flag 管理器"""

    _cache: dict[str, Any] = {}
    _mtime: float = 0
    _config_path: Path = Path(__file__).parent.parent / "config" / "features.json"

    @classmethod
    def _load(cls) -> dict[str, Any]:
        """加载配置文件，支持热加载"""
        if not cls._config_path.exists():
            return {}

        mtime = cls._config_path.stat().st_mtime
        if mtime != cls._mtime:
            try:
                cls._cache = json.loads(cls._config_path.read_text(encoding="utf-8"))
                cls._mtime = mtime
            except (json.JSONDecodeError, OSError):
                # 配置文件损坏，保持旧缓存
                pass
        return cls._cache

    @classmethod
    def _get_flag(cls, key: str) -> dict[str, Any] | None:
        """获取单个 flag 配置"""
        flags = cls._load()
        return flags.get(key)

    @classmethod
    def is_enabled(
        cls,
        key: str,
        context: Any | None = None,
        user_id: int | None = None,
        role_codes: list[str] | None = None,
        school_id: int | None = None,
    ) -> bool:
        """
        检查 feature 是否启用

        支持：
        - 基础开关 enabled
        - 角色灰度 roles: []
        - 百分比灰度 percentage: 0-100
        - 校区灰度 schools: []
        - 用户白名单 users: []
        """
        flag = cls._get_flag(key)
        if not flag or not flag.get("enabled", False):
            return False

        # 从 context 补充参数
        if context is not None:
            user_id = user_id or getattr(context, "user_id", None)
            role_codes = role_codes or getattr(context, "role_codes", [])
            school_id = school_id or getattr(context, "school_id", None)

        # 角色灰度
        roles = flag.get("roles", [])
        if roles and role_codes and not any(r in role_codes for r in roles):
            return False

        # 校区灰度
        schools = flag.get("schools", [])
        if schools and school_id and school_id not in schools:
            return False

        # 用户白名单
        users = flag.get("users", [])
        if users and user_id and user_id not in users:
            return False

        # 百分比灰度（基于 user_id 一致性哈希）
        percentage = flag.get("percentage", 100)
        if percentage < 100 and user_id is not None:
            # 一致性哈希：同一用户始终命中同一桶
            bucket = (hash(f"{key}:{user_id}") % 100) + 1
            if bucket > percentage:
                return False

        return True

    @classmethod
    def get_flag_config(cls, key: str) -> dict[str, Any] | None:
        """获取完整 flag 配置（用于管理界面）"""
        return cls._get_flag(key)

    @classmethod
    def list_all(cls) -> dict[str, Any]:
        """列出所有 flags（用于管理界面）"""
        return cls._load()

    @classmethod
    def reload(cls):
        """强制重载"""
        cls._mtime = 0
        cls._load()


def feature_flag(key: str, raise_on_disabled: bool = True):
    """
    Feature Flag 装饰器

    用法：
        @feature_flag("new_schedule_engine")
        def generate_schedule(...):
            ...

    参数：
        key: feature key
        raise_on_disabled: 禁用时是否抛 404（False 则返回 None/跳过）
    """

    def decorator(func: Callable):
        import asyncio

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 从 kwargs 获取 context（FastAPI 依赖注入通常放在 kwargs）
            context = kwargs.get("_context") or kwargs.get("context")
            user_id = kwargs.get("user_id")
            role_codes = kwargs.get("role_codes")
            school_id = kwargs.get("school_id")

            # 也支持从 Request 获取
            request = kwargs.get("request")
            if request and hasattr(request, "state"):
                context = context or getattr(request.state, "context", None)

            enabled = FeatureFlags.is_enabled(
                key,
                context=context,
                user_id=user_id,
                role_codes=role_codes,
                school_id=school_id,
            )

            if not enabled:
                if raise_on_disabled:
                    raise HTTPException(status_code=404, detail=f"Feature '{key}' is not enabled")
                return None

            return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 从 kwargs 获取 context（FastAPI 依赖注入通常放在 kwargs）
            context = kwargs.get("_context") or kwargs.get("context")
            user_id = kwargs.get("user_id")
            role_codes = kwargs.get("role_codes")
            school_id = kwargs.get("school_id")

            request = kwargs.get("request")
            if request and hasattr(request, "state"):
                context = context or getattr(request.state, "context", None)

            enabled = FeatureFlags.is_enabled(
                key,
                context=context,
                user_id=user_id,
                role_codes=role_codes,
                school_id=school_id,
            )

            if not enabled:
                if raise_on_disabled:
                    raise HTTPException(status_code=404, detail=f"Feature '{key}' is not enabled")
                return None

            return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# 便捷函数：在模板/前端判断
def is_feature_enabled(key: str, **context_kwargs) -> bool:
    """模板/前端调用：判断 feature 是否启用"""
    return FeatureFlags.is_enabled(key, **context_kwargs)


# FastAPI 依赖注入：获取 feature 状态
def get_feature_flags(request: Request) -> dict[str, bool]:
    """获取当前用户可见的所有 feature 状态（用于前端渲染）"""
    context = get_current_context()
    flags = FeatureFlags.list_all()
    result = {}
    for key, config in flags.items():
        result[key] = FeatureFlags.is_enabled(key, context=context)
    return result


# 默认配置文件模板（首次运行自动创建）
DEFAULT_FEATURES_CONFIG = {
    "new_schedule_engine": {
        "enabled": True,
        "percentage": 20,
        "roles": ["admin", "director"],
        "description": "新版排课引擎（OR-Tools）",
    },
    "new_score_import": {
        "enabled": True,
        "percentage": 100,
        "description": "新版成绩导入（支持拖拽/粘贴/预览）",
    },
    "new_report_engine": {
        "enabled": False,
        "percentage": 0,
        "roles": ["admin"],
        "description": "新版报表引擎（docxtpl + WeasyPrint）",
    },
    "mobile_app_api": {"enabled": True, "percentage": 100, "description": "移动端 API 接口"},
    "ai_assist": {
        "enabled": False,
        "percentage": 5,
        "roles": ["director", "teacher"],
        "description": "AI 辅助功能（成绩分析/预警）",
    },
}


def ensure_features_config():
    """确保配置文件存在（启动时调用）"""
    config_path = Path(__file__).parent.parent / "config" / "features.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        config_path.write_text(
            json.dumps(DEFAULT_FEATURES_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8"
        )
