"""
权限系统 - 轻量级 RBAC
核心：枚举定义权限 + 装饰器保护 Service 方法 + View 层菜单显隐
"""

from collections.abc import Callable
from enum import StrEnum
from functools import wraps
from typing import Any

from edu_system.core.result import ErrorCodes, Result


class Permission(StrEnum):
    """权限枚举 - 按模块分组，易扩展"""

    # 学生管理
    STUDENT_VIEW = "student:view"
    STUDENT_CREATE = "student:create"
    STUDENT_EDIT = "student:edit"
    STUDENT_DELETE = "student:delete"
    STUDENT_IMPORT = "student:import"
    STUDENT_EXPORT = "student:export"
    STUDENT_BATCH = "student:batch"  # 批量操作

    # 学籍变动
    ENROLLMENT_TRANSFER = "enrollment:transfer"
    ENROLLMENT_STATUS = "enrollment:status"
    ENROLLMENT_UPGRADE = "enrollment:upgrade"

    # 成绩管理
    SCORE_VIEW = "score:view"
    SCORE_ENTRY = "score:entry"
    SCORE_EDIT = "score:edit"
    SCORE_PUBLISH = "score:publish"
    SCORE_STATS = "score:stats"
    SCORE_REPORT = "score:report"

    # 教师管理
    TEACHER_VIEW = "teacher:view"
    TEACHER_EDIT = "teacher:edit"
    TEACHER_ASSIGN = "teacher:assign"

    # 考试管理
    EXAM_VIEW = "exam:view"
    EXAM_EDIT = "exam:edit"
    EXAM_ARRANGE = "exam:arrange"

    # 考勤管理
    ATTENDANCE_VIEW = "attendance:view"
    ATTENDANCE_ENTRY = "attendance:entry"
    ATTENDANCE_STATS = "attendance:stats"
    ATTENDANCE_APPROVE = "attendance:approve"

    # 基础配置
    CONFIG_VIEW = "config:view"
    CONFIG_EDIT = "config:edit"

    # 系统维护
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_RESTORE = "system:restore"
    SYSTEM_INIT = "system:init"
    SYSTEM_AUDIT = "system:audit"
    SYSTEM_ADMIN = "system:admin"

    # 数据锁定
    DATA_UNLOCK = "data:unlock"


# 角色默认权限映射（可后续迁移到数据库）
ROLE_PERMISSIONS = {
    "admin": [p.value for p in Permission],
    "director": [
        Permission.STUDENT_VIEW.value,
        Permission.STUDENT_CREATE.value,
        Permission.STUDENT_EDIT.value,
        Permission.STUDENT_IMPORT.value,
        Permission.STUDENT_EXPORT.value,
        Permission.STUDENT_BATCH.value,
        Permission.ENROLLMENT_TRANSFER.value,
        Permission.ENROLLMENT_STATUS.value,
        Permission.ENROLLMENT_UPGRADE.value,
        Permission.SCORE_VIEW.value,
        Permission.SCORE_ENTRY.value,
        Permission.SCORE_EDIT.value,
        Permission.SCORE_PUBLISH.value,
        Permission.SCORE_STATS.value,
        Permission.SCORE_REPORT.value,
        Permission.TEACHER_VIEW.value,
        Permission.TEACHER_EDIT.value,
        Permission.TEACHER_ASSIGN.value,
        Permission.EXAM_VIEW.value,
        Permission.EXAM_EDIT.value,
        Permission.EXAM_ARRANGE.value,
        Permission.ATTENDANCE_VIEW.value,
        Permission.ATTENDANCE_ENTRY.value,
        Permission.ATTENDANCE_STATS.value,
        Permission.ATTENDANCE_APPROVE.value,
        Permission.CONFIG_VIEW.value,
        Permission.CONFIG_EDIT.value,
        Permission.SYSTEM_BACKUP.value,
        Permission.SYSTEM_AUDIT.value,
        Permission.DATA_UNLOCK.value,
    ],
    "teacher": [
        Permission.STUDENT_VIEW.value,
        Permission.SCORE_VIEW.value,
        Permission.SCORE_ENTRY.value,
        Permission.SCORE_EDIT.value,
        Permission.EXAM_VIEW.value,
        Permission.ATTENDANCE_VIEW.value,
        Permission.ATTENDANCE_ENTRY.value,
    ],
    "reader": [
        Permission.STUDENT_VIEW.value,
        Permission.SCORE_VIEW.value,
        Permission.TEACHER_VIEW.value,
        Permission.EXAM_VIEW.value,
        Permission.CONFIG_VIEW.value,
        Permission.ATTENDANCE_VIEW.value,
    ],
}


# 当前用户上下文（运行时注入）
_current_user = None


def set_current_user(user):
    """登录时调用，注入当前用户对象"""
    global _current_user
    _current_user = user


def get_current_user():
    """获取当前用户"""
    return _current_user


def clear_current_user():
    """登出时调用"""
    global _current_user
    _current_user = None


def has_permission(perm: Permission) -> bool:
    """检查当前用户是否拥有权限"""
    user = get_current_user()
    if not user:
        return False
    # 支持 user.permissions 为列表或逗号分隔字符串
    perms = user.permissions
    if isinstance(perms, str):
        perms = [p.strip() for p in perms.split(",") if p.strip()]
    return perm.value in perms


def require_permission(*perms: Permission):
    """
    装饰器：保护 Service 方法，无权限返回 Result.fail
    用法：
        @require_permission(Permission.STUDENT_EDIT)
        def update_student(self, ...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for perm in perms:
                if not has_permission(perm):
                    return Result.fail(
                        f"权限不足：需要 {perm.value}",
                        ErrorCodes.PERMISSION_DENIED,
                    )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*perms: Permission):
    """装饰器：满足任一权限即可"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not any(has_permission(p) for p in perms):
                return Result.fail(
                    f"权限不足：需要以下任一权限 {[p.value for p in perms]}",
                    ErrorCodes.PERMISSION_DENIED,
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator


# View 层辅助：菜单/按钮显隐
def can(perm: Permission) -> bool:
    """模板/View 中调用：`if can(Permission.STUDENT_EDIT): btn.show()`"""
    return has_permission(perm)


def cannot(perm: Permission) -> bool:
    return not can(perm)
