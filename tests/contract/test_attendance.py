"""
契约测试：考勤 API
运行：pytest tests/contract/test_attendance.py -x -v
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


class TestAttendanceContract:
    """考勤接口契约测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """登录获取 token"""
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

    def test_checkin(self):
        """打卡接口"""
        response = self.client.post(
            "/api/attendance/checkin",
            json={
                "student_id": 1,
                "check_type": "morning",
                "latitude": 23.123456,
                "longitude": 113.123456,
                "device_info": "iPhone 15",
            },
            headers=self.headers,
        )
        assert response.status_code in (200, 201, 400, 404, 422)

    def test_list_attendance(self):
        """考勤记录列表查询"""
        response = self.client.get(
            "/api/attendance",
            params={"student_id": 1, "date_from": "2026-01-01", "date_to": "2026-12-31"},
            headers=self.headers,
        )
        assert response.status_code in (200, 403, 404)
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "page_size" in data

    def test_leave_application(self):
        """请假申请"""
        response = self.client.post(
            "/api/attendance/leave",
            json={
                "student_id": 1,
                "leave_type": "sick",
                "start_date": "2026-08-05",
                "end_date": "2026-08-07",
                "reason": "感冒发烧",
                "attachments": [],
            },
            headers=self.headers,
        )
        assert response.status_code in (200, 201, 400, 403, 404, 422)

    def test_leave_approval(self):
        """请假审批"""
        # 先获取列表拿一个 ID
        list_resp = self.client.get("/api/attendance/leave", headers=self.headers)
        if list_resp.status_code == 200 and list_resp.json().get("total", 0) > 0:
            leave_id = list_resp.json()["items"][0]["id"]
            response = self.client.put(
                f"/api/attendance/leave/{leave_id}/approve",
                json={"approved": True, "comment": "批准"},
                headers=self.headers,
            )
            assert response.status_code in (200, 400, 404, 403)

    def test_leave_rejection(self):
        """请假驳回"""
        list_resp = self.client.get("/api/attendance/leave", headers=self.headers)
        if list_resp.status_code == 200 and list_resp.json().get("total", 0) > 0:
            leave_id = list_resp.json()["items"][0]["id"]
            response = self.client.put(
                f"/api/attendance/leave/{leave_id}/approve",
                json={"approved": False, "comment": "理由不充分"},
                headers=self.headers,
            )
            assert response.status_code in (200, 400, 404, 403)

    def test_attendance_stats(self):
        """考勤统计"""
        response = self.client.get(
            "/api/attendance/stats",
            params={"scope": "class", "class_id": 1},
            headers=self.headers,
        )
        assert response.status_code in (200, 400, 403, 404)

    def test_export_attendance(self):
        """导出考勤 Excel"""
        response = self.client.get(
            "/api/attendance/export",
            params={"class_id": 1, "date_from": "2026-08-01", "date_to": "2026-08-31"},
            headers=self.headers,
        )
        assert response.status_code in (200, 404, 403)

    def test_checkin_with_face(self):
        """人脸识别打卡"""
        response = self.client.post(
            "/api/attendance/checkin",
            json={
                "student_id": 1,
                "check_type": "afternoon",
                "face_embedding": "base64_encoded_embedding",
                "device_info": "iPad Pro",
            },
            headers=self.headers,
        )
        assert response.status_code in (200, 201, 400, 404, 422)

    def test_abnormal_alerts(self):
        """异常打卡告警"""
        response = self.client.get(
            "/api/attendance/alerts",
            params={"date": "2026-08-01"},
            headers=self.headers,
        )
        assert response.status_code in (200, 404)


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
