"""审计日志查询服务（M5-F1：服务日志查看）"""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session


class AuditLogService:
    """审计日志查询（gateway 写入，此处读取）"""

    def __init__(self, session: Session):
        self.session = session

    def list_logs(
        self,
        service_code: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """按服务代码过滤审计日志（含请求方法/路径/状态/耗时）"""
        where = "WHERE table_name = 'api_requests' AND action = 'API_REQUEST'"
        params: dict = {}
        if service_code:
            where += " AND new_values LIKE :svc"
            params["svc"] = f"%{service_code}%"
        where += " ORDER BY id DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        rows = self.session.execute(
            text(
                f"SELECT id, old_values, new_values, operator, ip, created_at "  # nosec B608 — 表名/字段名来自 SQLAlchemy 元数据或白名单校验，非用户输入
                f"FROM audit_logs {where}"
            ),
            params,
        ).fetchall()

        result = []
        for row in rows:
            try:
                old = json.loads(row.old_values or "{}")
                new = json.loads(row.new_values or "{}")
            except (json.JSONDecodeError, TypeError):
                old, new = {}, {}
            result.append(
                {
                    "id": row.id,
                    "method": old.get("method", ""),
                    "path": old.get("path", ""),
                    "status": new.get("status", 0),
                    "duration_ms": new.get("duration_ms", 0),
                    "service": new.get("service", ""),
                    "operator": row.operator,
                    "ip": row.ip,
                    "created_at": (
                        row.created_at.isoformat()
                        if hasattr(row.created_at, "isoformat")
                        else str(row.created_at)
                    ),
                }
            )
        return result

    def count_logs(self, service_code: str | None = None) -> int:
        """日志总数（分页用）"""
        where = "WHERE table_name = 'api_requests' AND action = 'API_REQUEST'"
        params: dict = {}
        if service_code:
            where += " AND new_values LIKE :svc"
            params["svc"] = f"%{service_code}%"
        row = self.session.execute(
            text(f"SELECT COUNT(*) FROM audit_logs {where}"),
            params,  # nosec B608 — 表名/字段名来自 SQLAlchemy 元数据或白名单校验，非用户输入
        ).scalar()
        return int(row or 0)
