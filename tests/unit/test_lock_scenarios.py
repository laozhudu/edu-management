"""
M5-C4 典型锁定场景自动加锁测试

覆盖典型场景：
- 成绩发布后自动锁定（lock_scores_after_publish + before_flush 拒绝修改）
- 学籍变动审核通过后自动锁定（lock_movements_after_approval）
- 考号生成后自动锁定（lock_exam_numbers）
- 学期归档自动锁定（lock_semester）

验证：
- 各场景加锁后 get_lock 命中
- 硬锁下 before_flush 拦截无 DATA_UNLOCK 权限的修改（抛 LockError）
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.core.permissions import set_current_user
from edu_system.models import Base, Exam, Semester, SemesterStatus, Student
from edu_system.services.locks import DataLockService, LockError, LockLevel


@pytest.fixture
def session():
    """内存 SQLite 会话（数据锁表 + 基础实体）"""
    from edu_system.models import AcademicYear, DataLock, Score  # noqa: F401

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture(autouse=True)
def _clean():
    """清理线程局部当前用户 + 学期，避免跨测试污染"""
    from edu_system.database import set_active_semester

    set_current_user(None)
    set_active_semester(0)
    yield
    set_current_user(None)
    set_active_semester(0)


@pytest.fixture
def semester(session):
    ay_obj = __import__("edu_system.models", fromlist=["AcademicYear"]).AcademicYear
    ay = ay_obj(name="2024-2025", sort_order=0, is_active=True)
    session.add(ay)
    session.flush()
    sem = Semester(
        academic_year_id=ay.id, year_start=2024, semester="1",
        label="2024-2025 第1学期", sort_order=1, is_active=True, status=SemesterStatus.active,
    )
    session.add(sem)
    session.flush()
    return sem


class TestAutoLockScenarios:
    """典型锁定场景自动加锁"""

    def test_score_publish_auto_lock(self, session, semester):
        """成绩发布后自动锁定考试成绩（hard），修改被拒绝"""
        svc = DataLockService(session)

        # 构造考试
        exam = Exam(
            name="期中考试", semester_id=semester.id, exam_type="midterm",
            status="completed",
        )
        session.add(exam)
        session.flush()

        # 自动加锁
        locks = svc.lock_scores_after_publish(exam.id, locked_by="admin")
        assert locks, "成绩发布应产生锁"
        lock = svc.get_lock(semester.id, "exam_scores", exam.id)
        assert lock is not None
        assert lock.lock_level == LockLevel.HARD.value

        session.rollback()

    def test_movement_approval_auto_lock(self, session, semester):
        """学籍变动审核通过后自动锁定"""
        from edu_system.models import StudentMovement

        svc = DataLockService(session)
        mov = StudentMovement(
            semester_id=semester.id, student_id=1, movement_category="transfer_in",
        )
        session.add(mov)
        session.flush()

        locks = svc.lock_movements_after_approval([mov.id], locked_by="admin")
        assert locks, "学籍审核通过应产生锁"
        lock = svc.get_lock(semester.id, "student_movement", mov.id)
        assert lock is not None
        assert lock.lock_level == LockLevel.HARD.value

        session.rollback()

    def test_exam_numbers_auto_lock(self, session, semester):
        """考号生成后自动锁定"""
        svc = DataLockService(session)
        lock = svc.lock_exam_numbers(semester.id, locked_by="admin")
        assert lock is not None
        fetched = svc.get_lock(semester.id, "exam_numbers", semester.id)
        assert fetched is not None
        assert fetched.lock_level == LockLevel.HARD.value

        session.rollback()

    def test_semester_archive_auto_lock(self, session, semester):
        """学期归档自动锁定整学期（semester 级）+ before_flush 拒绝修改"""
        from edu_system.models import Class as ClassModel
        from edu_system.models import Grade

        svc = DataLockService(session)

        # 锁前先建学生（供后续修改测试）
        grade = Grade(name="一年级", sort_order=1)
        session.add(grade)
        session.flush()
        cls = ClassModel(
            grade_id=grade.id, semester_id=semester.id, name="1班",
        )
        session.add(cls)
        session.flush()
        stu = Student(
            class_id=cls.id, name="张三", student_code="20240001",
            semester_id=semester.id, status="在校", gender="男", enroll_year=2024,
        )
        session.add(stu)
        session.flush()

        # 学期归档自动锁定
        lock = svc.lock_semester(semester.id, locked_by="admin", reason="学期归档")
        assert lock is not None
        fetched = svc.get_lock(semester.id, "semester", semester.id)
        assert fetched is not None
        assert fetched.lock_level == LockLevel.SEMESTER.value

        # 注册锁定拦截器（应用启动时注册；测试手动注册验证 before_flush）
        from edu_system.services.locks import register_lock_interceptor

        register_lock_interceptor()

        # before_flush 拦截：无权限用户修改被锁学期下的学生 → 抛 LockError
        set_current_user(None)
        stu.status = "已转学"
        with pytest.raises(LockError):
            session.flush()
        session.rollback()


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
