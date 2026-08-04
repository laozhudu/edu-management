"""
StatisticsWorker 后台 Worker 测试（M5-B3）

覆盖：
- run_full_recompute: 全量重算进度回调递增 + 完成回调
- run_incremental_recompute: 增量重算进度回调 + 完成回调
- 取消语义：cancel_check 返回 True 时提前终止
- 空脏实体列表安全
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.models import Base, Semester, Student
from edu_system.services.statistics import (
    run_full_recompute,
    run_incremental_recompute,
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


class TestFullRecompute:
    """全量重算：进度 + 完成"""

    def test_progress_monotonic_and_finished(self, session, test_data):
        """进度回调单调递增，最后触发完成回调"""
        sem = test_data["sem"]
        from edu_system.database import set_active_semester

        set_active_semester(sem.id)

        progress_steps = []
        finished = []

        ok = run_full_recompute(
            session,
            progress_cb=lambda p, m: progress_steps.append((p, m)),
            finished_cb=finished.append,
        )

        assert ok is True
        assert finished == ["全量重算完成"]
        assert len(progress_steps) >= 2  # 至少 开始 + 完成
        # 进度单调不减
        percents = [p for p, _ in progress_steps]
        assert percents == sorted(percents), f"进度应单调, got {percents}"
        assert percents[-1] == 100

    def test_cancel_before_start(self, session, test_data):
        """cancel_check 立即返回 True → 提前终止，不触发完成"""
        sem = test_data["sem"]
        from edu_system.database import set_active_semester

        set_active_semester(sem.id)

        finished = []

        ok = run_full_recompute(
            session,
            finished_cb=finished.append,
            cancel_check=lambda: True,
        )

        assert ok is False
        assert finished == []


class TestIncrementalRecompute:
    """增量重算：进度 + 取消"""

    def test_progress_and_finished(self, session, test_data):
        """增量重算逐项进度，最后触发完成回调"""
        sem = test_data["sem"]
        stu = test_data["stu"]

        progress_steps = []
        finished = []

        ok = run_incremental_recompute(
            session,
            [
                {"entity_type": "student", "entity_id": stu.id, "exam_id": None},
                {"entity_type": "school", "entity_id": 0, "exam_id": None},
            ],
            progress_cb=lambda p, m: progress_steps.append((p, m)),
            finished_cb=finished.append,
        )

        assert ok is True
        assert finished == ["增量重算完成: 2 项"]
        assert len(progress_steps) == 2
        assert progress_steps[0][0] == 50
        assert progress_steps[1][0] == 100

    def test_cancel_midway(self, session, test_data):
        """cancel_check 中途返回 True → 停止剩余项，不触发完成"""
        sem = test_data["sem"]
        stu = test_data["stu"]

        progress_steps = []
        finished = []
        calls = {"n": 0}

        def cancel_check():
            calls["n"] += 1
            return calls["n"] >= 2  # 第二项前取消

        ok = run_incremental_recompute(
            session,
            [
                {"entity_type": "student", "entity_id": stu.id, "exam_id": None},
                {"entity_type": "school", "entity_id": 0, "exam_id": None},
                {"entity_type": "school", "entity_id": 0, "exam_id": None},
            ],
            progress_cb=lambda p, m: progress_steps.append((p, m)),
            finished_cb=finished.append,
            cancel_check=cancel_check,
        )

        assert ok is False
        assert finished == []
        assert len(progress_steps) == 1  # 只处理了第一项

    def test_empty_dirty_list_safe(self, session, test_data):
        """空脏实体列表：安全返回完成"""
        sem = test_data["sem"]
        finished = []

        ok = run_incremental_recompute(
            session,
            [],
            finished_cb=finished.append,
        )

        assert ok is True
        assert finished == ["增量重算完成: 0 项"]


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
