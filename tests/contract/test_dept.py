"""契约测试：部门管理（B5）"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="module")
def client():
    from edu_system.api.main import create_app

    c = TestClient(create_app())
    r = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    c.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    yield c


class TestDept:
    def test_create(self, client):
        r = client.post("/api/dept", headers=client.headers, json={"dept_name": "教务处"})
        assert r.status_code == 201
        assert "id" in r.json()

    def test_create_missing_name(self, client):
        r = client.post("/api/dept", headers=client.headers, json={"dept_name": ""})
        assert r.status_code == 400

    def test_tree(self, client):
        r = client.get("/api/dept", headers=client.headers)
        assert r.status_code == 200
        assert "items" in r.json()
        assert r.json()["total"] >= 1

    def test_update(self, client):
        r = client.post("/api/dept", headers=client.headers, json={"dept_name": "学工处"})
        did = r.json()["id"]
        r = client.put(f"/api/dept/{did}", headers=client.headers, json={"dept_name": "学生处"})
        assert r.status_code == 200

    def test_delete(self, client):
        r = client.post("/api/dept", headers=client.headers, json={"dept_name": "临时部门"})
        did = r.json()["id"]
        r = client.delete(f"/api/dept/{did}", headers=client.headers)
        assert r.status_code == 200

    def test_delete_nonexistent(self, client):
        r = client.delete("/api/dept/99999", headers=client.headers)
        assert r.status_code == 404