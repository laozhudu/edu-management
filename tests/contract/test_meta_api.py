"""
字段元数据 API 契约测试（Sprint 3.7.8）
运行：pytest tests/contract/test_meta_api.py -x -v
"""

import sys
import time as _time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app

# 每次运行唯一后缀，避免跨运行字段残留冲突（契约测试共享持久化测试库）
_UNIQ = f"_{int(_time.time() * 1000) % 100000}"


@pytest.fixture()
def client():
    app = create_app()
    c = TestClient(app)
    resp = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    c.headers.update({"Authorization": f"Bearer {token}"})
    yield c


class TestFieldCRUD:
    """字段定义增删改查契约"""

    def test_list_fields_empty(self, client):
        """查询实体字段列表"""
        resp = client.get("/api/meta/fields", params={"entity_type": "student"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 0

    def test_create_field(self, client):
        """新增自定义字段成功"""
        resp = client.post(
            "/api/meta/fields",
            json={
                "entity_type": "student",
                "field_key": f"hobby_cr{_UNIQ}",
                "label": "兴趣爱好",
                "field_type": "string",
                "required": False,
                "sort_order": 10,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["field_key"] == f"hobby_cr{_UNIQ}"
        assert data["label"] == "兴趣爱好"
        assert data["is_system"] is False

    def test_create_field_duplicate(self, client):
        """重复字段键被拒绝（400）"""
        payload = {
            "entity_type": "student",
            "field_key": f"hobby2{_UNIQ}",
            "label": "重复测试",
            "field_type": "string",
        }
        assert client.post("/api/meta/fields", json=payload).status_code == 201
        resp = client.post("/api/meta/fields", json=payload)
        assert resp.status_code == 400
        assert "已存在" in resp.json()["detail"]

    def test_create_field_invalid_type(self, client):
        """非法字段类型被拒绝（400）"""
        resp = client.post(
            "/api/meta/fields",
            json={
                "entity_type": "student",
                "field_key": f"bad_type{_UNIQ}",
                "label": "坏类型",
                "field_type": "blob",
            },
        )
        assert resp.status_code == 400

    def test_create_field_enum_requires_options(self, client):
        """enum/select 字段必须提供 options（400）"""
        resp = client.post(
            "/api/meta/fields",
            json={
                "entity_type": "student",
                "field_key": f"bad_enum{_UNIQ}",
                "label": "坏枚举",
                "field_type": "enum",
            },
        )
        assert resp.status_code == 400

    def test_get_field(self, client):
        """查询单个字段定义"""
        client.post(
            "/api/meta/fields",
            json={
                "entity_type": "teacher",
                "field_key": f"cert_no{_UNIQ}",
                "label": "资格证号",
                "field_type": "string",
            },
        )
        resp = client.get(f"/api/meta/fields/teacher/cert_no{_UNIQ}")
        assert resp.status_code == 200
        assert resp.json()["label"] == "资格证号"

    def test_get_field_not_found(self, client):
        """不存在的字段返回 404"""
        resp = client.get("/api/meta/fields/student/nonexistent_key")
        assert resp.status_code == 404

    def test_update_field(self, client):
        """修改字段定义（label/required）"""
        client.post(
            "/api/meta/fields",
            json={
                "entity_type": "exam",
                "field_key": f"invigilator_note{_UNIQ}",
                "label": "监考备注",
                "field_type": "string",
            },
        )
        resp = client.put(
            f"/api/meta/fields/exam/invigilator_note{_UNIQ}",
            json={"label": "监考说明", "required": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["label"] == "监考说明"
        assert data["required"] is True

    def test_delete_field(self, client):
        """删除自定义字段成功（204）"""
        client.post(
            "/api/meta/fields",
            json={
                "entity_type": "class",
                "field_key": f"temp_note{_UNIQ}",
                "label": "临时备注",
                "field_type": "string",
            },
        )
        resp = client.delete(f"/api/meta/fields/class/temp_note{_UNIQ}")
        assert resp.status_code == 204
        # 再查应 404
        assert client.get(f"/api/meta/fields/class/temp_note{_UNIQ}").status_code == 404

    def test_delete_field_not_found(self, client):
        """删除不存在的字段返回 404"""
        resp = client.delete("/api/meta/fields/class/ghost_key")
        assert resp.status_code == 404


class TestEntityValues:
    """实体 ext_json 批量写入契约"""

    def test_set_entity_values(self, client):
        """批量写入自定义字段值"""
        # 先注册字段
        client.post(
            "/api/meta/fields",
            json={
                "entity_type": "student",
                "field_key": f"hobby{_UNIQ}",
                "label": "兴趣爱好",
                "field_type": "string",
            },
        )
        # 需要真实 student 记录（测试库有 test_data 学生）
        resp = client.post(
            "/api/meta/fields/student/1/values",
            json={"values": {f"hobby{_UNIQ}": "篮球"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["values"][f"hobby{_UNIQ}"] == "篮球"

    def test_set_entity_values_invalid_option(self, client):
        """enum 字段写入非法选项被拒绝（400）"""
        client.post(
            "/api/meta/fields",
            json={
                "entity_type": "teacher",
                "field_key": f"title_level{_UNIQ}",
                "label": "职称级别",
                "field_type": "enum",
                "options": ["初级", "中级", "高级"],
            },
        )
        resp = client.post(
            "/api/meta/fields/teacher/1/values",
            json={"values": {f"title_level{_UNIQ}": "超级"}},
        )
        assert resp.status_code == 400

    def test_set_entity_values_entity_not_found(self, client):
        """不存在的实体返回 400"""
        resp = client.post(
            "/api/meta/fields/student/99999/values",
            json={"values": {}},
        )
        assert resp.status_code == 400
