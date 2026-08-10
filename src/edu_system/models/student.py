# ruff: noqa: F405  (star import 自 base.py，__all__ 已保证定义)
"""
student 域模型
"""

from __future__ import annotations

from edu_system.models.base import *  # noqa: F401,F403,F405


# ════════════════════════════════════
# 学生 (完整学籍信息)
# ════════════════════════════════════
class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    name = Column(String(20), index=True)
    former_name = Column(String(20), default="")
    gender = Column(String(4), default="")
    student_no = Column(String(10), default="", comment="座号")
    student_code = Column(String(30), default="", comment="全国学籍号")
    id_card = Column(String(20), default="", comment="身份证号")
    birth_date = Column(Date, nullable=True)
    ethnicity = Column(String(20), default="")
    native_place = Column(String(30), default="", comment="籍贯")
    political_status = Column(String(20), default="群众", comment="政治面貌")
    phone = Column(String(20), default="")
    address = Column(String(100), default="", comment="居住地址")
    hukou_addr = Column(String(100), default="", comment="户籍地址")
    enroll_year = Column(Integer, default=0, comment="入学年份")
    exam_no = Column(String(20), default="", comment="考号(入学时生成，终身不变)")
    boarding = Column(String(10), default="走读")
    multiple_birth = Column(String(10), default="")
    health_status = Column(String(20), default="")
    is_disabled = Column(String(4), default="否")
    left_behind = Column(String(4), default="否")
    # 监护人1
    guardian1_name = Column(String(20), default="")
    guardian1_relation = Column(String(20), default="")
    guardian1_phone = Column(String(20), default="")
    guardian1_work = Column(String(50), default="")
    guardian1_edu = Column(String(20), default="")
    guardian1_id_card = Column(String(20), default="")
    # 监护人2
    guardian2_name = Column(String(20), default="")
    guardian2_relation = Column(String(20), default="")
    guardian2_phone = Column(String(20), default="")
    guardian2_work = Column(String(50), default="")
    guardian2_edu = Column(String(20), default="")
    guardian2_id_card = Column(String(20), default="")
    # 状态
    status = Column(String(10), default="在校")
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, comment="就读学期")
    # 照片
    photo = Column(LargeBinary, nullable=True, comment="学生照片")
    photo_mime = Column(String(20), default="", comment="照片MIME类型")
    note = Column(Text, default="")
    ext_json = Column(Text, nullable=True, comment="自定义扩展字段（JSON 对象）")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("class_id", "name", name="uq_student_class_name"),
        Index("idx_student_status", "status"),
        Index("idx_student_code", "student_code"),
        Index("idx_student_semester", "semester_id"),
    )
    class_ = relationship("Class", back_populates="students")
    scores = relationship("Score", back_populates="student")
    attendance_records = relationship("Attendance", back_populates="student")
    movements = relationship("StudentMovement", back_populates="student")

    @property
    def class_name(self):
        return self.class_.name if self.class_ else ""


# ════════════════════════════════════
# 教师 (完整人事信息)
# ════════════════════════════════════


class StudentMovement(Base):
    __tablename__ = "student_movements"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"))
    semester_id = Column(
        Integer, ForeignKey("semesters.id"), nullable=False, comment="变动发生学期"
    )
    move_type = Column(String(10), comment="变动具体类型")
    movement_category = Column(
        String(20),
        default="",
        comment="规范分类: upgrade升级/retain留级/transfer转班/suspend休学/resume复学/transfer_in转入/transfer_out转出/graduate毕业",
    )
    move_date = Column(Date, nullable=True)
    from_class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    to_class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    reason = Column(Text, default="")
    operator = Column(String(20), default="")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        Index("idx_movements_student", "student_id"),
        Index("idx_movements_semester", "semester_id"),
    )
    student = relationship("Student", back_populates="movements")
