"""
契约测试：审计日志 API（M5-F1）
运行：pytest tests/contract/test_audit_api.py -x -v

覆盖：
- GET /audit/logs: 日志列表（结构/过滤）
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app


class TestAuditApiContract:
    """审计日志接口契约测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        app = create_app()
        client = TestClient(app)
        self.client = client

        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        self.access_token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    def test_list_logs(self):
        """日志列表：返回 total + logs 结构"""
        response = self.client.get(
            "/api/audit/logs",
            headers=self.headers,
        )
        assert response.status_code in (200, 403)
        if response.status_code == 200:
            data = response.json()
            assert "total" in data
            assert "logs" in data
            assert isinstance(data["logs"], list)

    def test_list_logs_service_filter(self):
        """按服务过滤参数可接受"""
        response = self.client.get(
            "/api/audit/logs",
            params={"service": "score", "limit": 10},
            headers=self.headers,
        )
        assert response.status_code in (200, 403)

    def test_list_logs_requires_auth(self):
        """未登录拒绝"""
        response = self.client.get("/api/audit/logs")
        assert response.status_code in (401, 403)


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
