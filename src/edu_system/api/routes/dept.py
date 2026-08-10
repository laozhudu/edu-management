"""部门管理 API（B5：对齐若依 sys_dept 树形）"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_db, require_permission
from edu_system.core.permissions import Permission
from edu_system.models import Department

router = APIRouter(tags=["部门管理"])


class DeptCreate(BaseModel):
    dept_name: str
    parent_id: int | None = None
    order_num: int = 0
    leader: str = ""
    phone: str = ""


class DeptUpdate(BaseModel):
    dept_name: str | None = None
    parent_id: int | None = None
    order_num: int | None = None
    leader: str | None = None
    phone: str | None = None
    status: str | None = None


def _to_dict(d: Department) -> dict:
    return {
        "id": d.id,
        "parent_id": d.parent_id,
        "dept_name": d.dept_name,
        "order_num": d.order_num,
        "leader": d.leader,
        "phone": d.phone,
        "status": d.status,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


@router.get("/dept")
def dept_tree(
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_VIEW)),
):
    """部门树（含 children 嵌套）"""
    depts = db.query(Department).order_by(Department.order_num).all()
    by_id = {d.id: _to_dict(d) for d in depts}
    roots = []
    for d in depts:
        node = by_id[d.id]
        node["children"] = []
        pid = d.parent_id
        if pid and pid in by_id:
            by_id[pid]["children"].append(node)
        else:
            roots.append(node)
    return {"items": roots, "total": len(depts)}


@router.post("/dept", status_code=201)
def dept_create(
    body: DeptCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    if not body.dept_name.strip():
        raise HTTPException(status_code=400, detail="部门名称不能为空")
    if body.parent_id:
        parent = db.get(Department, body.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="上级部门不存在")
    d = Department(
        dept_name=body.dept_name.strip(),
        parent_id=body.parent_id,
        order_num=body.order_num,
        leader=body.leader,
        phone=body.phone,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id}


@router.put("/dept/{dept_id}")
def dept_update(
    dept_id: int,
    body: DeptUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    d = db.get(Department, dept_id)
    if not d:
        raise HTTPException(status_code=404, detail="部门不存在")
    if body.dept_name is not None:
        d.dept_name = body.dept_name
    if body.parent_id is not None:
        if body.parent_id == dept_id:
            raise HTTPException(status_code=400, detail="上级部门不能是自己")
        d.parent_id = body.parent_id
    if body.order_num is not None:
        d.order_num = body.order_num
    if body.leader is not None:
        d.leader = body.leader
    if body.phone is not None:
        d.phone = body.phone
    if body.status is not None:
        d.status = body.status
    db.commit()
    return {"ok": True}


@router.delete("/dept/{dept_id}")
def dept_delete(
    dept_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    d = db.get(Department, dept_id)
    if not d:
        raise HTTPException(status_code=404, detail="部门不存在")
    if db.query(Department).filter(Department.parent_id == dept_id).first():
        raise HTTPException(status_code=400, detail="存在下级部门，无法删除")
    db.delete(d)
    db.commit()
    return {"ok": True}
