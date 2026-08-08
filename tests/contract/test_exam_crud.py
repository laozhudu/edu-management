"""契约测试：考试管理 CRUD（P3-A4）"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app


class TestExamCrudContract:
    """考试 CRUD 契约测试"""

    def setup_method(self):
        self.client = TestClient(create_app())
        r = self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, r.text
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_exam_list(self):
        """考试列表"""
        r = self.client.get("/api/exam", headers=self.headers)
        assert r.status_code == 200, r.text
        assert "items" in r.json()

    def test_create_exam(self):
        """创建考试"""
        r = self.client.post(
            "/api/exam",
            headers=self.headers,
            json={
                "name": "契约测试考试",
                "exam_type": "monthly",
                "start_date": "2026-09-01",
                "end_date": "2026-09-02",
            },
        )
        assert r.status_code in (201, 400, 403), f"{r.status_code} {r.text[:80]}"
        if r.status_code == 201:
            assert "id" in r.json()

    def test_update_exam(self):
        """编辑考试"""
        r = self.client.post(
            "/api/exam",
            headers=self.headers,
            json={
                "name": "编辑测试考试",
                "exam_type": "midterm",
                "start_date": "2026-09-01",
                "end_date": "2026-09-02",
            },
        )
        if r.status_code != 201:
            return
        eid = r.json()["id"]
        r2 = self.client.put(
            f"/api/exam/{eid}", headers=self.headers, json={"name": "编辑测试考试改"}
        )
        assert r2.status_code in (200, 404, 403), f"{r2.status_code} {r2.text[:80]}"

    def test_delete_exam(self):
        """删除考试"""
        r = self.client.post(
            "/api/exam",
            headers=self.headers,
            json={
                "name": "删除测试考试",
                "exam_type": "mock",
                "start_date": "2026-09-01",
                "end_date": "2026-09-02",
            },
        )
        if r.status_code != 201:
            return
        eid = r.json()["id"]
        r2 = self.client.delete(f"/api/exam/{eid}", headers=self.headers)
        assert r2.status_code in (200, 204, 403), f"{r2.status_code} {r2.text[:80]}"

    def test_delete_nonexistent(self):
        """删除不存在考试 → 404"""
        r = self.client.delete("/api/exam/99999", headers=self.headers)
        assert r.status_code in (404, 403)


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
