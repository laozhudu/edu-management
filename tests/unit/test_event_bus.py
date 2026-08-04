"""
Outbox 事件总线单元测试
验证：事件发布、批量发布、处理、重试、死信
"""

import uuid

import pytest

from edu_system.core.event_bus import DomainEvent, EventBus, EventTypes
from edu_system.models import OutboxEvent


@pytest.fixture
def bus():
    """创建独立事件总线实例"""
    return EventBus()


def test_publish_event(bus, db_session):
    """发布事件应写入 outbox 表"""
    unique_type = f"test.publish.{uuid.uuid4()}"
    event = DomainEvent(
        event_type=unique_type,
        aggregate_id="1001",
        payload={"name": "张三"},
    )
    bus.publish(event, session=db_session)
    db_session.commit()

    from edu_system.database import get_session

    session = get_session()
    try:
        records = session.query(OutboxEvent).filter_by(event_type=unique_type).all()
        assert len(records) == 1
        assert records[0].aggregate_id == "1001"
    finally:
        session.close()


def test_publish_batch(bus, db_session):
    """批量发布事件"""
    unique_type = f"test.batch.{uuid.uuid4()}"
    events = [
        DomainEvent(
            event_type=unique_type,
            aggregate_id=f"id-{uuid.uuid4()}",
            payload={"n": i},
        )
        for i in range(3)
    ]
    bus.publish_batch(events, session=db_session)
    db_session.commit()

    from edu_system.database import get_session

    session = get_session()
    try:
        records = session.query(OutboxEvent).filter_by(event_type=unique_type).count()
        assert records == 3
    finally:
        session.close()


def test_process_outbox_with_handler(bus, db_session):
    """注册处理器后，处理 outbox 应调用处理器并标记已处理"""
    received = []
    unique_type = f"test.handled.{uuid.uuid4()}"

    def handler(payload):
        received.append(payload)

    bus.register(unique_type, handler)

    bus.publish(
        DomainEvent(event_type=unique_type, aggregate_id="1", payload={"k": "v"}),
        session=db_session,
    )
    db_session.commit()

    processed = bus.process_outbox()
    assert processed >= 1
    assert received == [{"k": "v"}]

    # 再次处理应无新事件
    processed_again = bus.process_outbox()
    assert processed_again == 0


def test_process_outbox_retry_and_dead_letter(bus, db_session):
    """处理失败应重试，超过 3 次进入死信"""
    call_count = {"n": 0}
    unique_type = f"test.failing.{uuid.uuid4()}"

    def failing_handler(payload):
        call_count["n"] += 1
        raise RuntimeError("模拟失败")

    bus.register(unique_type, failing_handler)

    bus.publish(
        DomainEvent(event_type=unique_type, aggregate_id="1", payload={}),
        session=db_session,
    )
    db_session.commit()

    # 第一次处理失败 -> retry_count=1
    bus.process_outbox()
    # 第二次 -> 2
    bus.process_outbox()
    # 第三次 -> 3，进入死信
    bus.process_outbox()
    # 第四次：死信事件不再被处理
    bus.process_outbox()

    assert call_count["n"] >= 3

    dead = bus.get_dead_letters()
    assert any(e.event_type == unique_type for e in dead)


def test_event_types_constants():
    """事件类型常量应定义完整"""
    assert EventTypes.STUDENT_CREATED == "student.created"
    assert EventTypes.SCORE_PUBLISHED == "score.published"
    assert EventTypes.ATTENDANCE_RECORDED == "attendance.recorded"
    assert EventTypes.DATA_LOCKED == "data.locked"
