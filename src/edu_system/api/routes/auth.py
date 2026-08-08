"""
认证 API 路由
- 登录/登出/刷新令牌
- 设备信任管理
- 当前用户信息
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.config import settings
from edu_system.core.auth import (
    DEVICE_TRUST_EXPIRE_DAYS,
    create_token_pair,
    generate_device_fingerprint,
    generate_device_id,
    verify_password,
    verify_refresh_token,
)
from edu_system.models import DeviceTrust, User

router = APIRouter(prefix="/auth", tags=["认证"])


# ===== Pydantic 模型 =====


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False
    device_name: str | None = None
    # 设备指纹字段（前端自动采集）
    user_agent: str | None = None
    accept_language: str | None = None
    screen_resolution: str | None = None
    timezone: str | None = None
    canvas_fingerprint: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str | None = None  # 从 Cookie 读取时可为空


class DeviceTrustRequest(BaseModel):
    device_name: str


class DeviceTrustResponse(BaseModel):
    device_id: str
    device_name: str
    trusted: bool
    created_at: str
    expires_at: str
    last_used_at: str | None = None


class DeviceListResponse(BaseModel):
    devices: list[DeviceTrustResponse]


class UserInfoResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    permissions: list[str]


# ===== 依赖注入 =====


def get_client_ip(request: Request) -> str:
    """获取客户端 IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def build_fingerprint_data(request: Request, login_data: LoginRequest) -> dict:
    """构建设备指纹数据"""
    return {
        "user_agent": login_data.user_agent or request.headers.get("User-Agent", ""),
        "accept_language": login_data.accept_language or request.headers.get("Accept-Language", ""),
        "screen_resolution": login_data.screen_resolution or "",
        "timezone": login_data.timezone or "",
        "canvas_fingerprint": login_data.canvas_fingerprint or "",
        "ip": get_client_ip(request),
    }


# ===== API 端点 =====


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    """用户登录

    - 验证用户名/密码
    - 生成 Access Token + Refresh Token
    - Refresh Token 存 HttpOnly Cookie
    - 可选：注册受信设备 (remember_me=True)
    """
    # 查找用户
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已禁用",
        )

    # 构建设备指纹
    fp_data = build_fingerprint_data(request, login_data)
    fingerprint = generate_device_fingerprint(fp_data)
    device_id = None

    # 如果 remember_me，尝试查找或注册受信设备
    if login_data.remember_me:
        device_trust = (
            db.query(DeviceTrust)
            .filter(
                DeviceTrust.user_id == user.id,
                DeviceTrust.fingerprint == fingerprint,
                DeviceTrust.trusted,
            )
            .first()
        )

        if device_trust:
            device_id = device_trust.device_id
            # 更新最后使用时间
            device_trust.last_used_at = datetime.utcnow()
        else:
            # 注册新受信设备
            device_id = generate_device_id()
            device_trust = DeviceTrust(
                device_id=device_id,
                user_id=user.id,
                device_name=login_data.device_name or f"设备 {device_id[:8]}",
                fingerprint=fingerprint,
                user_agent=fp_data["user_agent"],
                ip=fp_data["ip"],
                trusted=True,
                expires_at=datetime.now(UTC) + timedelta(days=DEVICE_TRUST_EXPIRE_DAYS),
            )
            db.add(device_trust)

        db.commit()

    # 生成令牌对
    token_pair = create_token_pair(
        user.id,
        device_id,
        permissions=user.role.permissions.split(",") if user.role and user.role.permissions else [],
        roles=[user.role.name] if user.role else [],
    )

    # 设置 HttpOnly Cookie 存 Refresh Token
    response.set_cookie(
        key="refresh_token",
        value=token_pair.refresh_token,
        httponly=True,
        secure=False,  # 开发环境 HTTP，生产环境设为 True
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/api/auth",
    )

    # 设置 access_token Cookie（非 HttpOnly，供整页跳转的页面路由识别登录态）
    response.set_cookie(
        key="access_token",
        value=token_pair.access_token,
        httponly=False,
        secure=False,
        samesite="lax",
        max_age=token_pair.expires_in,  # 15 分钟，与 token 同步
        path="/",
    )

    # 返回用户信息 + Access Token
    return LoginResponse(
        access_token=token_pair.access_token,
        expires_in=token_pair.expires_in,
        user={
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role.name if user.role else "user",
            "permissions": (
                user.role.permissions.split(",") if user.role and user.role.permissions else []
            ),
        },
    )


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(None, alias="refresh_token"),
    db: Session = Depends(get_db),
):
    """用户登出

    - 清除 HttpOnly Cookie
    - 可选：将 Refresh Token 加入黑名单 (防重放)
    """
    # TODO: 可选 - 将 refresh_token 加入黑名单/撤销列表
    # 目前仅清除 Cookie

    response.delete_cookie(
        key="refresh_token",
        path="/api/auth",
        httponly=True,
        secure=False,
        samesite="lax",
    )

    return {"message": "登出成功"}


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(None, alias="refresh_token"),
    db: Session = Depends(get_db),
):
    """刷新 Access Token

    - 从 HttpOnly Cookie 读取 Refresh Token
    - 验证有效性
    - 返回新的 Access Token
    - 可选：轮换 Refresh Token (安全增强)
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少刷新令牌",
        )

    try:
        payload = verify_refresh_token(refresh_token)
        user_id = int(payload["sub"])
        device_id = payload.get("device_id")

        # 验证用户仍存在且激活
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已禁用",
            )

        # 如果有设备 ID，验证设备信任仍有效
        if device_id:
            device_trust = (
                db.query(DeviceTrust)
                .filter(
                    DeviceTrust.device_id == device_id,
                    DeviceTrust.user_id == user_id,
                    DeviceTrust.trusted,
                )
                .first()
            )
            if not device_trust:
                device_id = None  # 设备信任已失效，不带 device_id 签发新 token

        # 生成新令牌对
        token_pair = create_token_pair(user_id, device_id)

        # 更新 Cookie
        response.set_cookie(
            key="refresh_token",
            value=token_pair.refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
            path="/api/auth",
        )

        return {
            "access_token": token_pair.access_token,
            "token_type": "bearer",
            "expires_in": token_pair.expires_in,
        }

    except ValueError:
        response.delete_cookie("refresh_token", path="/api/auth")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效或已过期",
        )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户信息"""
    return UserInfoResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        role=current_user.role.name if current_user.role else "user",
        permissions=(
            current_user.role.permissions.split(",")
            if current_user.role and current_user.role.permissions
            else []
        ),
    )


