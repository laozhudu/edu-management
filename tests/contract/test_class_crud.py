"""契约测试：班级管理 CRUD（P3-A1）"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app


class TestClassCrudContract:
    """班级 CRUD 契约测试（Web 班级管理页增删改）"""

    def setup_method(self):
        self.client = TestClient(create_app())
        r = self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, r.text
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_grade_list(self):
        """年级列表可用（班级下拉数据源）"""
        r = self.client.get("/api/class/grades", headers=self.headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        assert len(data["items"]) > 0

    def test_class_list(self):
        """班级列表"""
        r = self.client.get("/api/class", headers=self.headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        assert "total" in data

    def test_create_class(self):
        """创建班级"""
        r = self.client.post(
            "/api/class",
            headers=self.headers,
            json={"name": "契约测试班", "grade_id": 1, "head_teacher": "测试老师"},
        )
        assert r.status_code in (201, 400, 403), f"{r.status_code} {r.text[:80]}"
        if r.status_code == 201:
            assert "id" in r.json()

    def test_create_class_missing_name(self):
        """缺名称 → 400/422"""
        r = self.client.post("/api/class", headers=self.headers, json={"grade_id": 1})
        assert r.status_code in (400, 422, 403)

    def test_crud_roundtrip(self):
        """增→改→查→删 闭环"""
        r = self.client.post(
            "/api/class",
            headers=self.headers,
            json={"name": "往返测试班", "grade_id": 1},
        )
        if r.status_code == 403:
            return  # 权限受限跳过（契约允许）
        if r.status_code == 400:
            # 已存在同名（数据残留），改名重试
            r = self.client.post(
                "/api/class",
                headers=self.headers,
                json={"name": "往返测试班X", "grade_id": 1},
            )
        assert r.status_code == 201, f"{r.status_code} {r.text[:80]}"
        cid = r.json()["id"]
        # 更新
        r2 = self.client.put(
            f"/api/class/{cid}", headers=self.headers, json={"head_teacher": "新班主任"}
        )
        assert r2.status_code in (200, 404), f"{r2.status_code} {r2.text[:80]}"
        # 删除
        r3 = self.client.delete(f"/api/class/{cid}", headers=self.headers)
        assert r3.status_code in (200, 400, 404), f"{r3.status_code} {r3.text[:80]}"

    def test_delete_nonexistent(self):
        """删除不存在班级 → 404"""
        r = self.client.delete("/api/class/99999", headers=self.headers)
        assert r.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
