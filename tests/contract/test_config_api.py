"""
UI 配置 API 契约测试（M2-3）

/api/config 只读端点：暴露 ui_config（品牌/学校/版本/6 域导航/页签/主题/状态栏），
供未来 Web 前端消费。双端共享同一配置源。
运行：pytest tests/contract/test_config_api.py -x -v
"""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app

# 配置源（ui_config.json）——断言与配置源一致，不硬编码版本/校名，防升级后契约失效
_SRC_CFG = json.loads(
    (project_root / "src/edu_system/config/ui_config.json").read_text(encoding="utf-8")
)


@pytest.fixture()
def client():
    app = create_app()
    return TestClient(app)


class TestUIConfigAPI:
    """UI 配置只读端点契约"""

    def test_get_config_returns_brand_and_domains(self, client):
        """返回学校名称/版本（与配置源一致）+ 6 域导航结构（按 order 升序）"""
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        # 品牌/版本：与 ui_config.json 配置源一致
        assert data["app"]["school_name"] == _SRC_CFG["app"]["school_name"]
        assert data["app"]["version"] == _SRC_CFG["app"]["version"]
        # 8 域导航（home/students/scores/exams/teachers/classes/classrooms/system）
        assert len(data["domains"]) == 9
        domain_ids = [d["id"] for d in data["domains"]]
        assert domain_ids == [
            "home",
            "students",
            "teachers",
            "classes",
            "classrooms",
            "exams",
            "scores",
            "tools",
            "system",
        ]
        # 按 order 升序排列
        orders = [d["order"] for d in data["domains"]]
        assert orders == sorted(orders)

    def test_get_config_structure_complete(self, client):
        """每个域含 tabs（id/title/view 齐全），主题/顶栏/状态栏结构完整"""
        data = client.get("/api/config").json()
        # 域与页签结构
        for d in data["domains"]:
            assert d["tabs"], f"域 {d['id']} 无页签"
            for t in d["tabs"]:
                assert t["id"] and t["title"] and t["view"], f"页签结构不完整: {t}"
        # 主题令牌
        assert data["theme"]["accent_color"]
        assert data["theme"]["sidebar_bg"]
        # 顶栏（快捷键等）
        assert "shortcuts" in data["topbar"]
        # 状态栏
        assert "left" in data["statusbar"] and "right" in data["statusbar"]


class TestConfigHotReload:
    """G4 配置热加载：version 指纹 + reload"""

    def test_version_endpoint_public(self, client):
        """GET /api/config/version 公开（无需登录），返回指纹"""
        resp = client.get("/api/config/version")
        assert resp.status_code == 200
        data = resp.json()
        assert "fingerprint" in data
        assert data["fingerprint"]

    def test_version_fingerprint_stable(self, client):
        """同一配置文件指纹稳定（两次一致）"""
        f1 = client.get("/api/config/version").json()["fingerprint"]
        f2 = client.get("/api/config/version").json()["fingerprint"]
        assert f1 == f2

    def test_reload_requires_auth(self, client):
        """POST /api/config/reload 需登录"""
        resp = client.post("/api/config/reload")
        assert resp.status_code in (401, 403)

    def test_reload_success(self, client):
        """登录后 reload 返回新指纹 + 学校名"""
        login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        resp = client.post("/api/config/reload", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "fingerprint" in data
        assert "school" in data
