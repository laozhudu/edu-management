#!/usr/bin/env python3
"""
定时任务调度器
基于 APScheduler + SQLiteJobStore，嵌入 PyQt5 QThread
支持：统计刷新、自动锁分、自动归档、备份、审计清理
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import atexit
import logging
from datetime import datetime

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_MISSED
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from edu_system.database import get_session, init_db_with_defaults
from edu_system.services.locks import DataLockService
from edu_system.services.statistics import StatisticsService
from scripts.archive_semester import SemesterArchiver
from scripts.audit_cleaner import AuditCleaner
from scripts.backup import BackupManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchedulerService:
    """定时任务调度器服务"""

    def __init__(self, db_url: str = "sqlite:///data/scheduler_jobs.sqlite"):
        self.db_url = db_url
        self.scheduler = None
        self._init_scheduler()

    def _init_scheduler(self):
        """初始化调度器"""
        jobstores = {"default": SQLAlchemyJobStore(url=self.db_url)}
        executors = {
            "default": ThreadPoolExecutor(5),
        }
        job_defaults = {
            "coalesce": False,
            "max_instances": 1,
            "misfire_grace_time": 300,  # 5分钟容错
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="Asia/Shanghai",
        )

        # 添加事件监听
        self.scheduler.add_listener(
            self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )

    def _job_listener(self, event):
        """作业事件监听"""
        if event.exception:
            logger.error(f"作业失败: {event.job_id} - {event.exception}")
        elif event.code == EVENT_JOB_MISSED:
            logger.warning(f"作业错过执行: {event.job_id}")
        else:
            logger.info(f"作业完成: {event.job_id}")

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("调度器已启动")
            # 注册关闭钩子
            atexit.register(self.shutdown)

    def shutdown(self, wait=True):
        """关闭调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("调度器已关闭")

    def add_job(self, func, trigger, **kwargs):
        """添加作业"""
        return self.scheduler.add_job(func, trigger, **kwargs)

    def remove_job(self, job_id: str):
        """移除作业"""
        try:
            self.scheduler.remove_job(job_id)
            return True
        except:
            return False

    def get_jobs(self):
        """获取所有作业"""
        jobs = []
        for job in self.scheduler.get_jobs():
            next_run = None
            try:
                # APScheduler 3.x: next_run_time 是属性
                if hasattr(job, "next_run_time") and job.next_run_time:
                    next_run = job.next_run_time.isoformat()
            except:
                pass
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": next_run,
                    "trigger": str(job.trigger),
                    "func": job.func.__name__ if job.func else None,
                }
            )
        return jobs

    def pause_job(self, job_id: str):
        """暂停作业"""
        self.scheduler.pause_job(job_id)

    def resume_job(self, job_id: str):
        """恢复作业"""
        self.scheduler.resume_job(job_id)

    def trigger_job(self, job_id: str):
        """手动触发作业"""
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now())
            return True
        return False


# ===== 内置作业函数 =====


def job_statistics_refresh():
    """统计增量刷新（每 5 分钟）"""
    logger.info("执行统计增量刷新...")
    from edu_system.services.cache import invalidate_stats_cache

    session = get_session()
    service = StatisticsService(session)
    # 这里简化：实际应根据脏位增量更新
    # service.incremental_recompute(dirty_entities)
    invalidate_stats_cache()
    logger.info("统计缓存已失效，下次查询将重新计算")


def job_auto_lock_scores():
    """自动锁定成绩（成绩发布后触发，此处简化为定时检查）"""
    logger.info("检查需自动锁定的成绩...")
    from edu_system.models import Exam
    from edu_system.services.locks import LockLevel

    session = get_session()
    lock_svc = DataLockService(session)

    # 查找已发布但未锁定的考试
    exams = session.query(Exam).filter(Exam.is_published).all()  # 假设有此字段

    for exam in exams:
        # 检查是否已锁定
        existing = lock_svc.get_lock(exam.semester_id, "exam_scores", exam.id)
        if not existing:
            lock_svc.lock(
                semester_id=exam.semester_id,
                entity_type="exam_scores",
                entity_id=exam.id,
                lock_level=LockLevel.HARD,
                locked_by="system_auto",
                reason=f'考试 "{exam.name}" 成绩已发布，自动硬锁',
            )
            logger.info(f"已自动锁定考试成绩: {exam.name}")


