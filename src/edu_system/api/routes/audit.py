"""审计日志 API 路由（M5-F1：服务日志查看）"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from edu_system.api.deps import get_db, require_permission
from edu_system.core.permissions import Permission
from edu_system.services.audit import AuditLogService

router = APIRouter(prefix="/audit", tags=["审计"])


@router.get("/logs")
def list_audit_logs(
    service: str | None = Query(None, description="按服务代码过滤"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.SYSTEM_AUDIT)),
):
    """服务访问日志（gateway 审计记录查询）"""
    svc = AuditLogService(db)
    logs = svc.list_logs(service_code=service, limit=limit, offset=offset)
    total = svc.count_logs(service_code=service)
    return {"total": total, "logs": logs}


@router.get("/operations")
def list_operation_logs(
    table_name: str | None = Query(None, description="按表过滤（students/teachers/...）"),
    record_id: int | None = Query(None, description="按记录 ID 过滤"),
    action: str | None = Query(None, description="INSERT/UPDATE/DELETE"),
    operator: str | None = Query(None, description="按操作者过滤"),
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.SYSTEM_AUDIT)),
):
    """业务操作审计（谁在何时改了什么记录，含新旧值）"""
    from datetime import date, datetime

    from edu_system.core.audit import query_audit_logs

    def _parse(s: str):
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            try:
                return date.fromisoformat(s)
            except Exception:
                return None

    start = _parse(start_date) if start_date else None
    end = _parse(end_date) if end_date else None
    items, total = query_audit_logs(
        db,
        table_name=table_name,
        record_id=record_id,
        action=action,
        operator=operator,
        start_date=start,
        end_date=end,
        page=page,
        page_size=page_size,
    )
    # items 原始是 AuditLog 对象 → 序列化
    return {"total": total, "items": [_serialize_log(i) for i in items]}


def _serialize_log(item) -> dict:
    """AuditLog → dict（解析 JSON 字段）"""
    import json as _json

    def _try(s):
        if not s:
            return None
        try:
            return _json.loads(s)
        except Exception:
            return s

    return {
        "id": item.id,
        "table_name": item.table_name,
        "record_id": item.record_id,
        "action": item.action,
        "old_values": _try(item.old_values),
        "new_values": _try(item.new_values),
        "operator": item.operator,
        "ip": item.ip,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }
