"""契约测试：图书管理（A2 演示业务域，验证底座复用）"""
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


class TestBookCRUD:
    def test_create(self, client):
        r = client.post(
            "/api/books", headers=client.headers,
            json={"title": "三体", "author": "刘慈欣", "total_copies": 3},
        )
        assert r.status_code == 201
        assert "id" in r.json()

    def test_create_missing_title(self, client):
        r = client.post("/api/books", headers=client.headers, json={"title": ""})
        assert r.status_code == 400

    def test_list(self, client):
        r = client.get("/api/books", headers=client.headers)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_update(self, client):
        r = client.post("/api/books", headers=client.headers, json={"title": "朝闻道"})
        bid = r.json()["id"]
        r = client.put(f"/api/books/{bid}", headers=client.headers, json={"author": "刘慈欣"})
        assert r.status_code == 200

    def test_delete(self, client):
        r = client.post("/api/books", headers=client.headers, json={"title": "临时书"})
        bid = r.json()["id"]
        r = client.delete(f"/api/books/{bid}", headers=client.headers)
        assert r.status_code == 200

    def test_delete_nonexistent(self, client):
        r = client.delete("/api/books/99999", headers=client.headers)
        assert r.status_code == 404


class TestBorrow:
    def test_borrow_return(self, client):
        r = client.post("/api/books", headers=client.headers, json={"title": "球状闪电", "total_copies": 2})
        bid = r.json()["id"]
        r = client.post(f"/api/books/{bid}/borrow", headers=client.headers, json={"borrower_name": "张三", "days": 30})
        assert r.status_code == 200
        r = client.get("/api/books", headers=client.headers)
        assert r.json()["items"][0]["available_copies"] == 1
        r = client.post(f"/api/books/{bid}/return", headers=client.headers)
        assert r.status_code == 200

    def test_borrow_no_stock(self, client):
        r = client.post("/api/books", headers=client.headers, json={"title": "单本", "total_copies": 1})
        bid = r.json()["id"]
        r = client.post(f"/api/books/{bid}/borrow", headers=client.headers, json={"borrower_name": "李四"})
        assert r.status_code == 200
        r = client.post(f"/api/books/{bid}/borrow", headers=client.headers, json={"borrower_name": "王五"})
        assert r.status_code == 400  # 无可借册数

    def test_borrow_records(self, client):
        r = client.get("/api/borrow-records", headers=client.headers)
        assert r.status_code == 200
        assert "items" in r.json()


class TestAuditIntegration:
    def test_book_operation_audited(self, client):
        """验证业务域操作被底座审计记录"""
        before = client.get("/api/audit/operations", headers=client.headers).json()["total"]
        r = client.post("/api/books", headers=client.headers, json={"title": "审计验证书"})
        bid = r.json()["id"]
        after = client.get("/api/audit/operations", headers=client.headers).json()["total"]
        assert after >= before + 1
