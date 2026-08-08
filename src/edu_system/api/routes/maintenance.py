"""
数据维护 API 路由（P3-B：备份/清理/列表）

- POST /maintenance/backup: 立即执行每日增量备份
- GET /maintenance/backups: 备份文件列表
- POST /maintenance/clean/cache: 清理统计缓存
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.models import User

router = APIRouter(prefix="/maintenance", tags=["数据维护"])


def _backup_manager() -> "object":
    """构造 BackupManager（延迟导入避免循环依赖）"""
    from edu_system.config import DB_PATH
    from scripts.backup import BackupManager

    db_path = Path(DB_PATH)
    backup_root = Path("backups")
    return BackupManager(db_path, backup_root, verbose=False)


@router.post("/backup")
def run_backup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """立即执行每日增量备份"""
    try:
        manager = _backup_manager()
        result = manager.daily_incremental()
        return {"ok": True, "message": "备份完成", "result": str(result)[:200]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"备份失败: {e}")


@router.get("/backups")
def list_backups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """备份文件列表（按时间倒序）"""

    manager = _backup_manager()
    items = []
    for d in sorted(manager.daily_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
        if d.is_dir():
            files = [f.name for f in d.glob("*") if f.is_file()]
            items.append(
                {
                    "name": d.name,
                    "created": d.stat().st_mtime,
                    "file_count": len(files),
                    "files": files[:10],
                }
            )
    return {"items": items[:20], "total": len(items)}


@router.post("/clean/cache")
def clean_cache(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清理统计缓存"""
    try:
        from edu_system.services.cache import invalidate_stats_cache

        invalidate_stats_cache()
        return {"ok": True, "message": "统计缓存已清理"}
    except Exception:
        # 无独立缓存服务时，尝试清 SQLAlchemy 会话缓存
        db.expire_all()
        return {"ok": True, "message": "会话缓存已清理"}
