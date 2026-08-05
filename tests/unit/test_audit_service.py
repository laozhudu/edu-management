"""
审计日志服务单测（M5-F1：服务日志查看）

覆盖：
- list_logs: 按服务过滤 + 解析 JSON 字段
- count_logs: 总数
- 空表返回空列表
- limit 生效 + 倒序
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from edu_system.models import Base
from edu_system.services.audit import AuditLogService


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _insert_log(session, service: str, method: str, path: str, status: int):
    session.execute(
        text(
            "INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, operator, ip, created_at) "
            "VALUES ('api_requests', 0, 'API_REQUEST', :old, :new, 'admin', '127.0.0.1', '2026-08-05 10:00:00')"
        ),
        {
            "old": f'{{"method": "{method}", "path": "{path}"}}',
            "new": (
                f'{{"status": {status}, "duration_ms": 12, "service": "{service}"}}'
            ),
        },
    )
    session.commit()


class TestAuditLogService:
    def test_list_logs_empty(self, session):
        """空表返回空列表"""
        svc = AuditLogService(session)
        logs = svc.list_logs()
        assert logs == []

    def test_list_logs_by_service(self, session):
        """按服务过滤 + JSON 字段解析"""
        _insert_log(session, "score", "POST", "/api/score", 200)
        _insert_log(session, "attendance", "GET", "/api/attendance", 200)
        _insert_log(session, "score", "GET", "/api/score/1", 200)

        svc = AuditLogService(session)
        logs = svc.list_logs(service_code="score")
        assert len(logs) == 2
        first = logs[0]
        assert first["method"] == "GET"
        assert first["path"] == "/api/score/1"
        assert first["status"] == 200
        assert first["duration_ms"] == 12
        assert first["operator"] == "admin"
        assert first["ip"] == "127.0.0.1"

    def test_count_logs(self, session):
        """总数统计（按服务）"""
        _insert_log(session, "score", "POST", "/api/score", 200)
        _insert_log(session, "attendance", "GET", "/api/attendance", 200)

        svc = AuditLogService(session)
        assert svc.count_logs() == 2
        assert svc.count_logs(service_code="score") == 1

    def test_limit_and_order(self, session):
        """limit 生效 + 倒序（最新在前）"""
        _insert_log(session, "score", "POST", "/api/score/1", 200)
        _insert_log(session, "score", "POST", "/api/score/2", 200)
        _insert_log(session, "score", "POST", "/api/score/3", 201)

        svc = AuditLogService(session)
        logs = svc.list_logs(service_code="score", limit=2)
        assert len(logs) == 2
        # 最新在前：score/3 最新
        assert logs[0]["path"] == "/api/score/3"
