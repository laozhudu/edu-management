"""核心模块统一导出"""

from edu_system.core.audit import audit_init, manual_audit, query_audit_logs
from edu_system.core.permissions import (
    Permission,
    can,
    cannot,
    clear_current_user,
    get_current_user,
    has_permission,
    require_any_permission,
    require_permission,
    set_current_user,
)
from edu_system.core.result import ErrorCodes, Result

__all__ = [
    # result
    "Result",
    "ErrorCodes",
    # permissions
    "Permission",
    "require_permission",
    "require_any_permission",
    "can",
    "cannot",
    "has_permission",
    "set_current_user",
    "get_current_user",
    "clear_current_user",
    # audit
    "audit_init",
    "query_audit_logs",
    "manual_audit",
]
