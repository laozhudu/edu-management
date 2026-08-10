"""
edu_system — SQLAlchemy 声明式模型
兼容 1.4/2.0
统一命名规范：表名小写复数，类名单数 PascalCase
"""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

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


class ClassSubject(Base):
    __tablename__ = "class_subjects"
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    __table_args__ = (UniqueConstraint("semester_id", "class_id", "subject_id"),)
    semester = relationship("Semester", back_populates="class_subjects")


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


class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(50), primary_key=True)
    value = Column(Text, default="")


class AuditLog(Base):
    """审计日志表"""

    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String(10), nullable=False)  # INSERT/UPDATE/DELETE
    old_values = Column(Text, nullable=True)  # JSON
    new_values = Column(Text, nullable=True)  # JSON
    operator = Column(String(20), nullable=True)
    ip = Column(String(45), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


# ═══════════════════════════════════
# 权限系统预留模型 (v1.0 表建好，逻辑暂不启用)
# ═══════════════════════════════════


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(32), unique=True, comment="admin/director/teacher/reader")
    description = Column(String(255), default="")
    permissions = Column(String(4096), default="")

    users = relationship("User", back_populates="role")
    permission_entries = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )


class RolePermission(Base):
    """规范化权限表（Sprint 3.7.17）：替代 Role.permissions 逗号字符串

    - role_id + permission_code 唯一
    - 读写双轨：新表为准，Role.permissions 字符串保留兼容旧数据
    """

    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_code = Column(String(64), nullable=False)
    __table_args__ = (UniqueConstraint("role_id", "permission_code", name="uq_role_permission"),)
    role = relationship("Role", back_populates="permission_entries")


class RowLevelPolicy(Base):
    """行级数据作用域策略（Sprint 3.7.18）

    - role_id + entity_type + scope（作用域类型）+ 可选参数
    - scope: all(全校)/own_class(本班)/own_classes(任课班)/none(无)
    - 应用层拦截：查询时按角色作用域加过滤条件
    """

    __tablename__ = "row_level_policies"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    entity_type = Column(String(32), nullable=False, comment="student/score/attendance...")
    scope = Column(String(32), nullable=False, comment="all/own_class/own_classes/none")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("role_id", "entity_type", name="uq_rlp_role_entity"),)
    role = relationship("Role")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True, comment="登录名")
    password_hash = Column(String(128), default="")
    display_name = Column(String(64), default="")
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    role = relationship("Role", back_populates="users")

    @property
    def permissions(self) -> list:
        """获取用户权限列表（从角色继承）"""
        if self.role and self.role.permissions:
            return [p.strip() for p in self.role.permissions.split(",") if p.strip()]
        return []


class UserColumnConfig(Base):
    """用户列配置持久化（M5-G：多端同步）"""

    __tablename__ = "user_column_configs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    page_id = Column(String(64), nullable=False, index=True, comment="页面标识")
    columns = Column(JSON, default=[], comment="列配置 JSON")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    __table_args__ = (UniqueConstraint("user_id", "page_id", name="uq_user_page_config"),)

    user = relationship("User", backref="column_configs")


class Classroom(Base):
    __tablename__ = "classrooms"
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, comment="学期")
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, comment="班级")
    floor = Column(String(10), default="", comment="楼层")
    room_no = Column(String(20), default="", comment="教室号")
    capacity = Column(Integer, default=50, comment="座位数")
    semester = relationship("Semester", back_populates="classrooms")


# ════════════════════════════════════
# 系统级配置与学期配置
# ════════════════════════════════════


class GlobalSetting(Base):
    """全局配置（跨学期通用）"""

    __tablename__ = "global_settings"
    key = Column(String(50), primary_key=True)
    value = Column(Text, default="")
    description = Column(String(200), default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SemesterConfig(Base):
    """学期级配置（随学期隔离，支持版本控制与继承追溯）"""

    __tablename__ = "semester_configs"
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    key = Column(String(50), nullable=False, index=True)
    value = Column(Text, default="")
    version = Column(Integer, default=1, comment="配置版本号")
    inherited_from = Column(
        Integer, ForeignKey("semesters.id"), nullable=True, comment="继承来源学期ID"
    )
    description = Column(String(200), default="")
    created_by = Column(String(50), default="", comment="创建者")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("semester_id", "key", name="uq_semester_config"),
        Index("idx_semester_config_semester", "semester_id"),
    )
    semester = relationship("Semester", foreign_keys=[semester_id])
    source_semester = relationship("Semester", foreign_keys=[inherited_from])


class SemesterConfigHistory(Base):
    """学期配置版本快照表：保存每次写入/回滚的历史（key/value/version）

    semester_configs 表保持 (semester_id, key) 唯一存当前值；
    历史版本存此快照表，支持回滚追溯（回避 SQLite 约束 batch 迁移）。
    """

    __tablename__ = "semester_config_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    key = Column(String(50), nullable=False)
    value = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, index=True)
    action = Column(String(20), nullable=False, default="SAVE", comment="SAVE/ROLLBACK/INHERIT")
    operator = Column(String(50), nullable=True, default="")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("ix_config_history_semester_version", "semester_id", "version"),)


