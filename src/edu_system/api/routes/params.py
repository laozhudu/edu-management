"""参数管理 API 路由（M1：对齐若依 #7 参数，基于 GlobalSetting）"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_db, require_permission
from edu_system.core.permissions import Permission
from edu_system.models import GlobalSetting

router = APIRouter(prefix="/params", tags=["参数"])


class ParamCreate(BaseModel):
    key: str
    value: str = ""
    description: str = ""


class ParamUpdate(BaseModel):
    value: str | None = None
    description: str | None = None


@router.get("")
def param_list(
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_VIEW)),
):
    items = db.query(GlobalSetting).order_by(GlobalSetting.key).all()
    return {
        "items": [
            {
                "key": p.key,
                "value": p.value,
                "description": p.description,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in items
        ],
        "total": len(items),
    }


@router.post("", status_code=201)
def param_create(
    body: ParamCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    if not body.key.strip():
        raise HTTPException(status_code=400, detail="参数键不能为空")
    dup = db.query(GlobalSetting).filter(GlobalSetting.key == body.key.strip()).first()
    if dup:
        raise HTTPException(status_code=400, detail=f"参数「{body.key}」已存在")
    p = GlobalSetting(key=body.key.strip(), value=body.value, description=body.description)
    db.add(p)
    db.commit()
    return {"key": p.key}


@router.put("/{key}")
def param_update(
    key: str,
    body: ParamUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    p = db.query(GlobalSetting).filter(GlobalSetting.key == key).first()
    if not p:
        raise HTTPException(status_code=404, detail="参数不存在")
    if body.value is not None:
        p.value = body.value
    if body.description is not None:
        p.description = body.description
    db.commit()
    return {"ok": True, "key": key}


@router.delete("/{key}")
def param_delete(
    key: str,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    p = db.query(GlobalSetting).filter(GlobalSetting.key == key).first()
    if not p:
        raise HTTPException(status_code=404, detail="参数不存在")
    db.delete(p)
    db.commit()
    return {"ok": True}
