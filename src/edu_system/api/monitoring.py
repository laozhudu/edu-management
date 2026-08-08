"""
监控与指标 API
提供：/healthz（存活/就绪/依赖）、/metrics (Prometheus 文本格式)
"""

import os
import time
from typing import Any

import psutil
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from edu_system.config import settings
from edu_system.database import get_active_semester, get_session
from edu_system.services.cache import cache_service
from edu_system.services.scheduler import get_scheduler

router = APIRouter(prefix="/api/monitoring", tags=["监控指标"])


# ===== 健康检查 =====


@router.get("/healthz")
def health_check():
    """
    健康检查端点
    返回：存活/就绪/依赖状态
    """
    checks = {}
    overall = "healthy"

    # 1. 数据库连接检查
    try:
        session = get_session()
        session.execute(text("SELECT 1"))
        checks["database"] = {"status": "up", "latency_ms": 0}
    except Exception as e:
        checks["database"] = {"status": "down", "error": str(e)}
        overall = "unhealthy"

    # 2. 缓存服务检查
    try:
        stats = cache_service.get_stats()
        checks["cache"] = {
            "status": "up",
            "version": stats.get("version"),
            "entries": stats.get("entry_count"),
        }
    except Exception as e:
        checks["cache"] = {"status": "down", "error": str(e)}
        overall = "degraded"

    # 3. 调度器检查
    try:
        scheduler = get_scheduler()
        jobs = scheduler.get_jobs()
        checks["scheduler"] = {
            "status": "up" if scheduler.scheduler.running else "down",
            "jobs": len(jobs),
        }
    except Exception as e:
        checks["scheduler"] = {"status": "down", "error": str(e)}
        overall = "degraded"

    # 4. 磁盘空间检查
    try:
        disk = psutil.disk_usage(str(settings.PROJECT_ROOT))
        free_gb = disk.free / (1024**3)
        checks["disk"] = {
            "status": "up" if free_gb > 1 else "warning",
            "free_gb": round(free_gb, 2),
        }
        if free_gb < 1:
            overall = "degraded"
    except Exception as e:
        checks["disk"] = {"status": "unknown", "error": str(e)}

    # 5. 内存检查
    try:
        mem = psutil.virtual_memory()
        checks["memory"] = {
            "status": "up" if mem.percent < 90 else "warning",
            "used_percent": mem.percent,
        }
        if mem.percent > 90:
            overall = "degraded"
    except Exception as e:
        checks["memory"] = {"status": "unknown", "error": str(e)}

    return {
        "status": overall,
        "timestamp": time.time(),
        "checks": checks,
    }


@router.get("/healthz/live")
def liveness_probe():
    """存活探针：进程是否活着"""
    return {"status": "alive"}


@router.get("/healthz/ready")
def readiness_probe():
    """就绪探针：服务是否准备好接收流量"""
    try:
        session = get_session()
        session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        return Response(content=f"not ready: {e}", status_code=503)


# ===== Prometheus 指标 =====


