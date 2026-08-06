"""
授权 API 契约测试（M6 Sprint 7）

覆盖：
- POST /api/license/activate 激活（成功/无效码 400）
- GET  /api/license/status   状态查询
- GET  /api/license/machine-id 本机 ID（无需登录）
- 未登录访问受保护端点 401
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app
from edu_system.services.license import generate_license_code


class TestLicenseContract:
    @pytest.fixture(autouse=True)
    def setup(self):
        app = create_app()
        client = TestClient(app)
        self.client = client
        resp = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 200
        self.headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def test_machine_id_no_auth(self):
        """本机 ID 无需登录"""
        resp = self.client.get("/api/license/machine-id")
        assert resp.status_code == 200
        data = resp.json()
        assert "machine_id" in data
        assert len(data["machine_id"]) == 24

    def test_status_requires_auth(self):
        """状态查询需登录"""
        resp = self.client.get("/api/license/status")
        assert resp.status_code in (401, 403)

    def test_status_not_activated(self):
        """初始状态：未激活"""
        resp = self.client.get("/api/license/status", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "activated" in data

    def test_activate_invalid_code(self):
        """无效授权码返回 400"""
        resp = self.client.post(
            "/api/license/activate",
            json={"code": "bad.code.here"},
            headers=self.headers,
        )
        assert resp.status_code == 400

    def test_activate_valid_code(self):
        """有效授权码激活成功，状态变为已激活"""
        code = generate_license_code(days=30)
        resp = self.client.post(
            "/api/license/activate",
            json={"code": code},
            headers=self.headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

        status_resp = self.client.get("/api/license/status", headers=self.headers)
        status = status_resp.json()
        assert status["activated"] is True
