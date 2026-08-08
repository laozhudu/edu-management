"""
领域事件总线 - 解耦业务逻辑与副作用
使用方式：
    from core.events import EventBus, DomainEvent

    # 发布事件（在 Service 中）
    EventBus.publish(DomainEvent("student.transferred", {
        "student_id": student.id,
        "from_class_id": from_class_id,
        "to_class_id": to_class_id,
        "operator": operator
    }))

    # 订阅事件（在模块初始化时）
    EventBus.subscribe("student.transferred", handle_student_transferred)
"""

import threading
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DomainEvent:
    """领域事件"""

    event_type: str
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    version: int = 1


class EventBus:
    """轻量级进程内事件总线"""

    _handlers: dict[str, list[Callable]] = defaultdict(list)
    _lock = threading.RLock()
    _history: list[DomainEvent] = []  # 可选：保留最近 N 条用于调试

    @classmethod
    def subscribe(cls, event_type: str, handler: Callable[[DomainEvent], None]) -> None:
        """订阅事件类型"""
        with cls._lock:
            cls._handlers[event_type].append(handler)

    @classmethod
    def unsubscribe(cls, event_type: str, handler: Callable) -> None:
        """取消订阅"""
        with cls._lock:
            if handler in cls._handlers[event_type]:
                cls._handlers[event_type].remove(handler)

    @classmethod
    def publish(cls, event: DomainEvent) -> None:
        """发布事件（同步调用所有处理器）"""
        with cls._lock:
            handlers = cls._handlers.get(event.event_type, []).copy()
            cls._history.append(event)
            # 仅保留最近 1000 条
            if len(cls._history) > 1000:
                cls._history = cls._history[-1000:]

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # 记录错误但不阻塞其他 handler
                print(f"[EventBus] Handler error for {event.event_type}: {e}")

    @classmethod
    def publish_async(cls, event: DomainEvent) -> None:
        """异步发布（后台线程）"""
        import threading

        threading.Thread(target=cls.publish, args=(event,), daemon=True).start()

    @classmethod
    def get_history(cls, event_type: str | None = None, limit: int = 100) -> list[DomainEvent]:
        """获取事件历史（调试用）"""
        with cls._lock:
            events = cls._history
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            return events[-limit:]


# 预定义事件类型常量
class EventTypes:
    # 学生
    STUDENT_CREATED = "student.created"
    STUDENT_UPDATED = "student.updated"
    STUDENT_DELETED = "student.deleted"
    STUDENT_TRANSFERRED = "student.transferred"
    STUDENT_STATUS_CHANGED = "student.status_changed"

    # 成绩
    SCORE_CREATED = "score.created"
    SCORE_UPDATED = "score.updated"
    SCORE_PUBLISHED = "score.published"

    # 考试
    EXAM_CREATED = "exam.created"
    EXAM_PUBLISHED = "exam.published"

    # 学籍变动
    MOVEMENT_RECORDED = "movement.recorded"

    # 班级
    CLASS_CREATED = "class.created"
    CLASS_UPDATED = "class.updated"
