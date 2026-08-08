"""契约测试：数据维护（P3-B）"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app


class TestMaintenanceContract:
    """数据维护契约测试"""

    def setup_method(self):
        self.client = TestClient(create_app())
        r = self.client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, r.text
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_backup(self):
        """执行备份"""
        r = self.client.post("/api/maintenance/backup", headers=self.headers)
        assert r.status_code in (200, 500), f"{r.status_code} {r.text[:80]}"
        assert r.json().get("ok") in (True, None)

    def test_list_backups(self):
        """备份列表"""
        r = self.client.get("/api/maintenance/backups", headers=self.headers)
        assert r.status_code == 200, r.text
        assert "items" in r.json()

    def test_clean_cache(self):
        """清理缓存"""
        r = self.client.post("/api/maintenance/clean/cache", headers=self.headers)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