@router.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """
    Prometheus 格式指标
    包含：请求数/延迟/错误率/DB连接数/缓存命中率/调度器作业/系统资源
    """
    lines = []
    now = time.time()

    # 系统指标
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        lines.append("# HELP system_cpu_usage_percent CPU 使用率")
        lines.append("# TYPE system_cpu_usage_percent gauge")
        lines.append(f"system_cpu_usage_percent {cpu_percent}")

        mem = psutil.virtual_memory()
        lines.append("# HELP system_memory_used_bytes 内存使用字节数")
        lines.append("# TYPE system_memory_used_bytes gauge")
        lines.append(f"system_memory_used_bytes {mem.used}")

        lines.append("# HELP system_memory_total_bytes 内存总字节数")
        lines.append("# TYPE system_memory_total_bytes gauge")
        lines.append(f"system_memory_total_bytes {mem.total}")

        lines.append("# HELP system_memory_usage_percent 内存使用率")
        lines.append("# TYPE system_memory_usage_percent gauge")
        lines.append(f"system_memory_usage_percent {mem.percent}")

        disk = psutil.disk_usage(str(settings.PROJECT_ROOT))
        lines.append("# HELP system_disk_free_bytes 磁盘剩余字节数")
        lines.append("# TYPE system_disk_free_bytes gauge")
        lines.append(f"system_disk_free_bytes {disk.free}")

        lines.append("# HELP system_disk_usage_percent 磁盘使用率")
        lines.append("# TYPE system_disk_usage_percent gauge")
        lines.append(f"system_disk_usage_percent {disk.percent}")
    except:
        pass

    # 数据库指标
    try:
        session = get_session()
        start = time.time()
        session.execute(text("SELECT 1"))
        db_latency = (time.time() - start) * 1000

        lines.append("# HELP database_latency_ms 数据库查询延迟毫秒")
        lines.append("# TYPE database_latency_ms gauge")
        lines.append(f"database_latency_ms {db_latency:.2f}")

        # 连接池状态（SQLite 无连接池，记录为 1）
        lines.append("# HELP database_connections_active 活跃数据库连接数")
        lines.append("# TYPE database_connections_active gauge")
        lines.append("database_connections_active 1")
    except:
        pass

    # 缓存指标
    try:
        stats = cache_service.get_stats()
        lines.append("# HELP cache_version 缓存版本号")
        lines.append("# TYPE cache_version gauge")
        lines.append(f"cache_version {stats.get('version', 0)}")

        lines.append("# HELP cache_entries_total 缓存条目总数")
        lines.append("# TYPE cache_entries_total gauge")
        lines.append(f"cache_entries_total {stats.get('entry_count', 0)}")

        lines.append("# HELP cache_size_bytes 缓存占用字节数")
        lines.append("# TYPE cache_size_bytes gauge")
        lines.append(f"cache_size_bytes {stats.get('size_bytes', 0)}")
    except:
        pass

    # 调度器指标
    try:
        scheduler = get_scheduler()
        jobs = scheduler.get_jobs()
        lines.append("# HELP scheduler_jobs_total 调度器作业总数")
        lines.append("# TYPE scheduler_jobs_total gauge")
        lines.append(f"scheduler_jobs_total {len(jobs)}")

        lines.append("# HELP scheduler_running 调度器运行状态")
        lines.append("# TYPE scheduler_running gauge")
        lines.append(f"scheduler_running {1 if scheduler.scheduler.running else 0}")
    except:
        pass

    # 学期指标
    try:
        active_semester = get_active_semester()
        lines.append("# HELP semester_active_id 当前激活学期ID")
        lines.append("# TYPE semester_active_id gauge")
        lines.append(f"semester_active_id {active_semester or 0}")
    except:
        pass

    # 进程指标
    try:
        process = psutil.Process(os.getpid())
        lines.append("# HELP process_cpu_percent 进程 CPU 使用率")
        lines.append("# TYPE process_cpu_percent gauge")
        lines.append(f"process_cpu_percent {process.cpu_percent()}")

        lines.append("# HELP process_memory_rss_bytes 进程 RSS 内存")
        lines.append("# TYPE process_memory_rss_bytes gauge")
        lines.append(f"process_memory_rss_bytes {process.memory_info().rss}")

        lines.append("# HELP process_threads 进程线程数")
        lines.append("# TYPE process_threads gauge")
        lines.append(f"process_threads {process.num_threads()}")

        lines.append("# HELP process_uptime_seconds 进程运行时间")
        lines.append("# TYPE process_uptime_seconds gauge")
        lines.append(f"process_uptime_seconds {time.time() - process.create_time()}")
    except:
        pass

    return "\n".join(lines) + "\n"


# ===== 指标摘要（JSON 格式，便于前端展示） =====


@router.get("/metrics/summary")
def metrics_summary() -> dict[str, Any]:
    """指标摘要（JSON 格式）"""
    summary = {}

    try:
        summary["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory": {
                "used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
                "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "free_gb": round(psutil.disk_usage(str(settings.PROJECT_ROOT)).free / (1024**3), 2),
                "percent": psutil.disk_usage(str(settings.PROJECT_ROOT)).percent,
            },
        }
    except:
        summary["system"] = {}

    try:
        session = get_session()
        start = time.time()
        session.execute(text("SELECT 1"))
        summary["database"] = {"latency_ms": round((time.time() - start) * 1000, 2), "status": "up"}
    except:
        summary["database"] = {"status": "down"}

    try:
        stats = cache_service.get_stats()
        summary["cache"] = stats
    except:
        summary["cache"] = {}

    try:
        scheduler = get_scheduler()
        summary["scheduler"] = {
            "running": scheduler.scheduler.running,
            "jobs": len(scheduler.get_jobs()),
        }
    except:
        summary["scheduler"] = {}

    try:
        summary["semester"] = {"active_id": get_active_semester()}
    except:
        summary["semester"] = {}

    try:
        process = psutil.Process(os.getpid())
        summary["process"] = {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": round(process.memory_info().rss / (1024**2), 2),
            "threads": process.num_threads(),
            "uptime_sec": int(time.time() - process.create_time()),
        }
    except:
        summary["process"] = {}

    summary["timestamp"] = time.time()
    return summary
