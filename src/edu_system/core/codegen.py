"""
core/codegen — 轻量代码生成器（B5：对齐若依 generator）

输入 model 类 → 生成：
  1. api/routes/{name}.py    （CRUD 路由 + PageQuery 分页 + 统一返回）
  2. tests/contract/test_{name}.py（契约测试）
  3. 注册提示（main.py include_router + service_registry 服务码）

用法（CLI）：python scripts/codegen.py Student --fields ...
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FieldSpec:
    name: str
    col_type: str = "String"  # String/Integer/Float/Date/Text/Boolean
    label: str = ""
    required: bool = False
    searchable: bool = False


@dataclass
class CodegenConfig:
    """生成配置（对齐若依 gen_table）"""

    model_name: str  # Student
    table_name: str  # students
    module_name: str  # student（路由文件名/URL 前缀）
    business_name: str  # 业务中文名（学生）
    function_name: str  # 功能名（学生管理）
    fields: list[FieldSpec] = field(default_factory=list)
    tpl_category: str = "crud"  # crud / tree
    author: str = "codegen"
    datetime: str = ""

    def class_name(self) -> str:
        return self.model_name

    def var_name(self) -> str:
        return self.model_name[0].lower() + self.model_name[1:]


ROUTE_TEMPLATE = '''"""{function_name} API（{module_name}）— 由 codegen 生成
模板: core/codegen.py（对齐若依 generator 的 Controller/Service 范式）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import PageQuery, get_db, paginate_response, require_permission
from edu_system.core.permissions import Permission
from edu_system.models import {model_name}

router = APIRouter(tags=["{business_name}"])


class {model_name}Create(BaseModel):
{create_fields}


class {model_name}Update(BaseModel):
{update_fields}


def _to_dict(o: {model_name}) -> dict:
    return {{
        "id": o.id,
{to_dict_fields}
    }}


@router.get("/{module_name}")
def {module_name}_list(
    query: PageQuery = Depends(),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_VIEW)),
):
    q = db.query({model_name})
{search_filters}
    total = q.count()
    items = q.order_by({model_name}.id.desc()).offset(query.offset).limit(query.page_size).all()
    return paginate_response([_to_dict(o) for o in items], total, query.page, query.page_size)


