"""契约测试：数据看板聚合统计（第四阶段 D1）"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app


class TestDashboardStatsContract:
    """Dashboard 聚合统计契约测试"""

    def setup_method(self):
        self.client = TestClient(create_app())
        r = self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, r.text
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_dashboard_stats(self):
        """看板聚合统计返回完整结构"""
        r = self.client.get("/api/stats/dashboard", headers=self.headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "kpi" in data
        assert "gender" in data
        assert "score_dist" in data
        assert "class_sizes" in data
        # gender 结构校验
        for g in data["gender"]:
            assert "name" in g and "value" in g
        # score_dist 5 段
        assert len(data["score_dist"]) == 5
        # kpi 关键字段
        assert "student_count" in data["kpi"]
        assert "class_count" in data["kpi"]

    def test_dashboard_kpi_counts(self):
        """KPI 计数非负且合理"""
        r = self.client.get("/api/stats/dashboard", headers=self.headers)
        assert r.status_code == 200
        kpi = r.json()["kpi"]
        for v in kpi.values():
            assert v >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
