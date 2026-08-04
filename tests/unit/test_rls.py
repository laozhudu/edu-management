"""
RowLevelSecurity 测试（Sprint 3.7.18）
覆盖：作用域查询、默认兜底、策略管理、apply_scope 过滤（all/none/own_class/own_classes）
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.core.rls import RowLevelSecurity
from edu_system.models import Base, Role, Student


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture
def rls(session):
    return RowLevelSecurity(session)


class TestScopeQuery:
    def test_default_all_admin(self, rls):
        assert rls.get_scope_by_role_name("admin", "student") == "all"

    def test_default_none_reader(self, rls):
        assert rls.get_scope_by_role_name("reader", "student") == "none"

    def test_default_own_classes_teacher(self, rls):
        assert rls.get_scope_by_role_name("teacher", "student") == "own_classes"


class TestPolicyCRUD:
    def test_set_and_get(self, session, rls):
        from edu_system.models import Role

        r = Role(name="custom", permissions="")
        session.add(r)
        session.commit()
        rls.set_policy(r.id, "student", "own_class")
        assert rls.get_scope(r.id, "student") == "own_class"

    def test_set_upsert(self, session, rls):
        r = Role(name="custom", permissions="")
        session.add(r)
        session.commit()
        rls.set_policy(r.id, "student", "own_class")
        rls.set_policy(r.id, "student", "all")  # 更新
        assert rls.get_scope(r.id, "student") == "all"

    def test_delete_policy(self, session, rls):
        r = Role(name="custom", permissions="")
        session.add(r)
        session.commit()
        rls.set_policy(r.id, "student", "own_class")
        rls.delete_policy(r.id, "student")
        assert rls.get_scope(r.id, "student") is None


class TestApplyScope:
    def _seed(self, session):
        for cid, name in [(1, "一班"), (2, "二班")]:
            session.add(Student(name=name, class_id=cid, semester_id=0))
        session.commit()

    def test_all_scope_no_filter(self, session, rls):
        self._seed(session)
        q = rls.apply_scope(session.query(Student), "student", "admin")
        assert q.count() == 2

    def test_none_scope_empty(self, session, rls):
        self._seed(session)
        q = rls.apply_scope(session.query(Student), "student", "reader")
        assert q.count() == 0

    def test_own_class_filter(self, session, rls):
        """班主任 own_class 作用域：DB 策略 + role_id"""
        self._seed(session)
        r = Role(name="head_teacher", permissions="")
        session.add(r)
        session.commit()
        rls.set_policy(r.id, "student", "own_class")
        q = rls.apply_scope(
            session.query(Student),
            "student",
            "head_teacher",
            context={"class_id": 1},
            role_id=r.id,
        )
        rows = q.all()
        assert len(rows) == 1
        assert rows[0].class_id == 1

    def test_apply_scope_own_class_via_context(self, session, rls):
        """apply_scope 的 own_class 分支（DB 策略 + context + role_id）"""
        self._seed(session)
        r = Role(name="head_teacher", permissions="")
        session.add(r)
        session.commit()
        rls.set_policy(r.id, "student", "own_class")
        # 直接调 apply_scope：DB 策略优先（role_id 传入）
        q = rls.apply_scope(
            session.query(Student),
            "student",
            "head_teacher",
            context={"class_id": 2},
            role_id=r.id,
        )
        rows = q.all()
        assert len(rows) == 1
        assert rows[0].class_id == 2

    def test_own_classes_multiple(self, session, rls):
        self._seed(session)
        q = rls.apply_scope(
            session.query(Student),
            "student",
            "teacher",
            context={"class_ids": [1, 2]},
        )
        assert q.count() == 2

    def test_own_classes_subset(self, session, rls):
        self._seed(session)
        q = rls.apply_scope(
            session.query(Student),
            "student",
            "teacher",
            context={"class_ids": [1]},
        )
        assert q.count() == 1

    def test_own_classes_no_context_empty(self, session, rls):
        self._seed(session)
        q = rls.apply_scope(session.query(Student), "student", "teacher")
        assert q.count() == 0

    def test_predefined_policy(self, session, rls):
        """DB 配置的作用域优先于默认"""
        r = Role(name="custom", permissions="")
        session.add(r)
        session.commit()
        # custom 不在默认策略 → none
        assert rls.get_scope_by_role_name("custom", "score") == "none"
        # DB 配置后生效
        rls.set_policy(r.id, "score", "all")
        assert rls.get_scope(r.id, "score") == "all"
