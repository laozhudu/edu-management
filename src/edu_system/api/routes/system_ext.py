"""M2：通知公告 + 登录日志 + 在线用户 API（对齐若依 #8/#10/#11）"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import (
    PageQuery,
    get_current_user,
    get_db,
    paginate_response,
    require_permission,
)
from edu_system.core.permissions import Permission
from edu_system.models import LoginLog, Notice, NoticeRead, OnlineUser, User

router = APIRouter(tags=["系统扩展"])

# ── 通知公告 ──


class NoticeCreate(BaseModel):
    title: str
    content: str = ""
    notice_type: str = "notice"


class NoticeUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None


@router.get("/notice")
def notice_list(
    status: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_VIEW)),
):
    q = db.query(Notice)
    if status:
        q = q.filter(Notice.status == status)
    items = q.order_by(Notice.id.desc()).all()
    return {
        "items": [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "notice_type": n.notice_type,
                "status": n.status,
                "publisher": n.publisher,
                "read_count": n.read_count,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
        "total": len(items),
    }


@router.post("/notice", status_code=201)
def notice_create(
    body: NoticeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="标题不能为空")
    n = Notice(
        title=body.title.strip(),
        content=body.content,
        notice_type=body.notice_type,
        publisher=current_user.username,
        status="0",
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return {"id": n.id}


@router.put("/notice/{notice_id}")
def notice_update(
    notice_id: int,
    body: NoticeUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    n = db.get(Notice, notice_id)
    if not n:
        raise HTTPException(status_code=404, detail="公告不存在")
    if body.title is not None:
        n.title = body.title
    if body.content is not None:
        n.content = body.content
    if body.status is not None:
        n.status = body.status
    db.commit()
    return {"ok": True}


@router.delete("/notice/{notice_id}")
def notice_delete(
    notice_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    n = db.get(Notice, notice_id)
    if not n:
        raise HTTPException(status_code=404, detail="公告不存在")
    db.query(NoticeRead).filter(NoticeRead.notice_id == notice_id).delete()
    db.delete(n)
    db.commit()
    return {"ok": True}


@router.post("/notice/{notice_id}/read")
def notice_mark_read(
    notice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """标记公告已读"""
    n = db.get(Notice, notice_id)
    if not n:
        raise HTTPException(status_code=404, detail="公告不存在")
    exists = (
        db.query(NoticeRead)
        .filter(NoticeRead.notice_id == notice_id, NoticeRead.user_id == current_user.id)
        .first()
    )
    if not exists:
        db.add(NoticeRead(notice_id=notice_id, user_id=current_user.id))
        n.read_count = (n.read_count or 0) + 1
        db.commit()
    return {"ok": True}


# ── 登录日志 ──


@router.get("/login-logs")
def login_log_list(
    query: PageQuery = Depends(),
    status: str | None = None,
    username: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.SYSTEM_AUDIT)),
):
    q = db.query(LoginLog)
    if status:
        q = q.filter(LoginLog.status == status)
    if username:
        q = q.filter(LoginLog.username == username)
    total = q.count()
    items = q.order_by(LoginLog.id.desc()).offset(query.offset).limit(query.page_size).all()
    return paginate_response(
        [
            {
                "id": lg.id,
                "username": lg.username,
                "status": lg.status,
                "msg": lg.msg,
                "ip": lg.ip,
                "user_agent": lg.user_agent,
                "created_at": lg.created_at.isoformat() if lg.created_at else None,
            }
            for lg in items
        ],
        total,
        query.page,
        query.page_size,
    )


# ── 在线用户 ──


@router.get("/online-users")
def online_user_list(
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.SYSTEM_AUDIT)),
):
    items = db.query(OnlineUser).order_by(OnlineUser.login_at.desc()).all()
    return {
        "total": len(items),
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "ip": u.ip,
                "login_at": u.login_at.isoformat() if u.login_at else None,
                "expire_at": u.expire_at.isoformat() if u.expire_at else None,
            }
            for u in items
        ],
    }


@router.post("/online-users/{user_id}/kick")
def online_user_kick(
    user_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.SYSTEM_ADMIN)),
):
    """强制下线（删除在线记录）"""
    u = db.get(OnlineUser, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="在线用户不存在")
    db.delete(u)
    db.commit()
    return {"ok": True}
