# ruff: noqa: F401  (本文件为纯 re-export，供 from edu_system.models import X 兼容)
"""edu_system — SQLAlchemy 声明式模型（按域拆分）
Base 单一来源：edu_system.models.base
"""

from edu_system.models.academic import (
    AcademicYear,
    Class,
    Grade,
    GradeSubject,
    Semester,
    SemesterStatus,
    Subject,
)
from edu_system.models.attendance import (
    Attendance,
    AttendanceStatus,
    AttendanceType,
    CheckMethod,
    LeaveApplication,
)
from edu_system.models.base import Base  # noqa: F401  (re-export)

# 单一 Base：与域文件（from .base import *）共用同一实例
from edu_system.models.exam import (
    AdmitCard,
    Exam,
    ExamRoom,
    ExamSeat,
    ExamStatus,
    ExamSubjectSetting,
    ExamType,
    Invigilation,
    RoomAssignmentStatus,
    Score,
)
from edu_system.models.library import (  # noqa: F401  (A2 演示业务域：图书管理)
    Book,
    BorrowRecord,
)
from edu_system.models.report import (
    ReportTemplate,
    SemesterStatsCache,
)
from edu_system.models.student import (
    Student,
    StudentMovement,
)
from edu_system.models.system import (
    AuditLog,
    Classroom,
    DataLock,
    DeviceTrust,
    DictData,
    DictType,
    FieldDefinition,
    GlobalSetting,
    IdempotencyKey,
    LockLevel,
    LoginLog,
    Notice,
    NoticeRead,
    OnlineUser,
    OutboxEvent,
    Role,
    RolePermission,
    RowLevelPolicy,
    School,
    SemesterConfig,
    SemesterConfigHistory,
    ServiceConfig,
    Setting,
    User,
    UserColumnConfig,
)
from edu_system.models.teacher import (
    ClassSubject,
    Department,
    Teacher,
    TeacherMovement,
)
from edu_system.services.storage import StoredFile  # noqa: E402, F401
