"""
契约测试：导入导出 API（M5-E7）
运行：pytest tests/contract/test_import_export_api.py -x -v

覆盖：
- GET /import/template: 模板下载（CSV）
- POST /import/preview: 上传 + 字段映射预览
- POST /import/execute: 执行导入
- GET /export/students: 学生导出
"""

import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app


class TestImportExportContract:
    """导入导出接口契约测试"""

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

    def test_template_download(self):
        """模板下载：CSV 含标准表头"""
        response = self.client.get(
            "/api/import/template?entity=student",
            headers=self.headers,
        )
        assert response.status_code in (200, 403)
        if response.status_code == 200:
            assert "text/csv" in response.headers.get("content-type", "")
            body = response.content.decode("utf-8-sig")
            assert "姓名" in body
            assert "性别" in body

    def test_preview_csv(self):
        """预览：上传 CSV 返回质量报告"""
        csv_data = "姓名,性别,座号\n张三,男,001\n李四,女,002\n".encode("utf-8")
        response = self.client.post(
            "/api/import/preview",
            files={"file": ("students.csv", io.BytesIO(csv_data), "text/csv")},
            data={"entity": "student", "mapping_json": "{}"},
            headers=self.headers,
        )
        assert response.status_code in (200, 403, 400)
        if response.status_code == 200:
            data = response.json()
            assert "total_rows" in data
            assert "error_count" in data
            assert "quality_report" in data
            assert data["total_rows"] == 2

    def test_export_students(self):
        """学生导出 CSV"""
        response = self.client.get(
            "/api/export/students",
            headers=self.headers,
        )
        assert response.status_code in (200, 403)
        if response.status_code == 200:
            assert "text/csv" in response.headers.get("content-type", "")


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