@router.post("/{module_name}", status_code=201)
def {module_name}_create(
    body: {model_name}Create,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    o = {model_name}(
{create_assign}
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return {{"id": o.id}}


@router.put("/{module_name}/{{{{obj_id}}}}")
def {module_name}_update(
    obj_id: int,
    body: {model_name}Update,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    o = db.get({model_name}, obj_id)
    if not o:
        raise HTTPException(status_code=404, detail="{business_name}不存在")
{update_assign}
    db.commit()
    return {{"ok": True}}


@router.delete("/{module_name}/{{{{obj_id}}}}")
def {module_name}_delete(
    obj_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    o = db.get({model_name}, obj_id)
    if not o:
        raise HTTPException(status_code=404, detail="{business_name}不存在")
    db.delete(o)
    db.commit()
    return {{"ok": True}}
'''

TEST_TEMPLATE = '''"""契约测试：{business_name}（{module_name}）— 由 codegen 生成"""
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
    r = c.post("/api/auth/login", json={{"username": "admin", "password": "admin123"}})
    assert r.status_code == 200, r.text
    c.headers = {{"Authorization": f"Bearer {{r.json()['access_token']}}"}}
    yield c


class Test{model_name}CRUD:
    def test_create(self, client):
        r = client.post("/api/{module_name}", headers=client.headers, json={{test_create_json}})
        assert r.status_code == 201, r.text[:200]
        assert "id" in r.json()

    def test_list(self, client):
        r = client.get("/api/{module_name}", headers=client.headers)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_update(self, client):
        r = client.post("/api/{module_name}", headers=client.headers, json={{test_create_json}})
        oid = r.json()["id"]
        r = client.put(f"/api/{module_name}/{{oid}}", headers=client.headers, json={{test_update_json}})
        assert r.status_code == 200

    def test_delete(self, client):
        r = client.post("/api/{module_name}", headers=client.headers, json={{test_create_json}})
        oid = r.json()["id"]
        r = client.delete(f"/api/{module_name}/{{oid}}", headers=client.headers)
        assert r.status_code == 200
'''

REGISTER_HINT = """# 注册提示（生成后手动执行）：
# 1. api/main.py:  from edu_system.api.routes import {module_name}  +  app.include_router({module_name}.router, prefix="/api")
# 2. api/service_registry.py: DEFAULT_SERVICES 加 "{module_name}" 服务码（api_prefix="/api/{module_name}"）
# 3. 桌面 registry.py:  "{module_name}": ("edu_system.gui.views.{module_name}", "{model_name}View", ["session"])
# 4. ui_config.json: 加页签 {{"id": "{module_name}", "title": "{business_name}", "view": "{module_name}"}}
"""


def _py_type(col_type: str) -> str:
    return {
        "String": "str",
        "Integer": "int",
        "Float": "float",
        "Boolean": "bool",
        "Text": "str",
    }.get(col_type, "str")


def generate(cfg: CodegenConfig) -> dict[str, str]:
    """生成全部文件内容，返回 {文件路径: 内容}"""
    create_fields = (
        "\n".join(
            f"    {f.name}: {_py_type(f.col_type)} = ..."
            if f.required
            else f"    {f.name}: {_py_type(f.col_type)} | None = None"
            for f in cfg.fields
        )
        or "    pass  # noqa: E701"
    )
    update_fields = (
        "\n".join(f"    {f.name}: {_py_type(f.col_type)} | None = None" for f in cfg.fields)
        or "    pass  # noqa: E701"
    )
    to_dict_fields = "\n".join(f'        "{f.name}": o.{f.name},' for f in cfg.fields)
    create_assign = "\n".join(f"        {f.name}=body.{f.name}," for f in cfg.fields)
    update_assign = "\n".join(
        f"    if body.{f.name} is not None:\n        o.{f.name} = body.{f.name}" for f in cfg.fields
    )
    search_filters = ""
    for f in cfg.fields:
        if f.searchable:
            search_filters += (
                f"    kw = query.order_by\n"
                f'    if kw and hasattr(query, "keyword") and query.keyword:\n'
                f"        q = q.filter({cfg.model_name}.{f.name}.contains(query.keyword))\n"
            )

    # 简化：search 用单独的 keyword 参数更干净
    search_filters = ""
    searchable = [f for f in cfg.fields if f.searchable]
    if searchable:
        search_filters = "    keyword = None\n    # 如需搜索: 加 keyword 查询参数\n"

    route = ROUTE_TEMPLATE.format(
        function_name=cfg.function_name,
        module_name=cfg.module_name,
        business_name=cfg.business_name,
        model_name=cfg.model_name,
        create_fields=create_fields,
        update_fields=update_fields,
        to_dict_fields=to_dict_fields,
        create_assign=create_assign,
        update_assign=update_assign,
        search_filters=search_filters,
    )

    test_create_json = ", ".join(
        f'"{f.name}": "示例"' if f.col_type == "String" else f'"{f.name}": 1'
        for f in cfg.fields[:3]
    )
    test_update_json = ", ".join(
        f'"{f.name}": "更新"' if f.col_type == "String" else f'"{f.name}": 2'
        for f in cfg.fields[:2]
    )
    test = TEST_TEMPLATE.format(
        business_name=cfg.business_name,
        module_name=cfg.module_name,
        model_name=cfg.model_name,
        test_create_json="{" + test_create_json + "}",
        test_update_json="{" + test_update_json + "}",
    )

    return {
        f"src/edu_system/api/routes/{cfg.module_name}.py": route,
        f"tests/contract/test_{cfg.module_name}.py": test,
        "REGISTER_HINT": REGISTER_HINT.format(
            module_name=cfg.module_name, business_name=cfg.business_name, model_name=cfg.model_name
        ),
    }
