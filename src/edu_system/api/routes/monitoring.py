"""M3：系统监控 API（对齐若依 #15 服务监控：CPU/内存/磁盘/JVM）

psutil 采集系统资源 + 缓存统计（服务注册/审计数）。
"""

from __future__ import annotations

import time
from datetime import datetime

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from edu_system.api.deps import get_db, require_permission
from edu_system.core.permissions import Permission

router = APIRouter(tags=["系统监控"])


@router.get("/monitor/server")
def server_stats(
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.SYSTEM_ADMIN)),
):
    """系统资源监控（对齐若依 Server 监控）"""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot_time = psutil.boot_time()
    cpu_count = psutil.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=0.1)
    return {
        "hostname": __import__("socket").gethostname(),
        "os": f"{psutil.linux_distribution(fullver=False) if hasattr(psutil, 'linux_distribution') else 'Linux'}",
        "cpu": {
            "model": _cpu_model(),
            "cores": cpu_count,
            "usage_percent": round(cpu_percent, 1),
        },
        "memory": {
            "total": mem.total,
            "used": mem.used,
            "free": mem.available,
            "usage_percent": round(mem.percent, 1),
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "usage_percent": round(disk.percent, 1),
        },
        "boot_time": datetime.fromtimestamp(boot_time).isoformat() if boot_time else None,
        "load_avg": psutil.getloadavg() if hasattr(psutil, "getloadavg") else None,
        "processes": len(psutil.pids()),
    }


@router.get("/monitor/cache")
def cache_stats(
    _user=Depends(require_permission(Permission.SYSTEM_ADMIN)),
):
    """缓存/底座统计（对齐若依 Redis 监控的轻量版）"""
    from edu_system.api.service_registry import service_registry

    svc_total = 0
    svc_enabled = 0
    try:
        svc_total = len(service_registry._services)
        svc_enabled = sum(1 for s in service_registry._services.values() if s.get("enabled"))
    except Exception:
        pass
    return {
        "services": {"total": svc_total, "enabled": svc_enabled},
        "uptime_seconds": time.time() - psutil.boot_time(),
        "timestamp": datetime.now().isoformat(),
    }


def _cpu_model() -> str:
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line:
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return ""
