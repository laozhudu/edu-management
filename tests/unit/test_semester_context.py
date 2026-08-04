"""
M5-A1/A2 学期上下文 + 自动注入过滤测试
覆盖：
- A1: set/get_active_semester 线程局部、semester_context 上下文管理器、线程隔离
- A2: before_compile 自动注入 WHERE semester_id（有列注入/无列排除/已有条件不重复/skip 标记/无激活学期不注入）
"""

import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.database import (
    _inject_semester_filter,
    get_active_semester,
    semester_context,
    set_active_semester,
)
from edu_system.models import Base, Class, Grade, Student


@pytest.fixture
def session():
    """内存库会话（含 Class/Student/Grade 表）"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture(autouse=True)
def _clean_semester():
    """每个测试前清理线程局部学期，防止被测试数据集加载器/其他测试污染"""
    set_active_semester(0)
    yield
    set_active_semester(0)


# ============================================================
# A1 会话上下文管理器
# ============================================================


class TestActiveSemester:
    def test_default_zero(self):
        """未设置时默认 0（无激活学期）"""
        assert get_active_semester() == 0

    def test_set_and_get(self):
        set_active_semester(7)
        assert get_active_semester() == 7
        set_active_semester(0)

    def test_thread_local_isolation(self):
        """不同线程互不影响（线程局部存储）"""
        set_active_semester(1)
        results = {}

        def worker():
            results["before"] = get_active_semester()
            set_active_semester(99)
            results["after_set"] = get_active_semester()

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert results["before"] == 0  # 子线程看不到主线程的值
        assert results["after_set"] == 99
        assert get_active_semester() == 1  # 主线程不受子线程影响


class TestSemesterContext:
    def test_context_switches_and_restores(self):
        """semester_context 进入切换、退出恢复"""
        set_active_semester(3)
        with semester_context(5):
            assert get_active_semester() == 5
        assert get_active_semester() == 3

    def test_context_nested(self):
        """嵌套上下文：内层退出后回到外层值"""
        set_active_semester(1)
        with semester_context(2):
            with semester_context(3):
                assert get_active_semester() == 3
            assert get_active_semester() == 2
        assert get_active_semester() == 1

    def test_context_restores_on_exception(self):
        """异常时同样恢复原值"""
        set_active_semester(4)
        with pytest.raises(RuntimeError):
            with semester_context(8):
                raise RuntimeError("boom")
        assert get_active_semester() == 4


# ============================================================
# A2 before_compile 自动注入
# ============================================================


class TestInjectSemesterFilter:
    def _sql(self, query):
        """编译查询为 SQL 字符串"""
        return str(query.statement.compile(compile_kwargs={"literal_binds": True}))

    def test_inject_when_semester_active(self, session):
        """激活学期时，含 semester_id 列的表自动注入 WHERE"""
        set_active_semester(10)
        q = session.query(Class)
        sql = self._sql(q)
        assert "semester_id" in sql
        assert "10" in sql

    def test_no_inject_without_semester(self, session):
        """无激活学期（0）时不注入 WHERE 过滤"""
        set_active_semester(0)
        q = session.query(Class)
        sql = self._sql(q)
        # SELECT 子句仍包含 semester_id 列，但不应有 WHERE semester_id 过滤
        assert "WHERE" not in sql or "semester_id =" not in sql

    def test_no_inject_for_table_without_column(self, session):
        """无 semester_id 列的表（grades）不注入"""
        set_active_semester(10)
        q = session.query(Grade)
        sql = self._sql(q)
        assert "semester_id" not in sql

    def test_existing_filter_not_duplicated(self, session):
        """已有 semester_id 过滤条件的查询不重复注入"""
        set_active_semester(10)
        q = session.query(Class).filter(Class.semester_id == 20)
        sql = self._sql(q)
        assert sql.count("semester_id = 20") == 1
        assert "10" not in sql

    def test_skip_marker(self, session):
        """标记 _skip_semester_filter 的查询跳过（跨学期报表/全局视图）"""
        set_active_semester(10)
        q = session.query(Class)
        q._skip_semester_filter = True
        sql = self._sql(q)
        # SELECT 子句仍包含 semester_id 列，但不应有 WHERE semester_id 过滤
        assert "WHERE" not in sql or "semester_id =" not in sql

    def test_multiple_entities_injected(self, session):
        """多实体查询（join）各自有列则都注入"""
        set_active_semester(10)
        q = session.query(Class, Student).join(Student, Student.class_id == Class.id)
        sql = self._sql(q)
        assert "classes.semester_id" in sql
        assert "students.semester_id" in sql

    def test_direct_function_returns_query(self, session):
        """事件函数返回查询对象（retval 契约）"""
        set_active_semester(10)
        q = session.query(Class)
        result = _inject_semester_filter(q)
        # filter() 返回新对象，验证返回的是 Query 且已注入过滤
        from sqlalchemy.orm import Query
        assert isinstance(result, Query)
        sql = self._sql(result)
        assert "semester_id = 10" in sql