def job_backup_daily():
    """每日备份（02:00）"""
    logger.info("执行每日增量备份...")
    from edu_system.database import get_session

    session = get_session()
    db_path = Path("项目根目录/data/school_data.db")
    backup_root = Path("项目根目录/backups")

    manager = BackupManager(db_path, backup_root, verbose=True)
    manager.daily_incremental()


def job_archive_semester_end():
    """学期末自动归档"""
    logger.info("检查需归档的学期...")
    from edu_system.models import Semester, SemesterStatus

    session = get_session()
    # 查找状态为 locked 且结束日期已过的学期
    semesters = (
        session.query(Semester)
        .filter(
            Semester.status == SemesterStatus.locked,
            Semester.end_date.isnot(None),
            Semester.end_date < datetime.now().date(),
        )
        .all()
    )

    for sem in semesters:
        logger.info(f"归档学期: {sem.label}")
        archiver = SemesterArchiver(
            Path("项目根目录/data/school_data.db"),
            Path("项目根目录/archives"),
            verbose=True,
        )
        archiver.archive_semester(sem.id)


def job_audit_cleanup():
    """审计清理（周日）"""
    logger.info("执行审计日志月度归档...")

    db_path = Path("项目根目录/data/school_data.db")
    archive_root = Path("项目根目录/archives/audit")

    cleaner = AuditCleaner(db_path, archive_root, verbose=True)
    cleaner.run_monthly_archive()


# ===== 作业注册函数 =====


def register_default_jobs(scheduler_service: SchedulerService):
    """注册默认作业"""

    # 1. 统计增量刷新 - 每 5 分钟
    scheduler_service.add_job(
        job_statistics_refresh,
        "interval",
        minutes=5,
        id="statistics_refresh",
        name="统计增量刷新",
        replace_existing=True,
    )

    # 2. 自动锁定成绩 - 每 10 分钟检查
    scheduler_service.add_job(
        job_auto_lock_scores,
        "interval",
        minutes=10,
        id="auto_lock_scores",
        name="自动锁定成绩",
        replace_existing=True,
    )

    # 3. 每日备份 - 每天 02:00
    scheduler_service.add_job(
        job_backup_daily,
        "cron",
        hour=2,
        minute=0,
        id="backup_daily",
        name="每日增量备份",
        replace_existing=True,
    )

    # 4. 学期末自动归档 - 每天 03:00 检查
    scheduler_service.add_job(
        job_archive_semester_end,
        "cron",
        hour=3,
        minute=0,
        id="archive_semester_end",
        name="学期末自动归档",
        replace_existing=True,
    )

    # 5. 审计清理 - 每周日 04:00
    scheduler_service.add_job(
        job_audit_cleanup,
        "cron",
        day_of_week="sun",
        hour=4,
        minute=0,
        id="audit_cleanup",
        name="审计日志月度归档",
        replace_existing=True,
    )

    logger.info("默认作业已注册")


# ===== 单例 =====

_scheduler_instance = None


def get_scheduler() -> SchedulerService:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SchedulerService()
        register_default_jobs(_scheduler_instance)
    return _scheduler_instance


if __name__ == "__main__":
    import time

    init_db_with_defaults()

    scheduler = get_scheduler()
    scheduler.start()

    print("调度器运行中... 按 Ctrl+C 停止")
    try:
        while True:
            time.sleep(60)
            jobs = scheduler.get_jobs()
            for job in jobs:
                print(f"  {job['id']}: 下次运行 {job['next_run_time']}")
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("调度器已停止")
