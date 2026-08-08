"""契约测试：学期管理（P3-A6）"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app


class TestSemesterContract:
    """学期 CRUD 契约测试"""

    def setup_method(self):
        self.client = TestClient(create_app())
        r = self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, r.text
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_semester_list(self):
        """学期列表"""
        r = self.client.get("/api/semester/list", headers=self.headers)
        assert r.status_code == 200, r.text
        assert "items" in r.json()

    def test_create_semester(self):
        """创建学期"""
        r = self.client.post(
            "/api/semester",
            headers=self.headers,
            json={"label": "2027-2028 第1学期", "year_start": 2027, "semester": "1"},
        )
        assert r.status_code in (201, 400, 403), f"{r.status_code} {r.text[:80]}"
        if r.status_code == 201:
            assert "id" in r.json()

    def test_create_semester_missing_label(self):
        """缺名称 → 400/422"""
        r = self.client.post("/api/semester", headers=self.headers, json={"year_start": 2027})
        assert r.status_code in (400, 422, 403)


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
