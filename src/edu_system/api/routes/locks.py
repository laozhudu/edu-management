"""
数据锁定 API 路由（M5-E6）

- POST /locks: 加锁（单条，含理由）
- DELETE /locks: 解锁（单条）
- POST /locks/batch: 批量加锁
- POST /locks/batch/unlock: 批量解锁
- GET  /locks: 锁定列表（按学期/实体类型过滤）

权限：加/解锁需 DATA_UNLOCK 权限（admin 默认拥有）；
查询需登录。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db, require_permission
from edu_system.core.permissions import Permission
from edu_system.models import DataLock, User
from edu_system.services.locks import DataLockService

router = APIRouter(prefix="/locks", tags=["数据锁定"])


class LockRequest(BaseModel):
    semester_id: int
    entity_type: str
    entity_id: int | None = None  # None=表级锁
    lock_level: str = "soft"  # soft/hard
    reason: str = ""


class UnlockRequest(BaseModel):
    semester_id: int
    entity_type: str
    entity_id: int | None = None


class BatchLockRequest(BaseModel):
    semester_id: int
    locks: list[LockRequest]


class BatchUnlockRequest(BaseModel):
    semester_id: int
    locks: list[UnlockRequest]


class LockResponse(BaseModel):
    id: int
    semester_id: int
    entity_type: str
    entity_id: int | None
    lock_level: str
    locked_by: str
    reason: str
    locked_at: str | None

    class Config:
        from_attributes = True


def _to_response(lock: DataLock) -> dict:
    return {
        "id": lock.id,
        "semester_id": lock.semester_id,
        "entity_type": lock.entity_type,
        "entity_id": lock.entity_id,
        "lock_level": lock.lock_level,
        "locked_by": lock.locked_by,
        "reason": lock.reason or "",
        "locked_at": lock.locked_at.isoformat() if lock.locked_at else None,
    }


@router.get("", response_model=list[dict])
def list_locks(
    semester_id: int | None = Query(None),
    entity_type: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """锁定列表（按学期/实体类型过滤）"""
    svc = DataLockService(db)
    locks = svc.list_locks(semester_id=semester_id, entity_type=entity_type)
    return [_to_response(lock) for lock in locks]


@router.post("", response_model=dict, status_code=201)
def create_lock(
    request: LockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_UNLOCK)),
):
    """加锁（单条，含理由）"""
    from edu_system.services.locks import LockLevel

    svc = DataLockService(db)
    level = (
        LockLevel(request.lock_level)
        if request.lock_level
        in (
            "soft",
            "hard",
        )
        else LockLevel.SOFT
    )
    try:
        lock = svc.lock(
            semester_id=request.semester_id,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            lock_level=level,
            locked_by=current_user.username,
            reason=request.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(lock)


@router.delete("")
def delete_lock(
    request: UnlockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_UNLOCK)),
):
    """解锁（单条）"""
    svc = DataLockService(db)
    try:
        ok = svc.unlock(
            semester_id=request.semester_id,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            unlocker=current_user.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="锁定记录不存在")
    return {"unlocked": True}


@router.post("/batch", response_model=dict)
def batch_lock(
    request: BatchLockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_UNLOCK)),
):
    """批量加锁"""
    from edu_system.services.locks import LockLevel

    svc = DataLockService(db)
    items = [
        {
            "entity_type": item.entity_type,
            "entity_id": item.entity_id,
            "lock_level": LockLevel(item.lock_level)
            if item.lock_level in ("soft", "hard")
            else LockLevel.SOFT,
            "locked_by": current_user.username,
            "reason": item.reason,
        }
        for item in request.locks
    ]
    locks = svc.batch_lock(request.semester_id, items)
    return {"locked": len(locks), "items": [_to_response(lock) for lock in locks]}


@router.post("/batch/unlock", response_model=dict)
def batch_unlock(
    request: BatchUnlockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_UNLOCK)),
):
    """批量解锁"""
    svc = DataLockService(db)
    items = [
        {"entity_type": item.entity_type, "entity_id": item.entity_id} for item in request.locks
    ]
    unlocked = svc.batch_unlock(request.semester_id, items, unlocker=current_user.username)
    return {"unlocked": len(unlocked)}
