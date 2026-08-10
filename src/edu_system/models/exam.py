# ruff: noqa: F405  (star import 自 base.py，__all__ 已保证定义)
"""
exam 域模型
"""

from __future__ import annotations

import enum

from edu_system.models.base import *  # noqa: F401,F403,F405


class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    name = Column(String(30))
    exam_type = Column(
        String(20), default="midterm", comment="midterm/final/monthly/weekly/mock/custom"
    )
    exam_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=True)
    note = Column(Text, default="")
    is_makeup = Column(Boolean, default=False, comment="是否补考考试")
    status = Column(
        String(20), default="draft", comment="draft/scheduled/in_progress/completed/archived"
    )
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(
        DateTime, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow
    )
    ext_json = Column(Text, nullable=True, comment="自定义扩展字段（JSON 对象）")
    __table_args__ = (UniqueConstraint("semester_id", "name", "grade_id"),)
    semester = relationship("Semester", back_populates="exams")
    grade = relationship("Grade")
    scores = relationship("Score", back_populates="exam")

    @property
    def start_date(self):
        """兼容属性：返回 exam_date 作为 start_date"""
        return self.exam_date

    @start_date.setter
    def start_date(self, value):
        self.exam_date = value


class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    score = Column(Float, nullable=True, comment="原始分（NULL=缺考）")
    converted_score = Column(Float, nullable=True, comment="折算分（按折算规则换算，NULL=未折算）")
    is_makeup = Column(Boolean, default=False, comment="是否补考/重修")
    is_published = Column(Boolean, default=False, comment="是否已发布")
    ext_json = Column(Text, nullable=True, comment="自定义扩展字段（JSON 对象）")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", "subject_id"),
        Index("idx_scores_exam", "exam_id"),
    )
    exam = relationship("Exam", back_populates="scores")
    student = relationship("Student", back_populates="scores")
    subject = relationship("Subject")


class ExamSubjectSetting(Base):
    __tablename__ = "exam_subject_settings"
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    full_mark = Column(Float, default=100)
    pass_line = Column(Float, default=60)
    good_line = Column(Float, default=80)
    excellent_line = Column(Float, default=90)
    low_line = Column(Float, default=30)
    __table_args__ = (UniqueConstraint("exam_id", "subject_id"),)


# ════════════════════════════════════
# 考试管理 (扩展)
# ════════════════════════════════════


# ════════════════════════════════════
# 考试管理 (扩展)
# ════════════════════════════════════
class ExamType(enum.StrEnum):
    """考试类型"""

    midterm = "midterm"  # 期中
    final = "final"  # 期末
    monthly = "monthly"  # 月考
    weekly = "weekly"  # 周考
    mock = "mock"  # 模拟
    custom = "custom"  # 自定义


class ExamStatus(enum.StrEnum):
    """考试状态"""

    draft = "draft"  # 草稿
    scheduled = "scheduled"  # 已排程
    in_progress = "in_progress"  # 进行中
    completed = "completed"  # 已完成
    archived = "archived"  # 已归档


class RoomAssignmentStatus(enum.StrEnum):
    """考场分配状态"""

    pending = "pending"  # 待分配
    assigned = "assigned"  # 已分配
    confirmed = "confirmed"  # 已确认


class ExamRoom(Base):
    """考试考场表"""

    __tablename__ = "exam_rooms"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    capacity = Column(Integer, default=30)
    assigned_count = Column(Integer, default=0)
    invigilator1_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    invigilator2_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    status = Column(SQLEnum(RoomAssignmentStatus), default=RoomAssignmentStatus.pending)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("exam_id", "room_id", "subject_id", name="uq_exam_room_subject"),
        Index("idx_exam_room_exam", "exam_id"),
    )
    exam = relationship("Exam")
    room = relationship("Classroom")
    subject = relationship("Subject")
    invigilator1 = relationship("Teacher", foreign_keys=[invigilator1_id])
    invigilator2 = relationship("Teacher", foreign_keys=[invigilator2_id])


class ExamSeat(Base):
    """考试座次表"""

    __tablename__ = "exam_seats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("exam_rooms.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    seat_row = Column(Integer, nullable=False)
    seat_col = Column(Integer, nullable=False)
    seat_number = Column(String(10), nullable=False, comment="如 01-01")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_exam_student_seat"),
        UniqueConstraint("room_id", "seat_row", "seat_col", name="uq_room_seat"),
        Index("idx_exam_seat_room", "room_id"),
    )
    exam = relationship("Exam")
    room = relationship("ExamRoom")
    student = relationship("Student")


class Invigilation(Base):
    """监考安排表"""

    __tablename__ = "invigilations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("exam_rooms.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    role = Column(String(20), default="chief", comment="chief/deputy/assistant")
    check_time = Column(DateTime, nullable=True, comment="签到时间")
    status = Column(String(20), default="pending", comment="pending/checked_in/absent")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_invigilation_exam_teacher", "exam_id", "teacher_id"),)
    exam = relationship("Exam")
    room = relationship("ExamRoom")
    teacher = relationship("Teacher")


class AdmitCard(Base):
    """准考证表"""

    __tablename__ = "admit_cards"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    qrcode_data = Column(Text, nullable=True, comment="二维码数据")
    pdf_url = Column(String(500), nullable=True, comment="PDF 存储路径")
    generated_at = Column(DateTime, nullable=True)
    printed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="generated", comment="generated/printed/issued")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_exam_admit_card"),
        Index("idx_admit_card_exam", "exam_id"),
    )
    exam = relationship("Exam")
    student = relationship("Student")
