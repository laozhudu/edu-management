"""
SemesterConfig 配置版本回滚 + 软删除测试（M5-C2）

覆盖：
- 版本控制：多次设置配置版本递增，get_versions 返回全版本
- 回滚：rollback_to_version 生成新版本且内容恢复目标版本
- 软删除：回滚/继承时旧版本行标记 is_deleted（非物理删），历史可追溯
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.models import Base, Semester, SemesterConfig
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


def _write_configs(svc, semester_id, configs, operator="admin"):
    """写入一组配置（生成一个新版本）"""
    version = svc._get_next_version(semester_id)
    for key, value in configs.items():
        session = svc.session
        session.add(
            SemesterConfig(
                semester_id=semester_id,
                key=key,
                value=str(value),
                version=version,
                created_by=operator,
            )
        )
    session.flush()
    return version


class TestConfigVersioning:
    """版本控制 + 回滚"""

    def test_versions_increment_and_rollback(self, session, semesters):
        """写入多版本→get_versions 返回，回滚生成新版本且内容恢复"""
        s1, _ = semesters
        svc = SemesterConfigService(session)

        _write_configs(svc, s1.id, {"max_class_size": "50", "dorm_fee": "800"})
        session.commit()
        v1 = svc._get_current_version(s1.id)
        assert v1 == 1

        # 修改配置 → 版本 2
        _write_configs(svc, s1.id, {"max_class_size": "55", "dorm_fee": "900", "meal_fee": "300"})
        session.commit()
        v2 = svc._get_current_version(s1.id)
        assert v2 == 2

        # 版本列表含 v1/v2
        versions = svc.get_versions(s1.id)
        assert [v["version"] for v in versions] == [2, 1]

        # 回滚到 v1
        result = svc.rollback_to_version(s1.id, 1)
        assert result["success"] is True
        assert result["new_version"] == 3

        # 回滚后当前配置 = v1 内容
        current = svc._get_all_configs(s1.id)
        assert current["max_class_size"] == "50"
        assert current["dorm_fee"] == "800"
        assert "meal_fee" not in current  # v1 无此项

        session.rollback()

    def test_rollback_missing_version(self, session, semesters):
        """回滚不存在的版本返回失败"""
        s1, _ = semesters
        svc = SemesterConfigService(session)
        result = svc.rollback_to_version(s1.id, 99)
        assert result["success"] is False
        assert "不存在" in result["error"]


class TestSoftDelete:
    """软删除：旧版本保留可追溯"""

    def test_rollback_soft_deletes_old_version(self, session, semesters):
        """回滚时旧版本行标记 is_deleted（非物理删除），历史保留"""
        s1, _ = semesters
        svc = SemesterConfigService(session)

        _write_configs(svc, s1.id, {"max_class_size": "50"})
        session.commit()
        v1 = svc._get_current_version(s1.id)

        _write_configs(svc, s1.id, {"max_class_size": "60"})
        session.commit()
        v2 = svc._get_current_version(s1.id)

        # 回滚到 v1 → 生成 v3，v1/v2 标记软删除
        svc.rollback_to_version(s1.id, 1, operator="teacher")
        session.commit()

        # v1/v2 行都保留但标记软删除
        deleted = (
            session.query(SemesterConfig)
            .filter(
                SemesterConfig.semester_id == s1.id,
                SemesterConfig.version.in_([v1, v2]),
                SemesterConfig.is_deleted.is_(True),
            )
            .count()
        )
        assert deleted >= 1, "旧版本行应标记软删除"

        # v3 为新有效版本
        v3 = svc._get_current_version(s1.id)
        assert v3 == 3
        active_rows = (
            session.query(SemesterConfig)
            .filter(
                SemesterConfig.semester_id == s1.id,
                SemesterConfig.version == v3,
                SemesterConfig.is_deleted.is_(False),
            )
            .count()
        )
        assert active_rows == 1  # 只有 max_class_size

        session.rollback()

    def test_version_history_materialized(self, session, semesters):
        """软删除后历史版本内容仍可从 get_version_configs 读取（可回滚追溯）"""
        s1, _ = semesters
        svc = SemesterConfigService(session)

        _write_configs(svc, s1.id, {"A": "1", "B": "2"})
        session.commit()
        v1 = svc._get_current_version(s1.id)

        _write_configs(svc, s1.id, {"A": "10", "B": "20"})
        session.commit()

        # 软删 v1 + v2，写入 v3
        svc.rollback_to_version(s1.id, v1)
        session.commit()

        # v1 历史内容仍可读取
        v1_configs = svc.get_version_configs(s1.id, v1)
        assert v1_configs == {"A": "1", "B": "2"}
        session.rollback()


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
