"""
审计日志模块 - 自动记录关键操作
使用 SQLAlchemy 事件监听，在 before_flush 时自动捕获变更
"""

import json

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from edu_system.core.permissions import get_current_user
from edu_system.models import AuditLog

# 需要审计的表（排除高频/临时表）
AUDIT_TABLES = {
    "students",
    "teachers",
    "classes",
    "exams",
    "scores",
    "enrollments",
    "semesters",
    "subjects",
    "audit_logs",
}

# 排除的字段（不记录变更）
EXCLUDE_FIELDS = {"created_at", "updated_at", "password_hash", "photo", "photo_mime"}


def _get_changed_data(obj, action: str) -> tuple:
    """获取对象变更前后的数据"""
    insp = inspect(obj)

    if action == "INSERT":
        old = None
        new = {
            c.key: getattr(obj, c.key)
            for c in insp.mapper.column_attrs
            if c.key not in EXCLUDE_FIELDS
        }
    elif action == "DELETE":
        old = {
            c.key: getattr(obj, c.key)
            for c in insp.mapper.column_attrs
            if c.key not in EXCLUDE_FIELDS
        }
        new = None
    else:  # UPDATE
        old = {}
        new = {}
        for attr in insp.attrs:
            key = attr.key
            if key in EXCLUDE_FIELDS:
                continue
            hist = attr.history
            if hist.has_changes():
                old[key] = hist.deleted[0] if hist.deleted else getattr(obj, key)
                new[key] = hist.added[0] if hist.added else getattr(obj, key)

    return old, new


def _audit_listener(session: Session, flush_context, instances):
    """SQLAlchemy before_flush 事件监听器"""
    user = get_current_user()
    operator = (
        user.display_name
        if user and hasattr(user, "display_name")
        else (user.username if user else "system")
    )

    for obj in session.new | session.dirty | session.deleted:
        table_name = obj.__tablename__ if hasattr(obj, "__tablename__") else ""
        if table_name not in AUDIT_TABLES:
            continue

        # 确定操作类型
        if obj in session.new:
            action = "INSERT"
        elif obj in session.deleted:
            action = "DELETE"
        else:
            action = "UPDATE"

        old_values, new_values = _get_changed_data(obj, action)

        # 获取记录 ID
        pk = inspect(obj).identity[0] if inspect(obj).identity else 0

        # 创建审计日志
        audit = AuditLog(
            table_name=table_name,
            record_id=pk,
            action=action,
            old_values=(
                json.dumps(old_values, ensure_ascii=False, default=str) if old_values else None
            ),
            new_values=(
                json.dumps(new_values, ensure_ascii=False, default=str) if new_values else None
            ),
            operator=operator,
            ip=None,  # 可后续扩展从 request 获取
        )
        session.add(audit)


def audit_init(engine):
    """初始化审计监听器（应用启动时调用一次）"""
    event.listen(Session, "before_flush", _audit_listener)
    print("[Audit] 审计监听器已启用")


def query_audit_logs(
    session: Session,
    table_name: str = None,
    record_id: int = None,
    action: str = None,
    operator: str = None,
    start_date=None,
    end_date=None,
    page: int = 1,
    page_size: int = 50,
):
    """查询审计日志"""
    from sqlalchemy import desc

    q = session.query(AuditLog)

    if table_name:
        q = q.filter(AuditLog.table_name == table_name)
    if record_id:
        q = q.filter(AuditLog.record_id == record_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if operator:
        q = q.filter(AuditLog.operator == operator)
    if start_date:
        q = q.filter(AuditLog.created_at >= start_date)
    if end_date:
        q = q.filter(AuditLog.created_at <= end_date)

    total = q.count()
    q = q.order_by(desc(AuditLog.created_at))
    q = q.offset((page - 1) * page_size).limit(page_size)

    items = q.all()
    return items, total


def manual_audit(
    session: Session,
    table_name: str,
    record_id: int,
    action: str,
    old_values: dict = None,
    new_values: dict = None,
    operator: str = None,
):
    """手动记录审计日志（用于复杂业务操作）"""
    import json

    user = get_current_user()
    op = operator or (user.display_name if user and hasattr(user, "display_name") else "system")

    audit = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        old_values=json.dumps(old_values, ensure_ascii=False, default=str) if old_values else None,
        new_values=json.dumps(new_values, ensure_ascii=False, default=str) if new_values else None,
        operator=op,
    )
    session.add(audit)
    session.flush()
