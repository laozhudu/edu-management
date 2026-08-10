# ruff: noqa: F405  (star import 自 base.py，__all__ 已保证定义)
"""
attendance 域模型
"""

from __future__ import annotations

import enum

from edu_system.models.base import *  # noqa: F401,F403,F405


# ════════════════════════════════════
# 考勤管理
# ════════════════════════════════════
class AttendanceType(enum.StrEnum):
    """考勤类型"""

    morning = "morning"  # 早读/早操
    noon = "noon"  # 午休
    afternoon = "afternoon"  # 下午课
    evening = "evening"  # 晚自习
    custom = "custom"  # 自定义


class CheckMethod(enum.StrEnum):
    """打卡方式"""

    gps = "gps"  # GPS 定位
    bluetooth = "bluetooth"  # 蓝牙信标
    face = "face"  # 人脸识别
    qrcode = "qrcode"  # 二维码
    manual = "manual"  # 手工补录


class AttendanceStatus(enum.StrEnum):
    """考勤状态"""

    present = "present"  # 正常
    late = "late"  # 迟到
    early_leave = "early_leave"  # 早退
    absent = "absent"  # 旷课
    leave = "leave"  # 请假
    makeup = "makeup"  # 补卡


class Attendance(Base):
    """考勤记录表"""

    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, autoincrement=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    attendance_type = Column(
        SQLEnum(AttendanceType), nullable=False, default=AttendanceType.morning
    )
    check_time = Column(DateTime, nullable=True, comment="实际打卡时间")
    scheduled_time = Column(DateTime, nullable=True, comment="应打卡时间")
    status = Column(SQLEnum(AttendanceStatus), nullable=False, default=AttendanceStatus.present)
    check_method = Column(SQLEnum(CheckMethod), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    face_verified = Column(Boolean, default=False)
    device_info = Column(String(200), nullable=True)
    remark = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint(
            "semester_id", "student_id", "date", "attendance_type", name="uq_student_attendance"
        ),
        Index("idx_attendance_class_date", "class_id", "date"),
        Index("idx_attendance_status", "status"),
    )
    student = relationship("Student", back_populates="attendance_records")
    class_ = relationship("Class")


class LeaveApplication(Base):
    """请假申请表"""

    __tablename__ = "leave_applications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    leave_type = Column(String(20), nullable=False, comment="事假/病假/公假/其他")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    reason = Column(Text, nullable=False)
    attachments = Column(Text, nullable=True, comment="JSON 数组：附件 URL")
    status = Column(String(20), default="pending", comment="pending/approved/rejected/cancelled")
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    reject_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        Index("idx_leave_student_status", "student_id", "status"),
        Index("idx_leave_class_date", "class_id", "start_date"),
    )
    student = relationship("Student")
    class_ = relationship("Class")
    approver = relationship("User")


# ════════════════════════════════════
# 设备信任表
# ════════════════════════════════════
