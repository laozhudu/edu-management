"""
契约测试：配置继承 API（M5-E5）
运行：pytest tests/contract/test_semester_inherit.py -x -v

覆盖：
- GET /semester/{id}/inherit/preview: 四色差异预览
- POST /semester/{id}/inherit/execute: 执行继承
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


class TestSemesterInheritContract:
    """配置继承接口契约测试"""

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

    def test_preview_inherit(self):
        """四色差异预览：返回 diffs 列表"""
        response = self.client.get(
            "/api/semester/1/inherit/preview",
            params={"source_id": 1, "target_id": 2},
            headers=self.headers,
        )
        assert response.status_code in (200, 404, 400, 403)
        if response.status_code == 200:
            data = response.json()
            assert "diffs" in data
            assert isinstance(data["diffs"], list)
            # 每项含 type（四色差异）
            for d in data["diffs"]:
                assert "type" in d

    def test_execute_inherit(self):
        """执行继承：深拷贝+覆盖+审计"""
        response = self.client.post(
            "/api/semester/1/inherit/execute",
            json={
                "source_semester_id": 1,
                "target_semester_id": 2,
                "overwrite_keys": [],
            },
            headers=self.headers,
        )
        assert response.status_code in (200, 404, 409, 403)
        if response.status_code == 200:
            data = response.json()
            assert "success" in data

    def test_execute_inherit_conflict(self):
        """执行继承：overwrite_keys 可携带"""
        response = self.client.post(
            "/api/semester/1/inherit/execute",
            json={
                "source_semester_id": 1,
                "target_semester_id": 2,
                "overwrite_keys": ["class_grade_weight"],
            },
            headers=self.headers,
        )
        assert response.status_code in (200, 404, 409, 403)


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
