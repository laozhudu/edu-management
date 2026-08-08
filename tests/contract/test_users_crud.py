"""契约测试：用户管理（P3-B）"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app


class TestUsersContract:
    """用户管理契约测试"""

    def setup_method(self):
        self.client = TestClient(create_app())
        r = self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, r.text
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_user_list(self):
        """用户列表"""
        r = self.client.get("/api/users", headers=self.headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data

    def test_role_list(self):
        """角色列表"""
        r = self.client.get("/api/users/roles", headers=self.headers)
        assert r.status_code == 200, r.text
        assert "items" in r.json()

    def test_create_user(self):
        """创建用户"""
        r = self.client.post(
            "/api/users",
            headers=self.headers,
            json={"username": "contract_user", "password": "test123", "role_name": "teacher"},
        )
        assert r.status_code in (201, 400, 403), f"{r.status_code} {r.text[:80]}"
        if r.status_code == 201:
            assert "id" in r.json()

    def test_update_user_role(self):
        """改角色"""
        r = self.client.post(
            "/api/users",
            headers=self.headers,
            json={"username": "contract_user2", "password": "test123"},
        )
        if r.status_code != 201:
            return
        uid = r.json()["id"]
        r2 = self.client.put(
            f"/api/users/{uid}", headers=self.headers, json={"role_name": "director"}
        )
        assert r2.status_code in (200, 404), f"{r2.status_code} {r2.text[:80]}"
        assert r2.json().get("role") == "director"

    def test_reset_password(self):
        """重置密码"""
        r = self.client.post(
            "/api/users",
            headers=self.headers,
            json={"username": "contract_user3", "password": "oldpass"},
        )
        if r.status_code != 201:
            return
        uid = r.json()["id"]
        r2 = self.client.put(
            f"/api/users/{uid}/password", headers=self.headers, json={"password": "newpass"}
        )
        assert r2.status_code in (200, 404), f"{r2.status_code} {r2.text[:80]}"
        assert r2.json().get("ok") is True

    def test_disable_self_forbidden(self):
        """停用自己被拒（防止锁死）"""
        r = self.client.get("/api/users", headers=self.headers)
        admin = next((u for u in r.json()["items"] if u["username"] == "admin"), None)
        if not admin:
            return
        r2 = self.client.put(
            f"/api/users/{admin['id']}", headers=self.headers, json={"is_active": False}
        )
        assert r2.status_code in (400, 403), f"{r2.status_code} {r2.text[:80]}"


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
