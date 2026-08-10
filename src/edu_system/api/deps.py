"""
FastAPI 依赖注入
提供数据库会话、当前学期、当前用户、权限验证等依赖
"""

from collections.abc import Generator
from datetime import datetime, timedelta

# 密码加密（直接使用 bcrypt 库，绕过 passlib 1.7.4 + bcrypt 4.x 不兼容）
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from edu_system.config import settings
from edu_system.core.context import SystemContext, get_current_context, set_current_context
from edu_system.core.permissions import Permission
from edu_system.database import get_active_semester, get_session, set_active_semester
from edu_system.models import User


def _check_bcrypt(password: str) -> None:
    """bcrypt 72 字节硬限制预检查"""
    if len(password.encode("utf-8")) > 72:
        raise ValueError("密码不能超过 72 字节")


def get_password_hash(password: str) -> str:
    """生成 bcrypt 密码哈希"""
    _check_bcrypt(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


def get_current_semester() -> int:
    """获取当前激活学期 ID"""
    return get_active_semester()


def set_current_semester_dep(semester_id: int):
    """设置当前学期（依赖注入版本）"""
    set_active_semester(semester_id)
    return semester_id


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        # 哈希格式不合法（如空串/旧格式），回退 passlib 兼容解析
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """创建刷新令牌"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """解码令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """获取当前用户（从 JWT 令牌）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已禁用")

    return user


async def get_current_user_ws(token: str, db: Session) -> User:
    """WebSocket 专用：获取当前用户"""
    payload = decode_token(token)
    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="无效令牌")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


def require_permission(perm: Permission):
    """权限依赖：检查用户是否拥有指定权限"""

    def permission_checker(
        current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        # 超级管理员拥有所有权限
        if current_user.role and current_user.role.name == "admin":
            return current_user

        # 检查用户角色权限（新表 role_permissions 优先，回退旧字符串列）
        if current_user.role:
            from edu_system.services.permissions import PermissionService

            role_id = int(current_user.role.id)
            perms = PermissionService(db).get_permissions(role_id)
            if perm.value in perms:
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"权限不足：需要 {perm.value}"
        )

    return permission_checker


def get_current_context_dep() -> SystemContext:
    """获取当前系统上下文（FastAPI 依赖注入版本）"""
    ctx = get_current_context()
    if ctx is None:
        ctx = SystemContext()
        set_current_context(ctx)
    return ctx


# ════════════════════════════════════
# B2：通用分页（对齐若依 PageHelper/startPage）
# ════════════════════════════════════


class PageQuery:
    """通用分页查询参数依赖（对齐若依 PageDomain）"""

    def __init__(
        self,
        page: int = 1,
        page_size: int = 50,
        order_by: str | None = None,
    ):
        self.page = max(page, 1)
        self.page_size = min(max(page_size, 1), 200)
        self.offset = (self.page - 1) * self.page_size
        self.order_by = order_by


def paginate_response(
    items: list,
    total: int,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """统一分页返回结构 {items, total, page, page_size}"""
    return {"items": items, "total": total, "page": page, "page_size": page_size}