# ════════════════════════════════════
# 多校区支持
# ════════════════════════════════════


class School(Base):
    """校区/学校模型"""

    __tablename__ = "schools"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    config_json = Column(Text, default="{}", comment="校区级配置 JSON")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


# ════════════════════════════════════
# 服务注册表（持久化配置）
# ════════════════════════════════════


class ServiceConfig(Base):
    """服务配置持久化表"""

    __tablename__ = "service_configs"
    id = Column(Integer, primary_key=True)
    service_code = Column(String(50), unique=True, nullable=False, index=True, comment="服务代码")
    name = Column(String(100), nullable=False, comment="服务名称")
    description = Column(Text, default="", comment="服务描述")
    api_prefix = Column(String(100), nullable=False, comment="API 前缀")
    enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    required_permissions = Column(Text, default="", comment="所需权限，逗号分隔")
    allowed_roles = Column(Text, default="", comment="允许角色，逗号分隔")
    rate_limit = Column(Integer, default=100, nullable=False, comment="限流阈值（请求数/窗口）")
    rate_limit_window = Column(Integer, default=60, nullable=False, comment="限流窗口（秒）")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ════════════════════════════════════
# 数据锁定机制
# ════════════════════════════════════


class LockLevel(enum.StrEnum):
    """锁定级别枚举"""

    none = "none"  # 无锁定
    soft = "soft"  # 软锁定：提示只读，管理员可强制编辑
    hard = "hard"  # 硬锁定：仅 DATA_UNLOCK 权限可解锁
    semester = "semester"  # 学期级锁定：整学期只读（归档态）


class DataLock(Base):
    """通用数据锁定表"""

    __tablename__ = "data_locks"
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    entity_type = Column(
        String(50), nullable=False, index=True, comment="实体类型：class/student/score/exam等"
    )
    entity_id = Column(Integer, nullable=False, index=True, comment="实体ID，0表示表级锁定")
    lock_level = Column(SQLEnum(LockLevel), default=LockLevel.soft, nullable=False)
    locked_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="锁定操作人")
    locked_at = Column(DateTime, server_default=func.now())
    reason = Column(Text, default="", comment="锁定理由")
    __table_args__ = (
        Index("idx_data_lock_entity", "entity_type", "entity_id"),
        Index("idx_data_lock_semester", "semester_id"),
    )
    semester = relationship("Semester")


# ════════════════════════════════════
# 幂等性键表
# ════════════════════════════════════


class IdempotencyKey(Base):
    """幂等性键表：防止重复请求"""

    __tablename__ = "idempotency_keys"
    key = Column(String(64), primary_key=True)
    response_body = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=True)
    response_headers = Column(Text, nullable=True)  # JSON 存储
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False, index=True)
    __table_args__ = (UniqueConstraint("key", name="uq_idempotency_key"),)


# ════════════════════════════════════
# Outbox 事件表
# ════════════════════════════════════


class OutboxEvent(Base):
    """Outbox 事件表：保证事件可靠投递"""

    __tablename__ = "outbox_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_id = Column(String(64), nullable=False, index=True)
    payload = Column(Text, nullable=False)  # JSON
    trace_id = Column(String(64), nullable=True, index=True)
    retry_count = Column(Integer, default=0)
    dead_letter = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    processed_at = Column(DateTime, nullable=True)
    __table_args__ = (Index("ix_outbox_unprocessed", "processed_at", "dead_letter"),)


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


class DeviceTrust(Base):
    """设备信任表：存储用户受信设备，支持免密登录"""

    __tablename__ = "device_trusts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_name = Column(String(100), nullable=False)
    fingerprint = Column(String(64), nullable=False, index=True)
    user_agent = Column(String(500), nullable=True)
    ip = Column(String(45), nullable=True)
    trusted = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False, index=True)
    last_used_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "fingerprint", name="uq_user_device_fingerprint"),
        Index("idx_device_trust_user_trusted", "user_id", "trusted"),
    )

    user = relationship("User")


# ════════════════════════════════════
# 数据锁定机制
# ════════════════════════════════════


class SemesterStatsCache(Base):
    """学期统计预计算缓存表"""

    __tablename__ = "semester_stats_cache"
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    entity_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="实体类型：student/class/subject/exam/school",
    )
    entity_id = Column(Integer, nullable=False, index=True, comment="实体ID，0表示学期汇总")
    metric_key = Column(
        String(50), nullable=False, index=True, comment="指标键：count/avg_score/pass_rate/rank等"
    )
    metric_value = Column(Float, nullable=False, comment="指标值")
    version = Column(Integer, default=1, comment="缓存版本，重算时递增")
    computed_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        UniqueConstraint(
            "semester_id", "entity_type", "entity_id", "metric_key", name="uq_semester_stat"
        ),
        Index("idx_stats_semester_entity", "semester_id", "entity_type", "entity_id"),
    )
    semester = relationship("Semester")


# ═══════════════════════════════════
# 字段动态增删机制（Sprint 3.7 核心：灵活度高、耦合低）
# ═══════════════════════════════════


