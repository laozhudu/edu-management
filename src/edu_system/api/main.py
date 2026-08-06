"""
FastAPI 主应用工厂
集成：Admin 界面、业务 API、认证、监控、静态文件
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from edu_system.api.logging import LoggingMiddleware
from edu_system.api.middleware.gateway import GatewayMiddleware
from edu_system.api.middleware.security import SecurityMiddleware
from edu_system.api.routes import scheduler, stats
from edu_system.api.service_registry import register_services
from edu_system.api.versions import APIVersionMiddleware, DeprecationMiddleware
from edu_system.config import settings
from edu_system.core.idempotency import IdempotencyMiddleware


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 启动时初始化数据库
        from edu_system.database import init_db_with_defaults

        init_db_with_defaults()

        # 初始化 Feature Flag 配置（不存在则自动创建）
        from edu_system.core.features import ensure_features_config

        ensure_features_config()

        # 注册 Outbox 事件处理定时任务（每 10 秒轮询）
        from edu_system.core.event_bus import register_outbox_job
        from edu_system.services.scheduler import get_scheduler

        register_outbox_job(get_scheduler().scheduler)

        yield

    app = FastAPI(
        title="教务管理系统 API",
        description="教务管理系统 v2.0",
        version="2.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Session 中间件
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

    # API 版本中间件
    app.add_middleware(APIVersionMiddleware, default_version="v1")

    # 弃用警告中间件
    app.add_middleware(
        DeprecationMiddleware,
        deprecated_versions={
            "v1": {
                "date": "2025-12-31",
                "link": "https://api.edu.example.com/docs/migration/v1-to-v2",
            }
        },
    )

    # 结构化日志中间件
    app.add_middleware(LoggingMiddleware)

    # 安全中间件（CSP/HSTS/限流等）
    app.add_middleware(SecurityMiddleware)

    # 网关中间件（服务级权限/限流/审计）
    app.add_middleware(GatewayMiddleware)

    # 幂等性中间件（仅拦截写请求，Idempotency-Key 防重复）
    app.add_middleware(IdempotencyMiddleware)

    # 注册服务注册表
    register_services(app)

    # 注册路由
    app.include_router(stats.router, prefix="/api")
    app.include_router(scheduler.router, prefix="/api")
    from edu_system.api.routes import (
        attendance,
        audit,
        auth,
        config,
        column_config,
        exam,
        import_export,
        locks,
        meta,
        pages,
        score,
        semester_inherit,
        students,
        teachers,
    )

    app.include_router(students.router, prefix="/api")
    app.include_router(teachers.router, prefix="/api")
    app.include_router(semester_inherit.router, prefix="/api")
    app.include_router(locks.router, prefix="/api")
    app.include_router(import_export.router, prefix="/api")
    app.include_router(audit.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(score.router, prefix="/api")
    app.include_router(attendance.router, prefix="/api")
    app.include_router(exam.router, prefix="/api")
    app.include_router(meta.router, prefix="/api")
    app.include_router(config.router, prefix="/api")
    
    # 手动注册 column_config 路由（include_router 在此环境有问题，需手动注册）
    # 先清除现有的同路径路由（避免重复）
    new_routes = []
    for route in column_config.router.routes:
        new_path = "/api" + route.path
        new_format = "/api" + route.path_format
        # 重新创建 APIRoute 以正确生成 path_regex
        from fastapi.routing import APIRoute
        new_route = APIRoute(
            path=new_path,
            endpoint=route.endpoint,
            methods=route.methods,
            response_class=route.response_class,
            status_code=route.status_code,
            tags=route.tags,
            summary=route.summary,
            description=route.description,
            response_description=route.response_description,
            responses=route.responses,
            deprecated=route.deprecated,
            operation_id=route.operation_id,
            response_model=route.response_model,
            response_model_include=route.response_model_include,
            response_model_exclude=route.response_model_exclude,
            response_model_by_alias=route.response_model_by_alias,
            response_model_exclude_unset=route.response_model_exclude_unset,
            response_model_exclude_defaults=route.response_model_exclude_defaults,
            response_model_exclude_none=route.response_model_exclude_none,
            include_in_schema=route.include_in_schema,
            name=route.name,
            dependencies=route.dependencies,
            callbacks=route.callbacks,
            openapi_extra=route.openapi_extra,
        )
        new_routes.append(new_route)
    
    for r in new_routes:
        app.router.routes.append(r)
    
    app.include_router(pages.router)  # Web 页面路由（无 /api 前缀）
    # app.include_router(admin.router, prefix="/api")
    # app.include_router(class_roster.router, prefix="/api")

    # 静态文件服务
    try:
        app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")
    except:
        pass

    # 健康检查
    @app.get("/healthz")
    async def healthz():
        from edu_system.services.cache import cache_service

        return {
            "status": "healthy",
            "version": "2.0.0",
            "cache_version": cache_service.get_version(),
        }

    # 挂载 Admin 界面
    from edu_system.api.admin_interface import create_admin_app as create_admin

    admin_app = create_admin()
    app.mount("/admin", admin_app)

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="warning")
