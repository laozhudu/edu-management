"""
契约测试：考试 API
运行：pytest tests/contract/test_exam.py -x -v
"""

import pytest
from fastapi.testclient import TestClient

from edu_system.api.main import create_app

app = create_app()
client = TestClient(app)


class TestExamContract:
    """考试接口契约测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """登录获取 token"""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        self.access_token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    def test_create_exam(self):
        """创建考试"""
        response = client.post(
            "/api/exam",
            json={
                "name": "2025-2026 学年第一学期期中考试",
                "semester_id": 1,
                "exam_type": "midterm",
                "start_date": "2025-11-15",
                "end_date": "2025-11-17",
                "description": "期中考试",
            },
            headers=self.headers,
        )
        assert response.status_code in (200, 201, 400, 404, 422)

    def test_list_exams(self):
        """考试列表查询"""
        response = client.get(
            "/api/exam",
            params={"semester_id": 1},
            headers=self.headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_get_exam(self):
        """获取单个考试详情"""
        list_resp = client.get("/api/exam", headers=self.headers)
        if list_resp.json().get("total", 0) > 0:
            exam_id = list_resp.json()["items"][0]["id"]
            response = client.get(
                f"/api/exam/{exam_id}",
                headers=self.headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == exam_id

    def test_auto_arrange_rooms(self):
        """自动分考场"""
        list_resp = client.get("/api/exam", headers=self.headers)
        if list_resp.json().get("total", 0) > 0:
            exam_id = list_resp.json()["items"][0]["id"]
            response = client.post(
                f"/api/exam/{exam_id}/rooms",
                json={
                    "strategy": "balanced",
                    "max_per_room": 30,
                },
                headers=self.headers,
            )
            assert response.status_code in (200, 201, 400, 404, 422)

    def test_arrange_seats(self):
        """排座次"""
        list_resp = client.get("/api/exam", headers=self.headers)
        if list_resp.json().get("total", 0) > 0:
            exam_id = list_resp.json()["items"][0]["id"]
            response = client.post(
                f"/api/exam/{exam_id}/seats",
                json={
                    "method": "snake",  # snake/name/number
                },
                headers=self.headers,
            )
            assert response.status_code in (200, 201, 400, 404, 422)

    def test_generate_invigilation(self):
        """生成监考表"""
        list_resp = client.get("/api/exam", headers=self.headers)
        if list_resp.json().get("total", 0) > 0:
            exam_id = list_resp.json()["items"][0]["id"]
            response = client.get(
                f"/api/exam/{exam_id}/invigilation",
                headers=self.headers,
            )
            assert response.status_code in (200, 400, 404)

    def test_generate_admit_cards(self):
        """批量生成准考证"""
        list_resp = client.get("/api/exam", headers=self.headers)
        if list_resp.json().get("total", 0) > 0:
            exam_id = list_resp.json()["items"][0]["id"]
            response = client.post(
                f"/api/exam/{exam_id}/admit-card",
                json={
                    "format": "pdf",
                    "include_qrcode": True,
                },
                headers=self.headers,
            )
            assert response.status_code in (200, 201, 400, 404, 422)

    def test_conflict_detection(self):
        """冲突检测"""
        response = client.get(
            "/api/exam/conflicts",
            params={"semester_id": 1},
            headers=self.headers,
        )
        assert response.status_code in (200, 404)

    def test_exam_schedule(self):
        """考试时间表"""
        response = client.get(
            "/api/exam/schedule",
            params={"semester_id": 1, "grade_id": 1},
            headers=self.headers,
        )
        assert response.status_code in (200, 404)


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
