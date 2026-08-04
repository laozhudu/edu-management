"""
学籍变动分类测试（Sprint 3.7.4）
覆盖：分类映射、create_movement 自动分类、按分类查询
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.models import Base, Student
from edu_system.repository.movement import MovementRepository, normalize_category


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture
def repo(session):
    return MovementRepository(session)


def _student(session):
    st = Student(name="张三", class_id=0, semester_id=0)
    session.add(st)
    session.commit()
    return st.id


class TestNormalizeCategory:
    def test_all_categories(self):
        assert normalize_category("升级") == "upgrade"
        assert normalize_category("留级") == "retain"
        assert normalize_category("转班") == "transfer"
        assert normalize_category("休学") == "suspend"
        assert normalize_category("复学") == "resume"
        assert normalize_category("转入") == "transfer_in"
        assert normalize_category("转出") == "transfer_out"
        assert normalize_category("毕业") == "graduate"
        assert normalize_category("升学") == "upgrade"

    def test_unknown_type(self):
        assert normalize_category("未知类型") == ""


class TestCreateMovement:
    def test_create_with_category(self, session, repo):
        sid = _student(session)
        mv = repo.create_movement(
            student_id=sid,
            semester_id=1,
            move_type="转班",
            from_class_id=1,
            to_class_id=2,
            reason="家庭搬迁",
        )
        assert mv.movement_category == "transfer"
        assert mv.from_class_id == 1
        assert mv.to_class_id == 2
        assert mv.reason == "家庭搬迁"
        assert mv.move_date is not None

    def test_create_default_move_date(self, session, repo):
        from datetime import date

        sid = _student(session)
        mv = repo.create_movement(student_id=sid, semester_id=1, move_type="休学")
        assert mv.move_date == date.today()

    def test_create_unknown_type_empty_category(self, session, repo):
        sid = _student(session)
        mv = repo.create_movement(student_id=sid, semester_id=1, move_type="自定义")
        assert mv.movement_category == ""


class TestListByCategory:
    def test_list_by_category(self, session, repo):
        sid = _student(session)
        repo.create_movement(student_id=sid, semester_id=1, move_type="升级")
        repo.create_movement(student_id=sid, semester_id=1, move_type="转班")
        repo.create_movement(student_id=sid, semester_id=1, move_type="升级")

        upgrades = repo.list_by_category("upgrade")
        assert len(upgrades) == 2
        transfers = repo.list_by_category("transfer")
        assert len(transfers) == 1

    def test_list_by_category_empty(self, session, repo):
        sid = _student(session)
        repo.create_movement(student_id=sid, semester_id=1, move_type="转班")
        assert repo.list_by_category("graduate") == []

    def test_list_by_student_still_works(self, session, repo):
        sid = _student(session)
        repo.create_movement(student_id=sid, semester_id=1, move_type="转班")
        assert len(repo.list_by_student(sid)) == 1
