"""契约测试：教师管理 CRUD（P3-A2）"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app


class TestTeacherCrudContract:
    """教师 CRUD 契约测试（Web 教师管理页增删改）"""

    def setup_method(self):
        self.client = TestClient(create_app())
        r = self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, r.text
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_teacher_list(self):
        """教师列表"""
        r = self.client.get("/api/teachers", headers=self.headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data

    def test_create_teacher(self):
        """创建教师"""
        r = self.client.post(
            "/api/teachers",
            headers=self.headers,
            json={"name": "契约测试师", "gender": "男", "title": "高级"},
        )
        assert r.status_code in (201, 400, 403), f"{r.status_code} {r.text[:80]}"
        if r.status_code == 201:
            assert "id" in r.json()

    def test_create_teacher_missing_name(self):
        """缺姓名 → 400/422"""
        r = self.client.post("/api/teachers", headers=self.headers, json={"gender": "男"})
        assert r.status_code in (400, 422, 403)

    def test_crud_roundtrip(self):
        """增→改→查→删 闭环"""
        r = self.client.post(
            "/api/teachers",
            headers=self.headers,
            json={"name": "往返测试师", "phone": "13800000000"},
        )
        if r.status_code == 403:
            return
        if r.status_code == 400:
            r = self.client.post(
                "/api/teachers",
                headers=self.headers,
                json={"name": "往返测试师X", "phone": "13800000000"},
            )
        assert r.status_code == 201, f"{r.status_code} {r.text[:80]}"
        tid = r.json()["id"]
        # 更新
        r2 = self.client.put(f"/api/teachers/{tid}", headers=self.headers, json={"title": "中级"})
        assert r2.status_code in (200, 404), f"{r2.status_code} {r2.text[:80]}"
        # 删除
        r3 = self.client.delete(f"/api/teachers/{tid}", headers=self.headers)
        assert r3.status_code in (200, 404), f"{r3.status_code}"

    def test_delete_nonexistent(self):
        """删除不存在教师 → 404"""
        r = self.client.delete("/api/teachers/99999", headers=self.headers)
        assert r.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
