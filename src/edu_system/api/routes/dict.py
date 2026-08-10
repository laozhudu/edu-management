"""字典管理 API 路由（M1：对齐若依 #6 字典）"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_db, require_permission
from edu_system.core.permissions import Permission
from edu_system.models import DictData, DictType

router = APIRouter(prefix="/dict", tags=["字典"])


class DictTypeCreate(BaseModel):
    dict_type: str
    dict_name: str = ""
    remark: str = ""


class DictTypeUpdate(BaseModel):
    dict_name: str | None = None
    status: str | None = None
    remark: str | None = None


class DictDataCreate(BaseModel):
    dict_type: str
    dict_label: str
    dict_value: str = ""
    sort_order: int = 0


class DictDataUpdate(BaseModel):
    dict_label: str | None = None
    dict_value: str | None = None
    sort_order: int | None = None
    status: str | None = None


# ── 字典类型 ──


@router.get("/types")
def dict_type_list(
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    items = db.query(DictType).order_by(DictType.id).all()
    return {
        "items": [
            {
                "id": t.id,
                "dict_type": t.dict_type,
                "dict_name": t.dict_name,
                "status": t.status,
                "remark": t.remark,
            }
            for t in items
        ],
        "total": len(items),
    }


@router.post("/types", status_code=201)
def dict_type_create(
    body: DictTypeCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    if not body.dict_type.strip():
        raise HTTPException(status_code=400, detail="字典类型编码不能为空")
    dup = db.query(DictType).filter(DictType.dict_type == body.dict_type.strip()).first()
    if dup:
        raise HTTPException(status_code=400, detail=f"字典类型「{body.dict_type}」已存在")
    t = DictType(dict_type=body.dict_type.strip(), dict_name=body.dict_name, remark=body.remark)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "dict_type": t.dict_type}


@router.put("/types/{type_id}")
def dict_type_update(
    type_id: int,
    body: DictTypeUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    t = db.get(DictType, type_id)
    if not t:
        raise HTTPException(status_code=404, detail="字典类型不存在")
    if body.dict_name is not None:
        t.dict_name = body.dict_name
    if body.status is not None:
        t.status = body.status
    if body.remark is not None:
        t.remark = body.remark
    db.commit()
    return {"ok": True}


@router.delete("/types/{type_id}")
def dict_type_delete(
    type_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    t = db.get(DictType, type_id)
    if not t:
        raise HTTPException(status_code=404, detail="字典类型不存在")
    # 级联删除该类型的数据
    db.query(DictData).filter(DictData.dict_type == t.dict_type).delete()
    db.delete(t)
    db.commit()
    return {"ok": True}


# ── 字典数据 ──


@router.get("/data")
def dict_data_list(
    dict_type: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    q = db.query(DictData)
    if dict_type:
        q = q.filter(DictData.dict_type == dict_type)
    items = q.order_by(DictData.dict_type, DictData.sort_order, DictData.id).all()
    return {
        "items": [
            {
                "id": d.id,
                "dict_type": d.dict_type,
                "dict_label": d.dict_label,
                "dict_value": d.dict_value,
                "sort_order": d.sort_order,
                "status": d.status,
            }
            for d in items
        ],
        "total": len(items),
    }


@router.get("/data/{dict_type}")
def dict_data_by_type(
    dict_type: str,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    """按类型取字典数据（表单下拉用，仅正常状态）"""
    items = (
        db.query(DictData)
        .filter(DictData.dict_type == dict_type, DictData.status == "0")
        .order_by(DictData.sort_order, DictData.id)
        .all()
    )
    return [{"label": d.dict_label, "value": d.dict_value or d.dict_label} for d in items]


@router.post("/data", status_code=201)
def dict_data_create(
    body: DictDataCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    if not body.dict_type.strip() or not body.dict_label.strip():
        raise HTTPException(status_code=400, detail="字典类型和标签不能为空")
    t = db.query(DictType).filter(DictType.dict_type == body.dict_type.strip()).first()
    if not t:
        raise HTTPException(status_code=400, detail=f"字典类型「{body.dict_type}」不存在")
    d = DictData(
        dict_type=body.dict_type.strip(),
        dict_label=body.dict_label.strip(),
        dict_value=body.dict_value.strip() or body.dict_label.strip(),
        sort_order=body.sort_order,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id}


@router.put("/data/{data_id}")
def dict_data_update(
    data_id: int,
    body: DictDataUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    d = db.get(DictData, data_id)
    if not d:
        raise HTTPException(status_code=404, detail="字典数据不存在")
    if body.dict_label is not None:
        d.dict_label = body.dict_label
    if body.dict_value is not None:
        d.dict_value = body.dict_value
    if body.sort_order is not None:
        d.sort_order = body.sort_order
    if body.status is not None:
        d.status = body.status
    db.commit()
    return {"ok": True}


@router.delete("/data/{data_id}")
def dict_data_delete(
    data_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    d = db.get(DictData, data_id)
    if not d:
        raise HTTPException(status_code=404, detail="字典数据不存在")
    db.delete(d)
    db.commit()
    return {"ok": True}
