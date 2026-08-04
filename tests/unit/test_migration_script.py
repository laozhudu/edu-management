"""
迁移脚本框架测试（Sprint 3.7.20）
覆盖：dry-run 不执行、checksum 计算/变化检测、回滚 SQL 生成
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from migrate_semester_context import MigrationScript
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from edu_system.models import Base, Semester


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


class TestMigrationScript:
    def test_dry_run_does_not_execute(self, session):
        """dry-run 模式不真正执行 SQL"""
        ms = MigrationScript(session, dry_run=True, verbose=False)
        ms.execute_sql("CREATE TABLE should_not_exist (id INTEGER)")
        # 表不应创建
        from sqlalchemy import inspect

        tables = inspect(session.bind).get_table_names()
        assert "should_not_exist" not in tables
        # 但 SQL 被记录
        assert ms.executed_sql == ["CREATE TABLE should_not_exist (id INTEGER)"]

    def test_execute_applies_sql(self, session):
        ms = MigrationScript(session, dry_run=False)
        ms.execute_sql("CREATE TABLE tmp_mig_test (id INTEGER)")
        from sqlalchemy import inspect

        tables = inspect(session.bind).get_table_names()
        assert "tmp_mig_test" in tables

    def test_checksum_stable(self, session):
        """同一数据校验和一致"""
        ms = MigrationScript(session)
        c1 = ms.get_table_checksum("semesters")
        c2 = ms.get_table_checksum("semesters")
        assert c1 == c2

    def test_checksum_changes_on_data_change(self, session):
        """数据变化后校验和变化"""
        ms = MigrationScript(session)
        before = ms.get_table_checksum("semesters")
        session.execute(
            text(
                "INSERT INTO semesters (label, year_start, semester, academic_year_id, status) VALUES ('测试', 2025, '1', 0, 'draft')"
            )
        )
        session.commit()
        after = ms.get_table_checksum("semesters")
        assert before != after

    def test_checksum_missing_table(self, session):
        """表不存在返回 ERROR 前缀"""
        ms = MigrationScript(session)
        result = ms.get_table_checksum("no_such_table")
        assert result.startswith("ERROR")

    def test_snapshot_and_verify(self, session):
        """快照后校验和对比"""
        ms = MigrationScript(session)
        tables = ["semesters"]
        ms.snapshot_checksums(tables)
        errors = ms.verify_checksums(tables)
        assert errors == []

    def test_generate_rollback_sql(self, session):
        """回滚 SQL 生成（含学期状态回滚语句）"""
        ms = MigrationScript(session, dry_run=False)
        rollback = ms.generate_rollback_sql()
        assert "UPDATE semesters" in rollback
        assert "COMMIT" in rollback

    def test_rollback_reverts(self, session):
        """事务回滚撤销数据变更（DML）"""
        ms = MigrationScript(session, dry_run=False)
        ms.execute_sql(
            "INSERT INTO semesters (label, year_start, semester, academic_year_id, status) VALUES ('回滚测试', 2025, '1', 0, 'draft')"
        )
        assert session.query(Semester).filter_by(label="回滚测试").count() == 1
        session.rollback()
        assert session.query(Semester).filter_by(label="回滚测试").count() == 0
