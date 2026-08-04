"""
StatisticsService 事件驱动增量刷新测试（M5-B2）

覆盖：
- mark_stats_dirty: 数据变更后发布 stats.dirty 事件（Outbox 持久化）
- 非法实体类型拒绝入队
- handle_stats_dirty: 消费事件 → 增量重算脏实体 → 缓存版本递增
- register_stats_dirty_handler: 注册处理器到事件总线
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.models import Base, OutboxEvent, Semester, Student
from edu_system.services.statistics import (
    StatisticsService,
    handle_stats_dirty,
    mark_stats_dirty,
    register_stats_dirty_handler,
)


@pytest.fixture
def session():
    """内存 SQLite 会话（含完整测试数据链）"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture(autouse=True)
def _clean_semester():
    """每个测试前清理线程局部学期，防止被测试数据集加载器/其他测试污染"""
    from edu_system.database import set_active_semester

    set_active_semester(0)
    yield
    set_active_semester(0)


@pytest.fixture
def test_data(session):
    """构造最小测试数据：学期 + 学生"""
    from edu_system.models import AcademicYear

    ay = AcademicYear(name="2024-2025", sort_order=0, is_active=True)
    session.add(ay)
    session.flush()

    sem = Semester(
        academic_year_id=ay.id,
        year_start=2024,
        semester="1",
        label="2024-2025 第1学期",
        sort_order=1,
        is_active=True,
        status="active",
    )
    session.add(sem)
    session.flush()

    stu = Student(name="张三", gender="男", class_id=0, semester_id=sem.id, status="在校")
    session.add(stu)
    session.flush()

    return {"sem": sem, "stu": stu}


class TestMarkStatsDirty:
    """数据变更后标记统计缓存脏"""

    def test_publish_event_written_to_outbox(self, session, test_data):
        """发布事件写入 Outbox 表（事务内持久化）"""
        sem = test_data["sem"]
        stu = test_data["stu"]

        ok = mark_stats_dirty(session, "student", stu.id, semester_id=sem.id)
        session.commit()

        assert ok is True
        events = session.query(OutboxEvent).all()
        assert len(events) == 1
        assert events[0].event_type == "stats.dirty"
        assert events[0].aggregate_id == f"student:{stu.id}"

    def test_invalid_entity_type_rejected(self, session):
        """非法实体类型拒绝入队（返回 False 且不写 Outbox）"""
        ok = mark_stats_dirty(session, "not_a_entity", 1)
        session.commit()

        assert ok is False
        assert session.query(OutboxEvent).count() == 0

    def test_payload_contains_exam_id(self, session, test_data):
        """考试变更时 payload 携带 exam_id"""
        sem = test_data["sem"]

        ok = mark_stats_dirty(session, "exam", 5, semester_id=sem.id, exam_id=5)
        session.commit()

        assert ok is True
        event = session.query(OutboxEvent).first()
        import json

        payload = json.loads(event.payload)
        assert payload["entity_type"] == "exam"
        assert payload["entity_id"] == 5
        assert payload["exam_id"] == 5
        assert payload["semester_id"] == sem.id


class TestHandleStatsDirty:
    """消费 stats.dirty 事件 → 增量重算"""

    def test_handler_recomputes_and_bumps_version(self, session, test_data):
        """处理器重算脏实体，缓存版本递增"""
        sem = test_data["sem"]
        stu = test_data["stu"]

        # 先全量重算（版本 1）
        svc = StatisticsService(session)
        svc.set_semester(sem.id)
        svc.full_recompute()
        session.commit()

        from edu_system.models import SemesterStatsCache

        v1 = (
            session.query(SemesterStatsCache.version)
            .filter(SemesterStatsCache.semester_id == sem.id)
            .first()
        )
        assert v1 is not None

        # 模拟学生变更：mark 脏 → 处理器消费
        mark_stats_dirty(session, "student", stu.id, semester_id=sem.id)
        session.commit()

        from edu_system.models import OutboxEvent

        event = session.query(OutboxEvent).first()
        import json

        handle_stats_dirty(json.loads(event.payload), session=session)

        # 新会话验证版本递增
        s2 = sessionmaker(bind=session.get_bind())()
        try:
            from edu_system.models import SemesterStatsCache

            versions = set(v for (v,) in s2.query(SemesterStatsCache.version).all())
            assert max(versions) > 1, f"缓存版本应递增, got {versions}"
        finally:
            s2.close()

    def test_invalid_payload_noop(self, session):
        """非法 payload 处理器安全跳过（不抛异常）"""
        handle_stats_dirty({"entity_type": "student", "entity_id": None})
        handle_stats_dirty({})
        handle_stats_dirty({"entity_type": "bogus", "entity_id": 1})
        # 到达此处即无异常

    def test_register_handler_to_event_bus(self):
        """注册处理器后事件总线可路由 stats.dirty"""
        from edu_system.core.event_bus import event_bus

        # 清掉可能已注册的同名处理器，保证幂等断言
        for handler in list(event_bus._handlers.get("stats.dirty", [])):
            event_bus.unregister("stats.dirty", handler)

        register_stats_dirty_handler()
        handlers = event_bus._handlers.get("stats.dirty", [])
        assert any(h.__name__ == "handle_stats_dirty" for h in handlers)


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
