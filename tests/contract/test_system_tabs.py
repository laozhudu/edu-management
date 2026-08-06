"""
系统域 6 个新页签契约测试

覆盖（system 域，view 字段指向各模板）：
- /page/system/semester        → semester.html        （学期设置）
- /page/system/classes         → class_list.html      （班级科目）
- /page/system/classrooms      → classroom_list.html  （教室位置）
- /page/system/users           → users.html           （用户权限）
- /page/system/data_maintenance→ data_maintenance.html（数据维护）
- /page/system/init            → init.html            （初始化系统）
- 各页依赖的后端 API 契约（学期/用户/缓存/健康检查）
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


class TestSystemTabs:
    """6 个新页签：渲染正确模板、含 Alpine 组件与数据源调用"""

    @pytest.mark.parametrize(
        "path,component,fetch_marker",
        [
            ("/page/system/semester", "semesterManage", "/api/semester/list"),
            ("/page/system/classes", "classList", "/api/students"),
            ("/page/system/classrooms", "classroomList", "/api/meta/ui-config"),
            ("/page/system/users", "userPermission", "/api/auth/me"),
            ("/page/system/data_maintenance", "dataMaintenance", "/api/stats/cache/stats"),
            ("/page/system/init", "systemInit", "此操作将清空所有业务数据"),
        ],
    )
    def test_tab_renders_specific_template(self, client, auth_headers, path, component, fetch_marker):
        r = client.get(path, headers=auth_headers)
        assert r.status_code == 200
        assert component in r.text, f"{path} 未渲染 {component} 组件"
        assert fetch_marker in r.text, f"{path} 缺少数据源调用 {fetch_marker}"

    def test_tab_redirects_when_anonymous(self, client):
        r = client.get("/page/system/semester", follow_redirects=False)
        assert r.status_code == 307
        assert r.headers["location"] == "/login"


class TestTabBackingApis:
    """新页签依赖的后端 API 契约"""

    def test_semester_list(self, client, auth_headers):
        r = client.get("/api/semester/list", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and "total" in data

    def test_semester_active(self, client, auth_headers):
        r = client.get("/api/semester/active", headers=auth_headers)
        assert r.status_code == 200
        assert "semester" in r.json()

    def test_auth_me(self, client, auth_headers):
        r = client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        for key in ("id", "username", "display_name", "role", "permissions"):
            assert key in data

    def test_cache_stats(self, client, auth_headers):
        r = client.get("/api/stats/cache/stats", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        for key in ("version", "entry_count", "size_bytes", "directory"):
            assert key in data

    def test_healthz(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert "version" in data and "cache_version" in data
