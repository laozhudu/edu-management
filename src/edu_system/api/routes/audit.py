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
