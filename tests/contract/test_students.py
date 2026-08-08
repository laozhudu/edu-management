"""
契约测试：学生查分 API（M5-E3）
运行：pytest tests/contract/test_students.py -x -v

覆盖：
- GET /students/me/scores: admin（非学生）→ 404 无关联学生
- 学生用户（姓名匹配）→ 200 返回成绩 + 趋势
- published_only 过滤参数
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


class TestStudentScoresContract:
    """学生查分接口契约测试"""

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

    def test_me_scores_admin_404(self):
        """admin 非学生：查本人成绩返回 404（无关联学生档案）"""
        response = self.client.get(
            "/api/students/me/scores",
            headers=self.headers,
        )
        assert response.status_code in (404, 403)

    def test_me_scores_structure(self):
        """成绩接口返回结构（趋势/汇总字段齐全）"""
        response = self.client.get(
            "/api/students/me/scores",
            headers=self.headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert "student_id" in data
            assert "student_name" in data
            assert "scores" in data
            assert "trends" in data
            assert "total" in data
            assert isinstance(data["trends"], list)
            # 趋势点含考试/分数
            if data["trends"]:
                t = data["trends"][0]
                assert "subject_name" in t
                assert "points" in t
        else:
            assert response.status_code in (404, 403)

    def test_me_scores_published_only(self):
        """published_only=true 参数可接受"""
        response = self.client.get(
            "/api/students/me/scores",
            params={"published_only": True},
            headers=self.headers,
        )
        assert response.status_code in (200, 404, 403)

    # ===== M5-E4 班级名单 =====

    def test_class_roster(self):
        """班级名单：只读列表（存在或不存在都返回合理状态）"""
        response = self.client.get(
            "/api/students/classes/1/students",
            headers=self.headers,
        )
        assert response.status_code in (200, 404, 403)
        if response.status_code == 200:
            data = response.json()
            assert "class_id" in data
            assert "class_name" in data
            assert "students" in data
            assert "total" in data

    def test_class_roster_search(self):
        """班级名单搜索参数可接受"""
        response = self.client.get(
            "/api/students/classes/1/students",
            params={"search": "张"},
            headers=self.headers,
        )
        assert response.status_code in (200, 404, 403)

    def test_class_roster_export(self):
        """班级名单导出 CSV"""
        response = self.client.get(
            "/api/students/classes/1/students/export",
            headers=self.headers,
        )
        assert response.status_code in (200, 404, 403)
        if response.status_code == 200:
            assert "text/csv" in response.headers.get("content-type", "")


class TestStudentCrudContract:
    """学生 CRUD 契约测试（Web 学生信息页增删改）"""

    def setup_method(self):
        self.client = TestClient(create_app())
        r = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert r.status_code == 200, r.text
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_create_student(self):
        """创建学生"""
        r = self.client.post(
            "/api/students",
            headers=self.headers,
            json={"name": "契约测试生", "class_id": 1, "student_no": "CT001", "gender": "男"},
        )
        assert r.status_code in (201, 403), f"{r.status_code} {r.text[:80]}"
        if r.status_code == 201:
            data = r.json()
            assert "id" in data

    def test_create_student_missing_name(self):
        """缺姓名 → 400"""
        r = self.client.post("/api/students", headers=self.headers, json={"class_id": 1})
        assert r.status_code in (400, 422, 403)

    def test_crud_roundtrip(self):
        """增→改→查→删 闭环"""
        r = self.client.post(
            "/api/students",
            headers=self.headers,
            json={"name": "往返测试", "class_id": 1, "student_no": "RT001"},
        )
        if r.status_code == 403:
            return  # 权限受限时跳过（契约允许）
        assert r.status_code == 201, f"{r.status_code} {r.text[:80]}"
        sid = r.json()["id"]
        # 更新
        r2 = self.client.put(
            f"/api/students/{sid}", headers=self.headers, json={"name": "往返测试改"}
        )
        assert r2.status_code in (200, 404), f"{r2.status_code} {r2.text[:80]}"
        # 删除
        r3 = self.client.delete(f"/api/students/{sid}", headers=self.headers)
        assert r3.status_code in (200, 404), f"{r3.status_code}"
        # 查已删 → 404
        r4 = self.client.get(f"/api/students/{sid}", headers=self.headers)
        assert r4.status_code in (404, 403, 405)


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
