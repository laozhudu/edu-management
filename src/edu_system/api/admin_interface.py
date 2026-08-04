"""
FastAPI 管理后台接口 - 简化版（不依赖 CRUDAdmin）
提供基础的管理 API 接口，后续可替换为完整的 Admin UI
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from edu_system.config import settings
from edu_system.database import get_session, init_db_with_defaults


def _create_admin_app() -> FastAPI:
    """创建管理后台 FastAPI 应用"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 启动时初始化数据库
        init_db_with_defaults()
        yield
        # 关闭时清理

    app = FastAPI(
        title="教务管理系统 - 管理后台",
        description="基础管理 API 接口",
        version="2.0.0",
        lifespan=lifespan,
    )

    # 基础依赖
    def get_db():
        db = get_session()
        try:
            yield db
        finally:
            db.close()

    # 健康检查
    @app.get("/health")
    def health():
        return {"status": "healthy", "version": "2.0.0"}

    # 基础信息
    @app.get("/info")
    def info():
        return {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": "development" if settings.DEBUG else "production",
        }

    # 这里可以后续添加具体的管理 API 路由
    # 例如：用户管理、角色管理、配置管理等

    return app


def create_admin_app() -> FastAPI:
    """创建管理后台 FastAPI 应用（导出函数）"""
    return _create_admin_app()


if __name__ == "__main__":
    import uvicorn

    app = _create_admin_app()
    uvicorn.run(app, host="0.0.0.0", port=8081, log_level="info")
