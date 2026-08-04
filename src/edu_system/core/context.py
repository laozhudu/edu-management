"""
系统上下文管理
- 线程本地存储当前请求上下文
- 包含用户、学期、校区、权限、trace_id 等
- 供 Feature Flag、审计、日志等使用
"""

import threading
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Optional

# ContextVar 用于异步上下文传递
_current_context: ContextVar[Optional["SystemContext"]] = ContextVar(
    "_current_context", default=None
)

# 线程本地存储（同步代码兼容）
_thread_local = threading.local()


@dataclass
class SystemContext:
    """系统上下文"""

    # 用户信息
    user_id: int = 0
    username: str = ""
    role_codes: list[str] = field(default_factory=list)

    # 环境信息
    school_id: int = 1
    academic_year_id: int = 0
    semester_id: int = 0

    # 运行时状态
    trace_id: str = ""
    ip: str = ""
    user_agent: str = ""

    # 扩展字段
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.role_codes is None:
            self.role_codes = []
        if self.extra is None:
            self.extra = {}


def get_current_context() -> SystemContext | None:
    """获取当前上下文（优先 ContextVar，回退线程本地）"""
    ctx = _current_context.get()
    if ctx is not None:
        return ctx
    return getattr(_thread_local, "context", None)


def set_current_context(ctx: SystemContext | None):
    """设置当前上下文"""
    if ctx is None:
        _current_context.set(None)
        if hasattr(_thread_local, "context"):
            delattr(_thread_local, "context")
    else:
        _current_context.set(ctx)
        _thread_local.context = ctx


def get_trace_id() -> str:
    """获取当前 trace_id（用于日志/追踪）"""
    ctx = get_current_context()
    return ctx.trace_id if ctx else ""


def set_current_user(user_id: int, username: str = "", role_codes: list = None):
    """设置当前用户（快捷方法）"""
    ctx = get_current_context() or SystemContext()
    ctx.user_id = user_id
    ctx.username = username
    ctx.role_codes = role_codes or []
    set_current_context(ctx)


def get_current_user_id() -> int:
    ctx = get_current_context()
    return ctx.user_id if ctx else 0


def get_current_role_codes() -> list[str]:
    ctx = get_current_context()
    return ctx.role_codes if ctx else []


def get_current_school_id() -> int:
    ctx = get_current_context()
    return ctx.school_id if ctx else 1


def get_current_semester_id() -> int:
    ctx = get_current_context()
    return ctx.semester_id if ctx else 0


class ContextManager:
    """上下文管理器（with 语句支持）"""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.old_ctx = None

    def __enter__(self):
        self.old_ctx = get_current_context()
        ctx = SystemContext(**self.kwargs)
        set_current_context(ctx)
        return ctx

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_current_context(self.old_ctx)


def with_context(**kwargs):
    """装饰器：为函数执行期间设置上下文"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with ContextManager(**kwargs):
                return func(*args, **kwargs)

        return wrapper

    return decorator
