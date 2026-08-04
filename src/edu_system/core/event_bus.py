"""
Outbox 事件总线
- outbox_events 表持久化事件
- APScheduler 定时轮询（每 10 秒）
- 重试 3 次，失败标记死信
- 复用现有 UnitOfWork + APScheduler
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from edu_system.database import get_session
from edu_system.models import OutboxEvent


@dataclass
class DomainEvent:
    """领域事件"""

    event_type: str
    aggregate_id: str
    payload: dict
    trace_id: str = ""


class EventBus:
    """事件总线：发布 + 消费"""

    def __init__(self):
        self._handlers: dict[str, list[Callable[[dict], None]]] = {}

    def register(self, event_type: str, handler: Callable[[dict], None]):
        """注册事件处理器"""
        self._handlers.setdefault(event_type, []).append(handler)

    def unregister(self, event_type: str, handler: Callable[[dict], None]):
        """注销事件处理器"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    def publish(self, event: DomainEvent, session: Session | None = None):
        """
        发布事件到 Outbox 表
        如果传入 session，使用该事务；否则创建新事务
        """
        close_session = False
        if session is None:
            session = get_session()
            close_session = True

        try:
            outbox = OutboxEvent(
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
                payload=json.dumps(event.payload, ensure_ascii=False),
                trace_id=event.trace_id or "",
            )
            session.add(outbox)
            if close_session:
                session.commit()
        finally:
            if close_session:
                session.close()

    def publish_batch(self, events: list[DomainEvent], session: Session | None = None):
        """批量发布事件"""
        close_session = False
        if session is None:
            session = get_session()
            close_session = True

        try:
            outbox_events = [
                OutboxEvent(
                    event_type=e.event_type,
                    aggregate_id=e.aggregate_id,
                    payload=json.dumps(e.payload, ensure_ascii=False),
                    trace_id=e.trace_id or "",
                )
                for e in events
            ]
            session.add_all(outbox_events)
            if close_session:
                session.commit()
        finally:
            if close_session:
                session.close()

    def process_outbox(self, batch_size: int = 50):
        """
        处理 Outbox 事件（APScheduler 定时调用，每 10 秒）
        """
        session = get_session()
        try:
            # 查询未处理、非死信事件
            events = (
                session.query(OutboxEvent)
                .filter(OutboxEvent.processed_at.is_(None), OutboxEvent.dead_letter.is_(False))
                .order_by(OutboxEvent.created_at)
                .limit(batch_size)
                .all()
            )

            if not events:
                return 0

            processed = 0
            for event in events:
                try:
                    handlers = self._handlers.get(event.event_type, [])
                    if not handlers:
                        # 无处理器，标记已处理
                        event.processed_at = datetime.utcnow()
                        processed += 1
                        continue

                    payload = json.loads(event.payload)
                    for handler in handlers:
                        handler(payload)

                    event.processed_at = datetime.utcnow()
                    processed += 1

                except Exception:
                    event.retry_count += 1
                    if event.retry_count >= 3:
                        event.dead_letter = True

            session.commit()
            return processed
        finally:
            session.close()

    def get_dead_letters(self, limit: int = 100) -> list:
        """获取死信事件"""
        session = get_session()
        try:
            return (
                session.query(OutboxEvent)
                .filter(OutboxEvent.dead_letter.is_(True))
                .order_by(OutboxEvent.created_at.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    def retry_dead_letter(self, event_id: int) -> bool:
        """重试死信事件"""
        session = get_session()
        try:
            event = session.query(OutboxEvent).filter_by(id=event_id).first()
            if event and event.dead_letter:
                event.dead_letter = False
                event.retry_count = 0
                event.processed_at = None
                session.commit()
                return True
            return False
        finally:
            session.close()


# 全局实例
event_bus = EventBus()


# APScheduler 注册函数
def register_outbox_job(scheduler, interval_seconds: int = 10):
    """注册 Outbox 处理定时任务"""
    scheduler.add_job(
        event_bus.process_outbox,
        "interval",
        seconds=interval_seconds,
        id="process_outbox",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


# 便捷函数：发布领域事件（自动获取 trace_id）
def publish_event(event_type: str, aggregate_id: str, payload: dict, trace_id: str = ""):
    """便捷发布函数"""
    from edu_system.core.context import get_trace_id

    event = DomainEvent(
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload,
        trace_id=trace_id or get_trace_id(),
    )
    event_bus.publish(event)


# 常用事件类型常量
class EventTypes:
    # 学生相关
    STUDENT_CREATED = "student.created"
    STUDENT_UPDATED = "student.updated"
    STUDENT_DELETED = "student.deleted"
    STUDENT_MOVED = "student.moved"

    # 成绩相关
    SCORE_CREATED = "score.created"
    SCORE_UPDATED = "score.updated"
    SCORE_DELETED = "score.deleted"
    SCORE_PUBLISHED = "score.published"
    SCORE_LOCKED = "score.locked"

    # 考试相关
    EXAM_CREATED = "exam.created"
    EXAM_UPDATED = "exam.updated"
    EXAM_SCHEDULED = "exam.scheduled"

    # 考勤相关
    ATTENDANCE_RECORDED = "attendance.recorded"
    ATTENDANCE_BATCH = "attendance.batch"

    # 学籍变动
    ENROLLMENT_CHANGED = "enrollment.changed"
    PROMOTION_COMPLETED = "promotion.completed"

    # 配置/锁定
    CONFIG_CHANGED = "config.changed"
    DATA_LOCKED = "data.locked"
    DATA_UNLOCKED = "data.unlocked"

    # 统计/报表
    STATS_DIRTY = "stats.dirty"
    REPORT_GENERATED = "report.generated"

    # 打印/证书
    CERTIFICATE_GENERATED = "certificate.generated"
    BATCH_PRINT_STARTED = "batch_print.started"
