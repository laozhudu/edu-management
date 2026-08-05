"""
Web 页面路由契约测试

覆盖：
- GET /login 登录页（未登录可访问，已登录跳首页）
- GET / 首页（未登录 307 → /login，已登录 200）
- GET /api/meta/ui-config（6 域导航配置）
- GET /api/stats/current（当前学期概览统计）
- GET /page/{domain}/{tab} 功能页占位（已登录 200）
"""

import pytest
from fastapi.testclient import TestClient

from edu_system.api.main import create_app

pytestmark = pytest.mark.contract


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(client):
    """管理员登录态"""
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestLoginPage:
    def test_anonymous_login_page_200(self, client):
        r = client.get("/login")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_logged_in_redirects_to_home(self, client, auth_headers):
        r = client.get("/login", headers=auth_headers, follow_redirects=False)
        assert r.status_code == 307
        assert r.headers["location"] == "/"


class TestIndexPage:
    def test_anonymous_redirects_to_login(self, client):
        r = client.get("/", follow_redirects=False)
        assert r.status_code == 307
        assert r.headers["location"] == "/login"

    def test_logged_in_200(self, client, auth_headers):
        r = client.get("/", headers=auth_headers)
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]


class TestUIConfigAPI:
    def test_ui_config_has_6_domains(self, client, auth_headers):
        r = client.get("/api/meta/ui-config", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data["domains"]) == 6
        ids = [d["id"] for d in data["domains"]]
        assert set(ids) >= {"home", "students", "scores", "exams", "teachers", "system"}

    def test_ui_config_has_tabs(self, client, auth_headers):
        r = client.get("/api/meta/ui-config", headers=auth_headers)
        data = r.json()
        for d in data["domains"]:
            assert d.get("tabs"), f"domain {d['id']} 无页签"


class TestCurrentStatsAPI:
    def test_current_stats_200(self, client, auth_headers):
        r = client.get("/api/stats/current", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "students" in data
        assert "classes" in data
        assert "semester_id" in data

    def test_current_stats_requires_auth(self, client):
        r = client.get("/api/stats/current")
        assert r.status_code in (401, 403)


class TestPagePlaceholder:
    @pytest.mark.parametrize(
        "path",
        [
            "/page/students/student_list",
            "/page/scores/score_entry",
            "/page/exams/exam_manage",
            "/page/system/system_config",
        ],
    )
    def test_page_200_when_logged_in(self, client, auth_headers, path):
        r = client.get(path, headers=auth_headers)
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_page_redirects_when_anonymous(self, client):
        r = client.get("/page/students/student_list", follow_redirects=False)
        assert r.status_code == 307
        assert r.headers["location"] == "/login"
