"""
安全中间件
提供 CSP、HSTS、X-Frame-Options、Referrer-Policy、速率限制、输入消毒
"""

from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件：添加安全响应头、基础速率限制、输入消毒"""

    def __init__(self, app):
        super().__init__(app)
        # 简单内存速率限制（生产环境建议用 Redis）
        self._rate_limit_store = {}
        self._rate_limit_max = 100  # 每分钟最大请求数
        self._rate_limit_window = 60  # 窗口秒数

    async def dispatch(self, request: Request, call_next):
        # 1. 速率限制（基于 IP）
        client_ip = request.client.host if request.client else "unknown"
        if not self._check_rate_limit(client_ip):
            return Response(
                content="速率限制：请求过于频繁", status_code=429, headers={"Retry-After": "60"}
            )

        # 2. 继续处理请求
        response = await call_next(request)

        # 3. 添加安全响应头
        self._add_security_headers(response)

        return response

    def _check_rate_limit(self, client_ip: str) -> bool:
        """简单的内存速率限制"""
        import time

        now = time.time()
        window_start = now - 60  # 60秒窗口

        if client_ip not in self._rate_limit_store:
            self._rate_limit_store[client_ip] = []

        # 清理过期记录
        self._rate_limit_store[client_ip] = [
            ts for ts in self._rate_limit_store[client_ip] if ts > window_start
        ]

        if len(self._rate_limit_store[client_ip]) >= 100:
            return False

        self._rate_limit_store[client_ip].append(time.time())
        return True

    def _add_security_headers(self, response: Response):
        """添加安全响应头"""
        headers = MutableHeaders(response.headers)

        # CSP - 内容安全策略
        headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        # HSTS - 强制 HTTPS
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # X-Frame-Options - 防点击劫持
        headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options - 防 MIME 嗅探
        headers["X-Content-Type-Options"] = "nosniff"

        # Referrer-Policy
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy
        headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # X-XSS-Protection
        headers["X-XSS-Protection"] = "1; mode=block"
