"""
契约测试
运行：pytest tests/contract/test_*.py -x -v
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


class TestAuthContract:
    """认证接口契约测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """登录获取 token"""
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

    def test_login_success(self):
        """登录成功返回 access_token + refresh_token (HttpOnly Cookie)"""
        # Login already done in setup, just verify we got token
        assert self.access_token is not None

    def test_refresh_token_success(self):
        """刷新令牌成功"""
        # 先登录获取 refresh_token
        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        refresh_token = login_resp.cookies.get("refresh_token")
        assert refresh_token

        # 使用 refresh_token 刷新
        response = self.client.post(
            "/api/auth/refresh",
            cookies={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self):
        """无效 refresh_token 返回 401"""
        response = self.client.post(
            "/api/auth/refresh",
            cookies={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401

    def test_logout(self):
        """登出成功，清除 Cookie"""
        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        refresh_token = login_resp.cookies.get("refresh_token")

        response = self.client.post(
            "/api/auth/logout",
            cookies={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "message" in response.json()
        # Cookie 应被清除
        assert "refresh_token" not in response.cookies

    def test_protected_endpoint_without_token(self):
        """无 Token 访问受保护端点返回 401"""
        response = self.client.get("/api/auth/me")
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self):
        """有效 Token 访问受保护端点成功"""
        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        access_token = login_resp.json()["access_token"]

        response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"

    def test_device_trust_registration(self):
        """设备信任注册"""
        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        access_token = login_resp.json()["access_token"]

        response = self.client.post(
            "/api/auth/device/trust",
            json={"device_name": "我的电脑"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "device_id" in data
        assert data["trusted"] is True

    def test_device_trust_list(self):
        """获取受信设备列表"""
        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        access_token = login_resp.json()["access_token"]

        response = self.client.get(
            "/api/auth/device/trusted",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert isinstance(data["devices"], list)

    def test_device_trust_revoke(self):
        """撤销设备信任"""
        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        access_token = login_resp.json()["access_token"]

        # 先注册一个设备
        reg_resp = self.client.post(
            "/api/auth/device/trust",
            json={"device_name": "测试设备"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        device_id = reg_resp.json()["device_id"]

        # 撤销信任
        response = self.client.delete(
            f"/api/auth/device/trust/{device_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
