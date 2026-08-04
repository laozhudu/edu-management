"""
SemesterConfig 配置版本回滚 + 快照测试（M5-C2）

覆盖：
- 版本控制：继承执行产生版本递增，get_versions 返回全版本
- 回滚：rollback_to_version 恢复目标版本内容（覆盖当前值 + 删多余 key）
- 快照：每次写入/回滚在 history 表留档（key/value/version）
- 历史追溯：get_version_configs 可读任意历史版本
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.models import Base, Semester, SemesterConfig, SemesterConfigHistory
from edu_system.services.semester_config import SemesterConfigService


@pytest.fixture
def session():
    """内存 SQLite 会话"""
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
def semesters(session):
    """构造两个学期"""
    from edu_system.models import AcademicYear

    ay = AcademicYear(name="2024-2025", sort_order=0, is_active=True)
    session.add(ay)
    session.flush()

    s1 = Semester(
        academic_year_id=ay.id,
        year_start=2024,
        semester="1",
        label="2024-2025 第1学期",
        sort_order=1,
        is_active=True,
        status="active",
    )
    s2 = Semester(
        academic_year_id=ay.id,
        year_start=2024,
        semester="2",
        label="2024-2025 第2学期",
        sort_order=2,
        is_active=True,
        status="active",
    )
    session.add_all([s1, s2])
    session.flush()
    return s1, s2


def _seed_configs(session, semester_id, source_id):
    """用源学期配置执行多次继承，制造多版本"""
    svc = SemesterConfigService(session)

    def _inherit(source, configs, overwrite=None):
        # source 端写配置：每 key 一行当前值（upsert）
        v = (svc._get_current_version(source) or 0) + 1
        for k, val in configs.items():
            existing = (
                session.query(SemesterConfig)
                .filter(SemesterConfig.semester_id == source, SemesterConfig.key == k)
                .first()
            )
            if existing:
                existing.value = str(val)
                existing.version = v
            else:
                session.add(
                    SemesterConfig(
                        semester_id=source, key=k, value=str(val), version=v, created_by="t"
                    )
                )
        session.flush()
        return svc.execute_inherit(source, semester_id, overwrite, operator="teacher")

    _inherit(source_id, {"max_class_size": "50", "dorm_fee": "800"})
    res = _inherit(source_id, {"max_class_size": "60"}, overwrite=["max_class_size"])
    session.commit()
    return res


class TestConfigVersioning:
    """版本控制 + 回滚"""

    def test_versions_increment_and_rollback(self, session, semesters):
        """继承产生多版本→get_versions 返回，回滚恢复目标内容"""
        s1, s2 = semesters
        svc = SemesterConfigService(session)

        # 两次继承 → 版本递增
        _seed_configs(session, s1.id, s2.id)
        versions = svc.get_versions(s1.id)
        assert [v["version"] for v in versions] == [2, 1]

        # 回滚到 v1
        result = svc.rollback_to_version(s1.id, 1)
        assert result["success"] is True

        # 回滚后当前配置 = v1 内容
        current = svc._get_all_configs(s1.id)
        assert current["max_class_size"] == "50"
        assert current["dorm_fee"] == "800"

        session.rollback()

    def test_rollback_missing_version(self, session, semesters):
        """回滚不存在的版本返回失败"""
        s1, _ = semesters
        svc = SemesterConfigService(session)
        result = svc.rollback_to_version(s1.id, 99)
        assert result["success"] is False
        assert "不存在" in result["error"]


class TestSnapshotHistory:
    """版本快照：history 表留档 + 可追溯回滚"""

    def test_inherit_writes_history(self, session, semesters):
        """继承执行后 history 表有快照，get_version_configs 可读"""
        s1, s2 = semesters
        svc = SemesterConfigService(session)

        _seed_configs(session, s1.id, s2.id)

        # history 表有 v1 + v2 快照（version 0 是继承前的初始快照）
        hist_rows = (
            session.query(SemesterConfigHistory)
            .filter(SemesterConfigHistory.semester_id == s1.id)
            .all()
        )
        assert hist_rows, "继承应写入历史快照"
        versions = {h.version for h in hist_rows}
        assert {1, 2}.issubset(versions), f"应有版本 1,2，实际 {versions}"

        # 可读 v1 历史内容
        v1 = svc.get_version_configs(s1.id, 1)
        assert v1["max_class_size"] == "50"
        assert v1["dorm_fee"] == "800"
        session.rollback()

    def test_rollback_writes_new_history_version(self, session, semesters):
        """回滚产生新高版本快照，旧版本仍可读"""
        s1, s2 = semesters
        svc = SemesterConfigService(session)

        _seed_configs(session, s1.id, s2.id)
        svc.rollback_to_version(s1.id, 1, operator="admin")
        session.commit()

        # 回滚产生 v3（当前版本号=旧当前+1）
        assert svc._get_current_version(s1.id) == 3
        # v1 历史仍可追溯
        assert svc.get_version_configs(s1.id, 1)["max_class_size"] == "50"
        session.rollback()


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