class FieldDefinition(Base):
    """字段注册表：定义各实体的可扩展字段（自定义字段可增删，系统字段受保护）

    entity_type: student / teacher / class / exam / score / ...
    field_type: string / int / float / date / enum / select / bool
    """

    __tablename__ = "field_definitions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(30), nullable=False, index=True, comment="所属实体类型")
    field_key = Column(String(50), nullable=False, comment="字段键（写入 ext_json）")
    label = Column(String(100), nullable=False, comment="显示名称")
    field_type = Column(
        String(20), default="string", comment="string/int/float/date/enum/select/bool"
    )
    options = Column(Text, nullable=True, comment="enum/select 选项，JSON 数组")
    required = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    is_system = Column(Boolean, default=False, comment="系统字段不可删除")
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("entity_type", "field_key", name="uq_field_definition"),)


class ReportTemplate(Base):
    """报表模板（M5-D5）：名称/类型/文件路径/版本/变量列表"""

    __tablename__ = "report_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="模板名称")
    template_type = Column(
        String(20), nullable=False, default="excel", comment="excel/word/certificate"
    )
    file_path = Column(String(300), nullable=False, comment="模板文件相对路径")
    version = Column(Integer, nullable=False, default=1, comment="版本号（每次更新+1）")
    variables = Column(Text, nullable=True, comment="变量列表，JSON 数组 [{key,label}]")
    description = Column(String(300), nullable=True, default="")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_by = Column(String(50), nullable=True, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_report_template_version"),
        Index("idx_report_template_name", "name"),
    )


# 通用扩展列混入：各业务表加 ext_json 存自定义字段（SQLite JSON1 支持 json_extract 查询）
def _ext_json_column() -> Column:
    """返回通用 ext_json 扩展列定义（JSON 文本）"""
    return Column(Text, nullable=True, comment="自定义扩展字段（JSON 对象）")


# ════════════════════════════════════
# 字典管理（M1：对齐若依 #6 字典）
# ════════════════════════════════════


class DictType(Base):
    """字典类型"""

    __tablename__ = "dict_types"
    id = Column(Integer, primary_key=True)
    dict_type = Column(String(64), unique=True, nullable=False, comment="字典类型编码")
    dict_name = Column(String(64), default="", comment="字典类型名称")
    status = Column(String(4), default="0", comment="状态: 0正常/1停用")
    remark = Column(String(255), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DictData(Base):
    """字典数据"""

    __tablename__ = "dict_data"
    id = Column(Integer, primary_key=True)
    dict_type = Column(String(64), nullable=False, comment="字典类型编码", index=True)
    dict_label = Column(String(64), default="", comment="显示标签（中文）")
    dict_value = Column(String(64), default="", comment="实际值")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(String(4), default="0", comment="状态: 0正常/1停用")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_dict_type_sort", "dict_type", "sort_order"),)


# ════════════════════════════════════
# M2：通知公告 / 登录日志 / 在线用户（对齐若依 #8/#10/#11）
# ════════════════════════════════════


class Notice(Base):
    """通知公告"""

    __tablename__ = "notices"
    id = Column(Integer, primary_key=True)
    title = Column(String(120), nullable=False, comment="标题")
    content = Column(Text, default="")
    notice_type = Column(String(10), default="notice", comment="类型: notice通知/announce公告")
    status = Column(String(4), default="0", comment="状态: 0发布/1草稿/2已下线")
    publisher = Column(String(32), default="", comment="发布人")
    read_count = Column(Integer, default=0, comment="阅读数")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class NoticeRead(Base):
    """公告已读记录"""

    __tablename__ = "notice_reads"
    id = Column(Integer, primary_key=True)
    notice_id = Column(Integer, ForeignKey("notices.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, nullable=False)
    read_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("notice_id", "user_id", name="uq_notice_user"),)


class LoginLog(Base):
    """登录日志"""

    __tablename__ = "login_logs"
    id = Column(Integer, primary_key=True)
    username = Column(String(32), default="")
    status = Column(String(4), default="0", comment="0成功/1失败")
    msg = Column(String(120), default="")
    ip = Column(String(45), default="")
    user_agent = Column(String(200), default="")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_loginlog_time", "created_at"),)


class OnlineUser(Base):
    """在线用户（登录会话跟踪）"""

    __tablename__ = "online_users"
    id = Column(Integer, primary_key=True)
    token_fp = Column(
        String(64), unique=True, nullable=False, comment="token 指纹（sha256 前 16 位）"
    )
    username = Column(String(32), default="")
    display_name = Column(String(64), default="")
    ip = Column(String(45), default="")
    user_agent = Column(String(200), default="")
    login_at = Column(DateTime, server_default=func.now())
    expire_at = Column(DateTime, nullable=True)
    __table_args__ = (Index("idx_online_expire", "expire_at"),)


# ── 外部模块模型注册（确保全部表进入 Base.metadata，init_db 可建全量表）──
# 模型按业务模块分散定义在 services/ 下，必须在此 import 触发注册，
# 否则 Base.metadata.create_all() 不会创建对应表（如 stored_files）。
from edu_system.services.storage import StoredFile  # noqa: E402, F401  (注册 stored_files 表)
