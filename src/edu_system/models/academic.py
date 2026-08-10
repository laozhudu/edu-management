# ruff: noqa: F405  (star import 自 base.py，__all__ 已保证定义)
"""
academic 域模型
"""

from __future__ import annotations

import enum

from edu_system.models.base import *  # noqa: F401,F403,F405


# ════════════════════════════════════
# 学年 / 学期
# ════════════════════════════════════
class SemesterStatus(enum.StrEnum):
    """学期状态枚举"""

    draft = "draft"  # 草稿
    active = "active"  # 激活
    locked = "locked"  # 锁定（仅查询/导出）
    archived = "archived"  # 归档（只读）


class AcademicYear(Base):
    """学年模型"""

    __tablename__ = "academic_years"
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True, nullable=False, comment="如 2024-2025")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=False)
    description = Column(String(200), default="")
    created_at = Column(DateTime, server_default=func.now())

    semesters = relationship(
        "Semester", back_populates="academic_year", order_by="Semester.sort_order"
    )


class Semester(Base):
    __tablename__ = "semesters"
    id = Column(Integer, primary_key=True)
    academic_year_id = Column(
        Integer, ForeignKey("academic_years.id"), nullable=False, comment="所属学年"
    )
    year_start = Column(Integer, nullable=False, comment="起始年份，如 2024")
    semester = Column(String(10), nullable=False, comment="学期标识：1/2/夏/冬")
    label = Column(String(50), nullable=False, comment="显示名称，如 2024-2025 第1学期")
    sort_order = Column(Integer, default=0, comment="学期内排序：1=秋季/第1学期，2=春季/第2学期")
    is_active = Column(Boolean, default=False, comment="是否为当前激活学期")
    status = Column(
        SQLEnum(SemesterStatus), default=SemesterStatus.draft, nullable=False, comment="学期状态"
    )
    start_date = Column(Date, nullable=True, comment="学期开始日期")
    end_date = Column(Date, nullable=True, comment="学期结束日期")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("academic_year_id", "semester", name="uq_semester_year_term"),
        Index("idx_semester_active", "is_active"),
        Index("idx_semester_status", "status"),
    )
    academic_year = relationship("AcademicYear", back_populates="semesters")
    exams = relationship("Exam", back_populates="semester")
    class_subjects = relationship("ClassSubject", back_populates="semester")
    classrooms = relationship("Classroom", back_populates="semester")
    classes = relationship("Class", back_populates="semester")

    @property
    def display_label(self) -> str:
        """统一显示样式：2024-2025学年度第一学期（不依赖存储 label，兼容存量）"""
        ay_name = (
            self.academic_year.name
            if self.academic_year
            else f"{self.year_start}-{self.year_start + 1}"
        )
        cn = {"1": "一", "2": "二", "3": "三", "4": "四"}.get(
            str(self.semester), str(self.semester)
        )
        return f"{ay_name}学年度第{cn}学期"


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True)
    full_mark = Column(Float, default=100)
    pass_line = Column(Float, default=60)
    good_line = Column(Float, default=80)
    excellent_line = Column(Float, default=90)
    low_line = Column(Float, default=30)
    sort_order = Column(Integer, default=0)


class Grade(Base):
    __tablename__ = "grades"
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True)
    sort_order = Column(Integer, default=0)
    classes = relationship("Class", back_populates="grade")


class GradeSubject(Base):
    __tablename__ = "grade_subjects"
    id = Column(Integer, primary_key=True)
    grade_id = Column(Integer, ForeignKey("grades.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    sort_order = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("grade_id", "subject_id"),)


class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, comment="所属学期")
    name = Column(String(10))
    head_teacher = Column(String(20), default="")
    class_type = Column(String(20), default="")
    room = Column(String(20), default="")
    ext_json = Column(Text, nullable=True, comment="自定义扩展字段（JSON 对象）")
    __table_args__ = (
        UniqueConstraint("grade_id", "semester_id", "name"),
        Index("idx_class_grade_semester", "grade_id", "semester_id"),
    )
    grade = relationship("Grade", back_populates="classes")
    semester = relationship("Semester", back_populates="classes")
    students = relationship("Student", back_populates="class_")
    attendance_records = relationship("Attendance", back_populates="class_")


# ════════════════════════════════════
# 学生 (完整学籍信息)
# ════════════════════════════════════