# ===== 设备信任管理 =====


@router.post("/device/trust", response_model=DeviceTrustResponse)
async def register_trusted_device(
    request: Request,
    device_data: DeviceTrustRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """注册受信设备 (需登录后调用)"""
    fingerprint_data = {
        "user_agent": request.headers.get("User-Agent", ""),
        "accept_language": request.headers.get("Accept-Language", ""),
        "screen_resolution": "",
        "timezone": "",
        "canvas_fingerprint": "",
        "ip": get_client_ip(request),
    }
    fingerprint = generate_device_fingerprint(fingerprint_data)

    # 检查是否已存在
    existing = (
        db.query(DeviceTrust)
        .filter(
            DeviceTrust.user_id == current_user.id,
            DeviceTrust.fingerprint == fingerprint,
        )
        .first()
    )

    if existing:
        existing.trusted = True
        existing.device_name = device_data.device_name
        existing.last_used_at = datetime.now(UTC)
        db.commit()
        device_trust = existing
    else:
        device_id = generate_device_id()
        device_trust = DeviceTrust(
            device_id=generate_device_id(),
            user_id=current_user.id,
            device_name=device_data.device_name,
            fingerprint=fingerprint,
            user_agent=request.headers.get("User-Agent", ""),
            ip=get_client_ip(request),
            trusted=True,
            expires_at=datetime.now(UTC) + timedelta(days=DEVICE_TRUST_EXPIRE_DAYS),
        )
        db.add(device_trust)
        db.commit()
        db.refresh(device_trust)

    return DeviceTrustResponse(
        device_id=device_trust.device_id,
        device_name=device_trust.device_name,
        trusted=device_trust.trusted,
        created_at=device_trust.created_at.isoformat(),
        expires_at=device_trust.expires_at.isoformat(),
        last_used_at=device_trust.last_used_at.isoformat() if device_trust.last_used_at else None,
    )


@router.get("/device/trusted", response_model=DeviceListResponse)
async def list_trusted_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的受信设备列表"""
    devices = (
        db.query(DeviceTrust)
        .filter(
            DeviceTrust.user_id == current_user.id,
            DeviceTrust.trusted,
        )
        .order_by(DeviceTrust.last_used_at.desc().nullslast())
        .all()
    )

    return DeviceListResponse(
        devices=[
            DeviceTrustResponse(
                device_id=d.device_id,
                device_name=d.device_name,
                trusted=d.trusted,
                created_at=d.created_at.isoformat(),
                expires_at=d.expires_at.isoformat(),
                last_used_at=d.last_used_at.isoformat() if d.last_used_at else None,
            )
            for d in devices
        ]
    )


@router.delete("/device/trust/{device_id}")
async def revoke_device_trust(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """撤销设备信任"""
    device_trust = (
        db.query(DeviceTrust)
        .filter(
            DeviceTrust.device_id == device_id,
            DeviceTrust.user_id == current_user.id,
        )
        .first()
    )

    if not device_trust:
        raise HTTPException(status_code=404, detail="设备不存在")

    device_trust.trusted = False
    db.commit()

    return {"message": "设备信任已撤销"}
