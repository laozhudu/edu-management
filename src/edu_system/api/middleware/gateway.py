"""
API 网关中间件：服务级权限控制 + 限流 + 审计日志
"""

import json
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from edu_system.api.service_registry import service_registry


class GatewayMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.service_registry = service_registry
        self._rate_limit_store = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # 1. 解析服务代码
        service_code = self._extract_service_code(request)

        # 跳过公开端点（健康检查/认证/UI 配置）
        if self._is_public_endpoint(request):
            return await call_next(request)

        # 2. 服务是否启用
        if service_code and not self.service_registry.is_enabled(service_code):
            return JSONResponse(
                status_code=403,
                content={"error": f"服务 {service_code} 已禁用"},
                headers={"X-Service-Disabled": "true"},
            )

        # 3. 服务级限流
        if self._is_service_rate_limited(request, service_code):
            config = self.service_registry.get_config(service_code)
            window = config.get("rate_limit_window", 60) if config else 60
            return JSONResponse(
                status_code=429,
                content={"error": f"服务 {service_code} 请求过于频繁"},
                headers={"Retry-After": str(window), "X-Service-Rate-Limited": "true"},
            )

        # 4. 权限校验
        if service_code:
            required_perms = self.service_registry.get_required_permissions(service_code)
            allowed_roles = self.service_registry.get_allowed_roles(service_code)

            # 获取当前用户权限/角色（从 Session/JWT）
            user_perms, user_roles = self._get_user_context(request)

            # 权限校验
            if required_perms and not any(p in user_perms for p in required_perms):
                return JSONResponse(
                    status_code=403,
                    content={"error": f"缺少权限: {required_perms}"},
                    headers={"X-Permission-Denied": "true"},
                )

            if allowed_roles and not any(r in user_roles for r in allowed_roles):
                return JSONResponse(
                    status_code=403,
                    content={"error": f"角色不匹配，需要: {allowed_roles}"},
                    headers={"X-Role-Denied": "true"},
                )

        # 5. 记录审计日志（异步，不阻塞响应）
        start_time = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)

        # 记录审计（异步，不阻塞）
        self._log_audit_async(request, response, service_code, duration_ms)

        # 添加服务标识头
        if service_code:
            response.headers["X-Service-Code"] = service_code
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        return response

    def _is_public_endpoint(self, request: Request) -> bool:
        """公开端点（跳过网关校验）：健康检查 + 认证 + UI 配置"""
        if self._is_health_check(request):
            return True
        # UI 配置：公开只读（品牌/导航结构），Web 登录页渲染依赖
        if request.url.path in ("/api/config", "/api/config/"):
            return True
        return False

    def _is_health_check(self, request: Request) -> bool:
        """检查是否为健康检查端点或认证相关端点（跳过网关校验）"""
        path = request.url.path
        # 健康检查端点
        if path in (
            "/healthz",
            "/api/stats/health",
            "/admin/health",
            "/api/auth/login",
            "/api/auth/logout",
            "/api/auth/refresh",
            "/api/auth/device/trust",
            "/api/auth/device/trusted",
            "/api/auth/me",
        ) or path.startswith("/api/stats/health"):
            return True
        # 所有认证相关端点跳过网关校验
        if path.startswith("/api/auth/"):
            return True
        return False

    def _extract_service_code(self, request: Request) -> str | None:
        """从路径提取服务代码: /api/{service_code}/..."""
        path = request.url.path
        if path.startswith("/api/"):
            parts = path.strip("/").split("/")
            if len(parts) >= 2:
                return parts[1]  # /api/{service_code}/...
        return None

    def _is_service_rate_limited(self, request: Request, service_code: str) -> bool:
        """服务级限流"""
        if not service_code:
            return False

        config = self.service_registry.get_config(service_code)
        if not config:
            return False

        rate_limit = config.get("rate_limit")
        if not rate_limit:
            return False

        client_ip = request.client.host if request.client else "unknown"
        key = f"{service_code}:{client_ip}"
        now = time.time()
        window = config.get("rate_limit_window", 60)
        max_requests = rate_limit

        # 清理过期记录
        self._rate_limit_store[key] = [
            ts for ts in self._rate_limit_store[key] if now - ts < window
        ]

        if len(self._rate_limit_store[key]) >= max_requests:
            return True

        self._rate_limit_store[key].append(time.time())
        return False

    def _get_user_context(self, request: Request) -> tuple:
        """获取当前用户权限和角色"""
        # 从 Session 获取
        try:
            user_perms = request.session.get("permissions", [])
            user_roles = request.session.get("roles", [])
        except AssertionError:
            # SessionMiddleware 未安装（如测试环境）
            user_perms = []
            user_roles = []

        # 如果是 JWT 认证（Web 端），解析 JWT 获取权限/角色
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from jose import jwt

                from edu_system.config import settings

                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                # 从 payload 获取用户 ID，再查数据库获取权限/角色
                # 简化：直接从 token 中获取（实际应查数据库）
                user_perms = payload.get("permissions", [])
                user_roles = payload.get("roles", [])
            except Exception:
                pass

        return user_perms, user_roles

    def _log_audit_async(self, request: Request, response, service_code: str, duration_ms: int):
        """异步记录审计日志（简化版：同步记录，生产用队列）"""
        try:
            from sqlalchemy import text

            from edu_system.database import get_session

            session = next(get_session())
            session.execute(
                text(
                    """
                    INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, operator, ip, created_at)
                    VALUES (:table, :rid, :act, :old, :new, :op, :ip, :created)
                """
                ),
                {
                    "table": "api_requests",
                    "rid": 0,
                    "act": "API_REQUEST",
                    "old": json.dumps({"method": request.method, "path": request.url.path}),
                    "new": json.dumps(
                        {
                            "status": response.status_code,
                            "duration_ms": duration_ms,
                            "service": service_code,
                        }
                    ),
                    "op": request.session.get("user_id", "anonymous"),
                    "ip": request.client.host if request.client else "unknown",
                    "created": datetime.now(),
                },
            )
            session.commit()
        except:
            pass  # 审计失败不影响主流程
        finally:
            pass


# 导入依赖
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
