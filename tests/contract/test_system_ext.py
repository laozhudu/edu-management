"""契约测试：通知公告 + 登录日志 + 在线用户（M2）"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="module")
def client():


    pass  # 依赖 conftest session 级初始化（隔离）
    c = TestClient(__import__("edu_system.api.main", fromlist=["create_app"]).create_app())
    r = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    c.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    yield c


class TestNotice:
    def test_create(self, client):
        r = client.post(
            "/api/notice",
            headers=client.headers,
            json={"title": "考试通知", "content": "期中考试安排", "notice_type": "notice"},
        )
        assert r.status_code == 201, r.text[:200]
        assert "id" in r.json()

    def test_list(self, client):
        r = client.get("/api/notice", headers=client.headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_missing_title(self, client):
        r = client.post("/api/notice", headers=client.headers, json={"title": ""})
        assert r.status_code == 400

    def test_mark_read(self, client):
        r = client.post("/api/notice", headers=client.headers, json={"title": "待读公告"})
        nid = r.json()["id"]
        r = client.post(f"/api/notice/{nid}/read", headers=client.headers)
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_update_delete(self, client):
        r = client.post("/api/notice", headers=client.headers, json={"title": "临时公告"})
        nid = r.json()["id"]
        r = client.put(f"/api/notice/{nid}", headers=client.headers, json={"status": "2"})
        assert r.status_code == 200
        r = client.delete(f"/api/notice/{nid}", headers=client.headers)
        assert r.status_code == 200


class TestLoginLog:
    def test_login_logs_written(self, client):
        """登录后应有日志（成功/失败）"""
        r = client.get("/api/login-logs", headers=client.headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_login_logs_paged(self, client):
        r = client.get(
            "/api/login-logs", headers=client.headers, params={"page": 1, "page_size": 10}
        )
        assert r.status_code == 200
        assert "items" in r.json()


class TestOnlineUser:
    def test_online_list(self, client):
        r = client.get("/api/online-users", headers=client.headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_kick_nonexistent(self, client):
        r = client.post("/api/online-users/99999/kick", headers=client.headers)
        assert r.status_code == 404
