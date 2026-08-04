"""
字段元数据 API 路由

动态字段增删查（Sprint 3.7.8）
- FieldDefinition 注册表 CRUD
- 实体 ext_json 自定义字段读写
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_db, require_permission
from edu_system.core.permissions import Permission
from edu_system.models import FieldDefinition
from edu_system.services.meta import FieldService, FieldValidationError

router = APIRouter(prefix="/meta/fields", tags=["字段元数据"])


# ===== Pydantic 模型 =====


class FieldCreate(BaseModel):
    entity_type: str
    field_key: str
    label: str
    field_type: str = "string"
    options: list | None = None
    required: bool = False
    sort_order: int = 0


class FieldUpdate(BaseModel):
    label: str | None = None
    field_type: str | None = None
    options: list | None = None
    required: bool | None = None
    sort_order: int | None = None


class FieldResponse(BaseModel):
    id: int
    entity_type: str
    field_key: str
    label: str
    field_type: str
    options: list | None = None
    required: bool
    sort_order: int
    is_system: bool
    created_by: str | None = None


class FieldListResponse(BaseModel):
    items: list[FieldResponse]
    total: int


class EntityValueResponse(BaseModel):
    entity_id: int
    entity_type: str
    values: dict[str, Any]


class EntityValues(BaseModel):
    values: dict[str, Any]


def _to_response(fd: FieldDefinition) -> FieldResponse:
    import json

    opts = None
    if fd.options:
        try:
            opts = json.loads(fd.options)
        except (ValueError, TypeError):
            opts = None
    return FieldResponse(
        id=fd.id,
        entity_type=fd.entity_type,
        field_key=fd.field_key,
        label=fd.label,
        field_type=fd.field_type,
        options=opts,
        required=fd.required,
        sort_order=fd.sort_order,
        is_system=fd.is_system,
        created_by=fd.created_by,
    )


def _handle_field_error(e: FieldValidationError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ===== 字段定义 CRUD =====


@router.get("", response_model=FieldListResponse)
def list_fields(
    entity_type: str = Query(..., description="实体类型：student/teacher/class/exam/score"),
    db: Session = Depends(get_db),
    _: Any = Depends(require_permission(Permission.CONFIG_VIEW)),
):
    """查询某实体的全部字段定义"""
    svc = FieldService(db)
    try:
        items = svc.list_fields(entity_type)
    except FieldValidationError as e:
        raise _handle_field_error(e)
    return FieldListResponse(items=[_to_response(f) for f in items], total=len(items))


@router.get("/{entity_type}/{field_key}", response_model=FieldResponse)
def get_field(
    entity_type: str,
    field_key: str,
    db: Session = Depends(get_db),
    _: Any = Depends(require_permission(Permission.CONFIG_VIEW)),
):
    """查询单个字段定义"""
    fd = FieldService(db).get_field(entity_type, field_key)
    if not fd:
        raise HTTPException(status_code=404, detail=f"字段不存在: {entity_type}.{field_key}")
    return _to_response(fd)


@router.post("", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
def create_field(
    body: FieldCreate,
    db: Session = Depends(get_db),
    _: Any = Depends(require_permission(Permission.CONFIG_EDIT)),
):
    """新增自定义字段"""
    svc = FieldService(db)
    try:
        fd = svc.add_field(
            entity_type=body.entity_type,
            field_key=body.field_key,
            label=body.label,
            field_type=body.field_type,
            options=body.options,
            required=body.required,
            sort_order=body.sort_order,
        )
    except FieldValidationError as e:
        raise _handle_field_error(e)
    return _to_response(fd)


@router.put("/{entity_type}/{field_key}", response_model=FieldResponse)
def update_field(
    entity_type: str,
    field_key: str,
    body: FieldUpdate,
    db: Session = Depends(get_db),
    _: Any = Depends(require_permission(Permission.CONFIG_EDIT)),
):
    """修改自定义字段定义"""
    svc = FieldService(db)
    try:
        fd = svc.update_field(
            entity_type=entity_type,
            field_key=field_key,
            label=body.label,
            field_type=body.field_type,
            options=body.options,
            required=body.required,
            sort_order=body.sort_order,
        )
    except FieldValidationError as e:
        raise _handle_field_error(e)
    return _to_response(fd)


@router.delete("/{entity_type}/{field_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(
    entity_type: str,
    field_key: str,
    db: Session = Depends(get_db),
    _: Any = Depends(require_permission(Permission.CONFIG_EDIT)),
):
    """删除自定义字段（系统字段受保护）"""
    try:
        deleted = FieldService(db).delete_field(entity_type, field_key)
    except FieldValidationError as e:
        raise _handle_field_error(e)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"字段不存在: {entity_type}.{field_key}")


# ===== 实体 ext_json 读写 =====


@router.post("/{entity_type}/{entity_id}/values")
def set_entity_values(
    entity_type: str,
    entity_id: int,
    body: EntityValues,
    db: Session = Depends(get_db),
    _: Any = Depends(require_permission(Permission.CONFIG_EDIT)),
):
    """批量写入实体自定义字段值（校验类型/必填/枚举）

    说明：写入依赖前端已持有实体对象（桌面端直调 FieldService.set_value），
    本端点提供 HTTP 通道；实体存在性由上层调用方保证。
    """
    svc = FieldService(db)
    try:
        svc.set_entity_values(entity_type, entity_id, body.values)
    except FieldValidationError as e:
        raise _handle_field_error(e)
    return {"entity_type": entity_type, "entity_id": entity_id, "values": body.values}
