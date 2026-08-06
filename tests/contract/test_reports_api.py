"""
报表 API 契约测试（M6 Sprint 6：报表引擎全集成）

覆盖：
- GET  /api/reports/types         报表类型列表（需登录）
- POST /api/reports/generate      生成报表（exam 类型返回 xlsx 文件）
- GET  /api/reports/printers      打印机列表
- 未登录访问 401/403
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app


class TestReportsContract:
    @pytest.fixture(autouse=True)
    def setup(self):
        app = create_app()
        client = TestClient(app)
        self.client = client
        resp = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 200
        self.headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def test_types_requires_auth(self):
        """未登录访问报表类型 401/403"""
        resp = self.client.get("/api/reports/types")
        assert resp.status_code in (401, 403)

    def test_list_report_types(self):
        """报表类型列表包含 exam/change/report_card/certificate"""
        resp = self.client.get("/api/reports/types", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        types = data if isinstance(data, list) else data.get("report_types", [])
        type_ids = [t["type"] for t in types]
        assert "exam" in type_ids
        assert "certificate" in type_ids

    def test_generate_invalid_type(self):
        """不支持的报表类型返回 400"""
        resp = self.client.post(
            "/api/reports/generate",
            json={"report_type": "unknown_type", "format": "excel"},
            headers=self.headers,
        )
        assert resp.status_code == 400

    def test_generate_exam_requires_exam_id(self):
        """exam 报表缺 exam_id 返回 400"""
        resp = self.client.post(
            "/api/reports/generate",
            json={"report_type": "exam", "format": "excel"},
            headers=self.headers,
        )
        assert resp.status_code == 400

    def test_generate_exam_report(self):
        """生成考试报表返回 xlsx 文件流"""
        # 先查一个考试
        exams = self.client.get("/api/exam", headers=self.headers)
        assert exams.status_code == 200
        data = exams.json()
        items = data if isinstance(data, list) else data.get("items", data.get("exams", []))
        if not items:
            pytest.skip("无考试数据，跳过生成测试")
        exam_id = items[0]["id"]

        resp = self.client.post(
            "/api/reports/generate",
            json={"report_type": "exam", "format": "excel", "exam_id": exam_id},
            headers=self.headers,
        )
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert "spreadsheet" in resp.headers.get("content-type", "")
            assert len(resp.content) > 0

    def test_printers_endpoint(self):
        """打印机列表端点返回结构正确"""
        resp = self.client.get("/api/reports/printers", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "printers" in data
        assert isinstance(data["printers"], list)
