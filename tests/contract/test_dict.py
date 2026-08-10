"""契约测试：字典管理（M1）"""

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


class TestDictType:
    def test_create_type(self, client):
        r = client.post(
            "/api/dict/types",
            headers=client.headers,
            json={"dict_type": "test_type", "dict_name": "测试字典"},
        )
        assert r.status_code == 201, r.text[:200]
        assert "id" in r.json()

    def test_duplicate_type(self, client):
        r = client.post(
            "/api/dict/types",
            headers=client.headers,
            json={"dict_type": "test_type"},
        )
        assert r.status_code == 400

    def test_list_types(self, client):
        r = client.get("/api/dict/types", headers=client.headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_update_type(self, client):
        # 创建后更新
        r = client.post(
            "/api/dict/types",
            headers=client.headers,
            json={"dict_type": "upd_type", "dict_name": "原"},
        )
        tid = r.json()["id"]
        r = client.put(
            f"/api/dict/types/{tid}",
            headers=client.headers,
            json={"dict_name": "新", "status": "1"},
        )
        assert r.status_code == 200, r.text[:200]
        assert r.json()["ok"] is True

    def test_delete_type(self, client):
        r = client.post(
            "/api/dict/types",
            headers=client.headers,
            json={"dict_type": "del_type"},
        )
        tid = r.json()["id"]
        r = client.delete(f"/api/dict/types/{tid}", headers=client.headers)
        assert r.status_code == 200


class TestDictData:
    def test_create_data(self, client):
        # 先建类型
        ct = "data_type"
        client.post("/api/dict/types", headers=client.headers, json={"dict_type": ct})
        r = client.post(
            "/api/dict/data",
            headers=client.headers,
            json={"dict_type": ct, "dict_label": "选项A", "dict_value": "a"},
        )
        assert r.status_code == 201, r.text[:200]
        assert "id" in r.json()

    def test_data_by_type(self, client):
        r = client.get("/api/dict/data", headers=client.headers, params={"dict_type": "data_type"})
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_data_of_type_endpoint(self, client):
        """表单下拉端点（仅正常状态）"""
        r = client.get("/api/dict/data/data_type", headers=client.headers)
        assert r.status_code == 200, r.text[:200]
        assert isinstance(r.json(), list)

    def test_update_data(self, client):
        ct = "upd_data"
        client.post("/api/dict/types", headers=client.headers, json={"dict_type": ct})
        r = client.post(
            "/api/dict/data",
            headers=client.headers,
            json={"dict_type": ct, "dict_label": "X", "dict_value": "x"},
        )
        did = r.json()["id"]
        r = client.put(
            f"/api/dict/data/{did}",
            headers=client.headers,
            json={"dict_label": "Y", "status": "1"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_delete_data(self, client):
        ct = "del_data"
        client.post("/api/dict/types", headers=client.headers, json={"dict_type": ct})
        r = client.post(
            "/api/dict/data",
            headers=client.headers,
            json={"dict_type": ct, "dict_label": "Z"},
        )
        did = r.json()["id"]
        r = client.delete(f"/api/dict/data/{did}", headers=client.headers)
        assert r.status_code == 200


class TestParams:
    """参数管理（M1）"""

    def test_list_params(self, client):
        r = client.get("/api/params", headers=client.headers)
        assert r.status_code == 200
        assert "items" in r.json()
        # seed 有 absent_marks
        assert r.json()["total"] >= 1

    def test_create_param(self, client):
        r = client.post(
            "/api/params",
            headers=client.headers,
            json={"key": "test_key", "value": "v1", "description": "测试参数"},
        )
        assert r.status_code == 201, r.text[:200]
        assert r.json()["key"] == "test_key"

    def test_update_param(self, client):
        # 单测试内完整流程（创建→更新），避免依赖 seed 键名
        r = client.post(
            "/api/params",
            headers=client.headers,
            json={"key": "tmp_upd_key", "value": "v1"},
        )
        assert r.status_code == 201
        r = client.put("/api/params/tmp_upd_key", headers=client.headers, json={"value": "v2"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_delete_param(self, client):
        # 创建即删（单测试内完整流程，避免跨测试隔离）
        r = client.post(
            "/api/params",
            headers=client.headers,
            json={"key": "tmp_del_key", "value": "x"},
        )
        assert r.status_code == 201
        r = client.delete("/api/params/tmp_del_key", headers=client.headers)
        assert r.status_code == 200

    def test_create_and_read(self, client):
        # 创建 + 列表可见（单测试内）
        r = client.post(
            "/api/params",
            headers=client.headers,
            json={"key": "tmp_cr_key", "value": "v", "description": "d"},
        )
        assert r.status_code == 201
        r = client.get("/api/params", headers=client.headers)
        keys = [i["key"] for i in r.json()["items"]]
        assert "tmp_cr_key" in keys

    def test_param_not_found(self, client):
        r = client.delete("/api/params/nonexistent_key", headers=client.headers)
        assert r.status_code == 404
