"""
学期显示统一样式测试（2024-2025学年度第一学期）

覆盖：
- format_semester_label：服务层统一格式化（1→一、2→二）
- Semester.display_label：模型属性（不依赖存储 label，兼容存量数据）
- 存量数据兼容：label 存旧格式时 display_label 仍输出统一格式
"""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.models import AcademicYear, Base, Semester, SemesterStatus
from edu_system.services.semester import SemesterService, format_semester_label


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


class TestFormatSemesterLabel:
    def test_first_semester(self):
        assert format_semester_label("2024-2025", "1") == "2024-2025学年度第一学期"

    def test_second_semester(self):
        assert format_semester_label("2024-2025", "2") == "2024-2025学年度第二学期"

    def test_int_input(self):
        assert format_semester_label("2024-2025", 1) == "2024-2025学年度第一学期"

    def test_unknown_number_passthrough(self):
        assert format_semester_label("2024-2025", "夏") == "2024-2025学年度第夏学期"


class TestDisplayLabel:
    def _mk_semester(self, session, ay_name="2024-2025", semester_no="1", stored_label=None):
        ay = AcademicYear(name=ay_name, sort_order=0, is_active=True)
        session.add(ay)
        session.flush()
        sem = Semester(
            academic_year_id=ay.id,
            year_start=2024,
            semester=semester_no,
            label=stored_label or f"{ay_name} 第{semester_no}学期",
            sort_order=1,
            is_active=True,
            status=SemesterStatus.active,
            start_date=date(2024, 9, 1),
            end_date=date(2025, 1, 15),
        )
        session.add(sem)
        session.flush()
        return sem

    def test_display_label_new_format(self, session):
        sem = self._mk_semester(session, stored_label="2024-2025学年度第一学期")
        assert sem.display_label == "2024-2025学年度第一学期"

    def test_display_label_legacy_format(self, session):
        """存量数据：label 存旧格式「2024-2025 第1学期」，display_label 仍统一"""
        sem = self._mk_semester(session, stored_label="2024-2025 第1学期")
        assert sem.display_label == "2024-2025学年度第一学期"

    def test_display_label_second(self, session):
        sem = self._mk_semester(session, semester_no="2", stored_label="2024-2025 第2学期")
        assert sem.display_label == "2024-2025学年度第二学期"

    def test_create_semester_uses_format(self, session):
        """创建学期时 label 自动用统一格式"""
        ay = AcademicYear(name="2025-2026", sort_order=0, is_active=True)
        session.add(ay)
        session.flush()
        svc = SemesterService(session)
        sem = svc.create(
            academic_year_id=ay.id,
            semester="1",
            sort_order=1,
        )
        assert sem.label == "2025-2026学年度第一学期"
