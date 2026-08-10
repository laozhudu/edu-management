"""契约测试：样式配置保存 + 审计操作日志（v3.7.0）"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    c = TestClient(create_app())
    r = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    c.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    yield c


@pytest.fixture(scope="module", autouse=True)
def _restore_config():
    """备份并恢复 ui_config.json（save-ui 测试会写回真实文件，防止污染其他测试）"""
    from edu_system.config.ui_config import _DEFAULT_CONFIG_PATH

    p = Path(_DEFAULT_CONFIG_PATH)
    backup = p.read_text(encoding="utf-8")
    yield
    p.write_text(backup, encoding="utf-8")
    try:
        from edu_system.config.ui_config import reload_config

        reload_config()
    except Exception:
        pass


class TestSaveUI:
    """界面样式配置保存"""

    def test_save_theme(self, client):
        """保存 theme 节 → 写回 + reload 生效"""
        r = client.post(
            "/api/config/save-ui",
            headers=client.headers,
            json={"theme": {"accent_color": "#1E90FF", "density": "comfortable"}},
        )
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert data["success"] is True
        assert "fingerprint" in data

    def test_save_login(self, client):
        """保存 login 节（登录框样式）"""
        r = client.post(
            "/api/config/save-ui",
            headers=client.headers,
            json={"login": {"window_width": 440, "brand_title_font_size": 18}},
        )
        assert r.status_code == 200, r.text[:200]
        assert r.json()["success"] is True

    def test_save_invalid(self, client):
        """非法结构 → 500 或校验失败"""
        r = client.post(
            "/api/config/save-ui",
            headers=client.headers,
            json={"theme": "not-a-dict"},
        )
        assert r.status_code in (422, 500)

    def test_config_reflects_saved(self, client):
        """保存后 GET config 反映新值（theme/topbar 在 API 返回中；login 写回文件）"""
        r = client.get("/api/config", headers=client.headers)
        assert r.status_code == 200
        theme = r.json().get("theme", {})
        assert theme.get("accent_color") == "#1E90FF"
        assert theme.get("density") == "comfortable"
        # login 节不在 GET /api/config 返回中（桌面专用），从配置文件验证写回
        import json

        from edu_system.config.ui_config import _DEFAULT_CONFIG_PATH

        raw = json.loads(Path(_DEFAULT_CONFIG_PATH).read_text(encoding="utf-8"))
        assert raw.get("login", {}).get("window_width") == 440
        assert raw.get("login", {}).get("brand_title_font_size") == 18


class TestAuditOperations:
    """业务操作审计日志查询"""

    def test_operations_list(self, client):
        """操作审计列表（至少返回结构正确）"""
        r = client.get("/api/audit/operations", headers=client.headers)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        # query_audit_logs 返回 items/total 结构
        assert "items" in data or "logs" in data or "total" in data

    def test_operations_filter_table(self, client):
        """按表过滤"""
        r = client.get(
            "/api/audit/operations", headers=client.headers, params={"table_name": "students"}
        )
        assert r.status_code == 200, r.text[:200]

    def test_operations_page(self, client):
        """分页参数"""
        r = client.get(
            "/api/audit/operations",
            headers=client.headers,
            params={"page": 1, "page_size": 20},
        )
        assert r.status_code == 200, r.text[:200]
