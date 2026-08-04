"""
API 版本管理
支持：/api/v1/、/api/v2/、Deprecation Header、OpenAPI 标记
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class APIVersionMiddleware(BaseHTTPMiddleware):
    """API 版本中间件：从路径/Header 解析版本"""

    def __init__(self, app, default_version: str = "v1"):
        super().__init__(app)
        self.default_version = default_version

    async def dispatch(self, request: Request, call_next):
        # 从路径解析版本
        version = self._extract_version(request)
        request.state.api_version = version
        request.state.api_version_deprecated = version != "v2"  # v1 已弃用

        response = await call_next(request)

        # 添加版本头
        response.headers["X-API-Version"] = request.state.api_version

        return response

    def _extract_version(self, request) -> str:
        """从路径提取版本: /api/v1/... 或 /api/v2/..."""
        path = request.url.path
        if path.startswith("/api/"):
            parts = path.strip("/").split("/")
            if len(parts) >= 2 and parts[1].startswith("v"):
                return parts[1]
        return self.default_version


class DeprecationMiddleware(BaseHTTPMiddleware):
    """弃用警告中间件：为已弃用版本添加警告头"""

    def __init__(self, app, deprecated_versions: dict = None):
        super().__init__(app)
        self.deprecated_versions = deprecated_versions or {}

    async def dispatch(self, request, call_next):
        version = getattr(request.state, "api_version", "v1")

        if version in self.deprecated_versions:
            deprecation_info = self.deprecated_versions[version]
            request.state.deprecation_warning = deprecation_info

        response = await call_next(request)

        # 添加弃用警告头
        if hasattr(request.state, "deprecation_warning"):
            info = request.state.deprecation_warning
            response.headers["Deprecation"] = "true"
            if "date" in info:
                response.headers["Sunset"] = info["date"]
            if "link" in info:
                response.headers["Link"] = f'<{info["link"]}>; rel="deprecation"'

        return response
