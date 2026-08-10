# ruff: noqa: F405  (star import 自 base.py，__all__ 已保证定义)
"""
teacher 域模型
"""

from __future__ import annotations

from edu_system.models.base import *  # noqa: F401,F403,F405


# ════════════════════════════════════
# 教师 (完整人事信息)
# ════════════════════════════════════
class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True)
    gender = Column(String(4), default="")
    phone = Column(String(20), default="")
    title = Column(String(20), default="", comment="职称")
    education = Column(String(20), default="", comment="学历")
    degree = Column(String(20), default="", comment="学位")
    political_status = Column(String(20), default="", comment="政治面貌")
    birth_date = Column(Date, nullable=True, comment="出生年月")
    work_start_date = Column(Date, nullable=True, comment="参加工作时间")
    graduation_date = Column(Date, nullable=True, comment="毕业时间")
    staff_no = Column(String(20), default="", comment="编号")
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, comment="所属学期")
    status = Column(
        String(10), default="active", comment="在职状态: active在职/resigned离职/retired退休"
    )
    note = Column(Text, default="")
    ext_json = Column(Text, nullable=True, comment="自定义扩展字段（JSON 对象）")


class TeacherMovement(Base):
    """教师变动记录（对齐 StudentMovement：入职/变动/退休）"""

    __tablename__ = "teacher_movements"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"))
    semester_id = Column(
        Integer, ForeignKey("semesters.id"), nullable=False, comment="变动发生学期"
    )
    move_type = Column(String(10), comment="变动具体类型")
    movement_category = Column(
        String(20),
        default="",
        comment="规范分类: onboard入职/promote晋升/transfer调岗/resign离职/retire退休",
    )
    move_date = Column(Date, nullable=True)
    from_title = Column(String(20), default="", comment="原职称/岗位")
    to_title = Column(String(20), default="", comment="新职称/岗位")
    reason = Column(Text, default="")
    operator = Column(String(20), default="")
    created_at = Column(DateTime, server_default=func.now())


# ════════════════════════════════════
# 考试/成绩/任课/变动
# ════════════════════════════════════


# ════════════════════════════════════
# 考试/成绩/任课/变动
# ════════════════════════════════════
class ClassSubject(Base):
    __tablename__ = "class_subjects"
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    __table_args__ = (UniqueConstraint("semester_id", "class_id", "subject_id"),)
    semester = relationship("Semester", back_populates="class_subjects")
