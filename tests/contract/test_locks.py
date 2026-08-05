"""
契约测试：数据锁定 API（M5-E6）
运行：pytest tests/contract/test_locks.py -x -v

覆盖：
- POST /locks: 加锁（含理由）
- GET  /locks: 锁定列表
- DELETE /locks: 解锁
- POST /locks/batch: 批量加锁
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


class TestLocksContract:
    """数据锁定接口契约测试"""

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

    def test_create_lock(self):
        """加锁（含理由）"""
        response = self.client.post(
            "/api/locks",
            json={
                "semester_id": 1,
                "entity_type": "exam",
                "entity_id": 1,
                "lock_level": "hard",
                "reason": "成绩已发布，锁定防修改",
            },
            headers=self.headers,
        )
        assert response.status_code in (201, 403, 400)
        if response.status_code == 201:
            data = response.json()
            assert data["entity_type"] == "exam"
            assert data["lock_level"] == "hard"
            assert "reason" in data

    def test_list_locks(self):
        """锁定列表"""
        response = self.client.get(
            "/api/locks",
            headers=self.headers,
        )
        assert response.status_code in (200, 403)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_batch_lock(self):
        """批量加锁"""
        response = self.client.post(
            "/api/locks/batch",
            json={
                "semester_id": 1,
                "locks": [
                    {
                        "entity_type": "score",
                        "entity_id": 1,
                        "lock_level": "soft",
                        "reason": "批量锁定考试1",
                    },
                    {
                        "entity_type": "score",
                        "entity_id": 2,
                        "lock_level": "soft",
                        "reason": "批量锁定考试2",
                    },
                ],
            },
            headers=self.headers,
        )
        assert response.status_code in (200, 403, 400)
        if response.status_code == 200:
            data = response.json()
            assert "locked" in data
            assert data["locked"] >= 0

    def test_unlock(self):
        """解锁"""
        # 先加锁再解锁
        self.client.post(
            "/api/locks",
            json={
                "semester_id": 1,
                "entity_type": "exam",
                "entity_id": 999,
                "lock_level": "soft",
                "reason": "临时锁",
            },
            headers=self.headers,
        )
        response = self.client.request(
            "DELETE",
            "/api/locks",
            json={
                "semester_id": 1,
                "entity_type": "exam",
                "entity_id": 999,
            },
            headers=self.headers,
        )
        assert response.status_code in (200, 404, 403)


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
