"""
用户管理 API 路由（P3-B：用户权限 Web 化）

- GET /users: 用户列表（含角色名）
- POST /users: 创建用户
- PUT /users/{id}: 更新（角色/显示名/停启用）
- PUT /users/{id}/password: 重置密码
- GET /users/roles: 角色列表
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.models import Role, User

router = APIRouter(prefix="/users", tags=["用户管理"])


class UserCreateRequest(BaseModel):
    """创建用户请求"""

    username: str
    password: str
    display_name: str = ""
    role_name: str = "reader"


class UserUpdateRequest(BaseModel):
    """更新用户请求（部分字段）"""

    display_name: str | None = None
    role_name: str | None = None
    is_active: bool | None = None


class PasswordResetRequest(BaseModel):
    """重置密码请求"""

    password: str


@router.get("")
def user_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户列表"""
    items = db.query(User).order_by(User.id).all()
    return {
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "role": u.role.name if u.role else None,
                "is_active": u.is_active,
            }
            for u in items
        ],
        "total": len(items),
    }


@router.get("/roles")
def role_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """角色列表"""
    items = db.query(Role).order_by(Role.id).all()
    return {
        "items": [{"id": r.id, "name": r.name, "description": r.description} for r in items],
        "total": len(items),
    }


@router.post("", status_code=201)
def create_user(
    body: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建用户"""
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    dup = db.query(User).filter(User.username == username).first()
    if dup:
        raise HTTPException(status_code=400, detail=f"用户名「{username}」已存在")

    role = db.query(Role).filter(Role.name == body.role_name).first()
    if role is None:
        role = db.query(Role).filter(Role.name == "reader").first()

    from edu_system.api.deps import get_password_hash

    user = User(
        username=username,
        password_hash=get_password_hash(body.password),
        display_name=body.display_name or username,
        role_id=role.id if role else None,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username}


@router.put("/{user_id}")
def update_user(
    user_id: int,
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新用户（角色/显示名/停启用）"""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")
    # 禁止停用自己（防止锁死）
    if user.id == current_user.id and body.is_active is False:
        raise HTTPException(status_code=400, detail="不能停用当前登录用户")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role_name is not None:
        role = db.query(Role).filter(Role.name == body.role_name).first()
        if role:
            user.role_id = role.id
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "role": user.role.name if user.role else None}


@router.put("/{user_id}/password")
def reset_password(
    user_id: int,
    body: PasswordResetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重置密码"""
    if not body.password:
        raise HTTPException(status_code=400, detail="新密码不能为空")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    from edu_system.api.deps import get_password_hash

    user.password_hash = get_password_hash(body.password)
    db.commit()
    return {"ok": True, "message": f"用户「{user.username}」密码已重置"}
