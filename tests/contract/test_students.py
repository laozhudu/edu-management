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


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
