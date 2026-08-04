"""
定时任务管理 API
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from edu_system.services.scheduler import SchedulerService, get_scheduler

router = APIRouter(prefix="/api/admin/scheduler", tags=["定时任务管理"])


class JobCreateRequest(BaseModel):
    id: str
    name: str
    func: str  # 函数名，需在允许列表中
    trigger: str  # interval/cron/date
    trigger_args: dict[str, Any] = {}


class JobResponse(BaseModel):
    id: str
    name: str
    next_run_time: str | None
    trigger: str
    func: str


# 允许的作业函数映射（安全：仅允许白名单函数）
ALLOWED_JOBS = {
    "statistics_refresh": "edu_system.services.scheduler.job_statistics_refresh",
    "auto_lock_scores": "edu_system.services.scheduler.job_auto_lock_scores",
    "backup_daily": "edu_system.services.scheduler.job_backup_daily",
    "archive_semester_end": "edu_system.services.scheduler.job_archive_semester_end",
    "audit_cleanup": "edu_system.services.scheduler.job_audit_cleanup",
}


def get_scheduler_service() -> SchedulerService:
    return get_scheduler()


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(scheduler: SchedulerService = Depends(get_scheduler_service)):
    """获取所有作业列表"""
    jobs = scheduler.get_jobs()
    return jobs


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, scheduler: SchedulerService = Depends(get_scheduler_service)):
    """获取单个作业详情"""
    job = scheduler.scheduler.get_job(job_id)
    if not job:
        raise HTTPException(404, f"作业不存在: {job_id}")
    return {
        "id": job.id,
        "name": job.name,
        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        "trigger": str(job.trigger),
        "func": job.func.__name__ if job.func else None,
    }


@router.post("/jobs", response_model=JobResponse)
def create_job(req: JobCreateRequest, scheduler: SchedulerService = Depends(get_scheduler_service)):
    """创建新作业"""
    if req.func not in ALLOWED_JOBS:
        raise HTTPException(400, f"不允许的作业函数: {req.func}")

    # 动态导入函数
    module_path, func_name = ALLOWED_JOBS[req.func].rsplit(".", 1)
    module = __import__(module_path, fromlist=[func_name])
    func = getattr(module, func_name)

    # 添加作业
    if req.trigger == "interval":
        job = scheduler.add_job(func, "interval", **req.trigger_args, id=req.id, name=req.name)
    elif req.trigger == "cron":
        job = scheduler.add_job(func, "cron", **req.trigger_args, id=req.id, name=req.name)
    elif req.trigger == "date":
        job = scheduler.add_job(func, "date", **req.trigger_args, id=req.id, name=req.name)
    else:
        raise HTTPException(400, f"不支持的触发器类型: {req.trigger}")

    return {
        "id": job.id,
        "name": job.name,
        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        "trigger": str(job.trigger),
        "func": func.__name__,
    }


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, scheduler: SchedulerService = Depends(get_scheduler_service)):
    """删除作业"""
    if not scheduler.remove_job(job_id):
        raise HTTPException(404, f"作业不存在: {job_id}")
    return {"message": f"作业已删除: {job_id}"}


@router.post("/jobs/{job_id}/pause")
def pause_job(job_id: str, scheduler: SchedulerService = Depends(get_scheduler_service)):
    """暂停作业"""
    try:
        scheduler.pause_job(job_id)
        return {"message": f"作业已暂停: {job_id}"}
    except Exception:
        raise HTTPException(404, f"作业不存在: {job_id}")


@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: str, scheduler: SchedulerService = Depends(get_scheduler_service)):
    """恢复作业"""
    try:
        scheduler.resume_job(job_id)
        return {"message": f"作业已恢复: {job_id}"}
    except Exception:
        raise HTTPException(404, f"作业不存在: {job_id}")


@router.post("/jobs/{job_id}/trigger")
def trigger_job(job_id: str, scheduler: SchedulerService = Depends(get_scheduler_service)):
    """手动触发作业"""
    if not scheduler.trigger_job(job_id):
        raise HTTPException(404, f"作业不存在: {job_id}")
    return {"message": f"作业已触发: {job_id}"}


@router.get("/status")
def get_scheduler_status(scheduler: SchedulerService = Depends(get_scheduler_service)):
    """获取调度器状态"""
    return {
        "running": scheduler.scheduler.running,
        "job_count": len(scheduler.scheduler.get_jobs()),
        "timezone": str(scheduler.scheduler.timezone),
    }
