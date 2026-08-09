"""契约测试：报表下载（P3-B 中文文件名编码修复）"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app


class TestReportsContract:
    """报表下载契约测试"""

    def setup_method(self):
        self.client = TestClient(create_app())
        r = self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, r.text
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_report_types(self):
        """报表类型列表"""
        r = self.client.get("/api/reports/types", headers=self.headers)
        assert r.status_code == 200, r.text
        assert "report_types" in r.json() or "items" in r.json()

    def test_generate_exam_report(self):
        """生成考试报表（中文文件名编码）"""
        r = self.client.post(
            "/api/reports/generate",
            headers=self.headers,
            json={"report_type": "exam", "exam_id": 1},
        )
        assert r.status_code == 200, r.text[:200]
        cd = r.headers.get("content-disposition", "")
        # RFC 5987 编码（filename*=UTF-8''...）—— 中文文件名不再触发 latin-1 错误
        assert "filename*=" in cd, f"应使用 RFC 5987 编码: {cd}"
        assert len(r.content) > 0

    def test_generate_change_report(self):
        """生成学籍变动报表（学期参数）"""
        r = self.client.post(
            "/api/reports/generate",
            headers=self.headers,
            json={"report_type": "change", "semester_id": 1},
        )
        assert r.status_code == 200, r.text[:200]
        assert len(r.content) > 0

    def test_generate_report_card(self):
        """生成成绩单（word 格式）"""
        r = self.client.post(
            "/api/reports/generate",
            headers=self.headers,
            json={"report_type": "report_card", "format": "word", "exam_id": 1},
        )
        assert r.status_code == 200, r.text[:200]
        assert len(r.content) > 0

    def test_report_missing_param(self):
        """缺参数 → 400"""
        r = self.client.post(
            "/api/reports/generate",
            headers=self.headers,
            json={"report_type": "exam"},  # 缺 exam_id
        )
        assert r.status_code == 400, f"{r.status_code} {r.text[:80]}"

    def test_report_page_renders(self):
        """报表页渲染（report.html 就位后非占位）"""
        r = self.client.get("/page/system/report", headers=self.headers)
        assert r.status_code == 200
        assert "reportManager" in r.text, "报表页应渲染 reportManager 组件（非 index 占位）"


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
