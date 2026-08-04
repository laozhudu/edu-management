"""
测试数据 Schema 定义
定义标准测试数据集结构：3 学年 × 2 学期 × 3 年级 × 12 班 × 50 人 = 10,800 学生全维度数据
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class StudentStatus(str, Enum):
    """学生状态"""

    ENROLLED = "在校"
    TRANSFERRED_OUT = "转出"
    SUSPENDED = "休学"
    GRADUATED = "毕业"
    DROPPED = "退学"


class TeacherTitle(str, Enum):
    """教师职称"""

    NONE = "无"
    PRIMARY = "初级"
    INTERMEDIATE = "中级"
    SENIOR = "高级"
    SPECIAL = "特级"


class MovementType(str, Enum):
    """学籍变动类型"""

    TRANSFER_CLASS = "转班"
    SUSPEND = "休学"
    RESUME = "复学"
    TRANSFER_OUT = "转出"
    TRANSFER_IN = "转入"
    GRADUATE = "毕业"
    DROP = "退学"


class ExamType(str, Enum):
    """考试类型"""

    MIDTERM = "期中"
    FINAL = "期末"
    MONTHLY = "月考"
    MOCK = "模拟"
    MAKEUP = "补考"


@dataclass
class AcademicYearData:
    """学年数据"""

    name: str  # "2024-2025"
    sort_order: int
    is_active: bool
    description: str = ""
    semesters: list["SemesterData"] = field(default_factory=list)


@dataclass
class SemesterData:
    """学期数据"""

    academic_year_id: int
    year_start: int
    semester: str  # "1" 或 "2"
    label: str  # "2024-2025 第1学期"
    sort_order: int
    is_active: bool
    status: str  # draft/active/locked/archived
    start_date: date | None = None
    end_date: date | None = None
    students: list["StudentData"] = field(default_factory=list)
    teachers: list["TeacherData"] = field(default_factory=list)
    classes: list["ClassData"] = field(default_factory=list)
    exams: list["ExamData"] = field(default_factory=list)


@dataclass
class GradeData:
    """年级数据"""

    name: str  # "初一", "初二", "初三"
    sort_order: int
    classes: list["ClassData"] = field(default_factory=list)


@dataclass
class ClassData:
    """班级数据"""

    grade_id: int
    semester_id: int
    name: str  # "1班", "2班"
    head_teacher: str = ""
    class_type: str = "普通班"
    room: str = ""
    students: list["StudentData"] = field(default_factory=list)


@dataclass
class StudentData:
    """学生数据"""

    class_id: int
    semester_id: int
    name: str
    gender: str  # "男"/"女"
    student_no: str  # 座号
    student_code: str  # 全国学籍号
    id_card: str  # 身份证号
    birth_date: date
    ethnicity: str = "汉族"
    native_place: str = ""
    political_status: str = "群众"
    phone: str = ""
    address: str = ""
    hukou_addr: str = ""
    enroll_year: int = 2024
    exam_no: str = ""  # 考号
    boarding: str = "走读"  # 走读/住校
    multiple_birth: str = ""
    health_status: str = ""
    is_disabled: str = "否"
    left_behind: str = "否"
    guardian1_name: str = ""
    guardian1_relation: str = ""
    guardian1_phone: str = ""
    guardian1_work: str = ""
    guardian1_edu: str = ""
    guardian1_id_card: str = ""
    guardian2_name: str = ""
    guardian2_relation: str = ""
    guardian2_phone: str = ""
    guardian2_work: str = ""
    guardian2_edu: str = ""
    guardian2_id_card: str = ""
    status: str = "在校"
    photo: bytes | None = None
    photo_mime: str = ""
    note: str = ""


@dataclass
class TeacherData:
    """教师数据"""

    semester_id: int
    name: str
    gender: str
    phone: str = ""
    title: str = ""  # 职称
    education: str = ""
    degree: str = ""
    political_status: str = ""
    birth_date: date | None = None
    work_start_date: date | None = None
    graduation_date: date | None = None
    staff_no: str = ""
    note: str = ""


@dataclass
class SubjectData:
    """学科数据"""

    name: str
    full_mark: float = 100
    pass_line: float = 60
    good_line: float = 80
    excellent_line: float = 90
    low_line: float = 30
    sort_order: int = 0


@dataclass
class ExamData:
    """考试数据"""

    semester_id: int
    name: str
    exam_date: date | None = None
    grade_id: int | None = None
    exam_type: str = "期中"
    note: str = ""
    is_makeup: bool = False
    subjects: list["ExamSubjectSettingData"] = field(default_factory=list)


@dataclass
class ExamSubjectSettingData:
    """考试学科设置"""

    exam_id: int
    subject_id: int
    full_mark: float = 100
    pass_line: float = 60
    good_line: float = 80
    excellent_line: float = 90
    low_line: float = 30


@dataclass
class ScoreData:
    """成绩数据"""

    exam_id: int
    student_id: int
    subject_id: int
    score: float | None = None  # NULL = 缺考
    is_makeup: bool = False
    is_published: bool = False


@dataclass
class ClassSubjectData:
    """任课数据"""

    semester_id: int
    class_id: int
    subject_id: int
    teacher_id: int | None = None


@dataclass
class StudentMovementData:
    """学籍变动数据"""

    student_id: int
    semester_id: int
    move_type: str  # 转班/休学/复学/转出/转入/毕业/退学
    move_date: date | None = None
    from_class_id: int | None = None
    to_class_id: int | None = None
    reason: str = ""
    operator: str = "system"


@dataclass
class ClassroomData:
    """教室数据"""

    semester_id: int
    class_id: int
    floor: str = ""
    room_no: str = ""
    capacity: int = 50


@dataclass
class GlobalSettingData:
    """全局配置"""

    key: str
    value: str
    description: str = ""


@dataclass
class SemesterConfigData:
    """学期配置"""

    semester_id: int
    key: str
    value: str
    version: int = 1
    inherited_from: int | None = None
    description: str = ""


# ===== 完整测试数据集 Schema =====


@dataclass
class TestDataSet:
    """完整测试数据集"""

    version: str = "1.0.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = "标准测试数据集：3学年×2学期×3年级×12班×50人=10,800学生"

    # 基础数据
    academic_years: list[AcademicYearData] = field(default_factory=list)
    grades: list[GradeData] = field(default_factory=list)
    subjects: list[SubjectData] = field(default_factory=list)

    # 学期相关数据（按学期分组）
    semesters: list[SemesterData] = field(default_factory=list)

    # 配置
    global_settings: list[GlobalSettingData] = field(default_factory=list)

    # 校验和
    checksums: dict[str, str] = field(default_factory=dict)

    @property
    def all_teachers(self) -> list["TeacherData"]:
        """获取所有学期的教师"""
        teachers = []
        for sem in self.semesters:
            teachers.extend(sem.teachers)
        return teachers

    @property
    def all_students(self) -> list["StudentData"]:
        """获取所有学期的学生"""
        students = []
        for sem in self.semesters:
            students.extend(sem.students)
        return students

    @property
    def all_classes(self) -> list["ClassData"]:
        """获取所有学期的班级"""
        classes = []
        for sem in self.semesters:
            classes.extend(sem.classes)
        return classes

    @property
    def all_exams(self) -> list["ExamData"]:
        """获取所有学期的考试"""
        exams = []
        for sem in self.semesters:
            exams.extend(sem.exams)
        return exams

    @property
    def all_classes(self) -> list["ClassData"]:
        """获取所有学期的班级"""
        classes = []
        for sem in self.semesters:
            classes.extend(sem.classes)
        return classes

    @property
    def all_students(self) -> list["StudentData"]:
        """获取所有学期的学生"""
        students = []
        for sem in self.semesters:
            students.extend(sem.students)
        return students

    def get_total_students(self) -> int:
        """获取总学生数"""
        total = 0
        for sem in self.semesters:
            total += len(sem.students)
        return total

    def get_coverage_summary(self) -> dict:
        """获取覆盖度摘要"""
        return {
            "academic_years": len(self.academic_years),
            "semesters": len(self.semesters),
            "grades": len(self.grades),
            "subjects": len(self.subjects),
            "total_students": self.get_total_students(),
            "total_classes": sum(len(s.classes) for s in self.semesters),
            "total_teachers": sum(len(s.teachers) for s in self.semesters),
            "total_exams": sum(len(s.exams) for s in self.semesters),
        }


# ===== 典型场景标签 =====

SCENARIO_TAGS = {
    "new_student_enrollment": "新生入学",
    "class_transfer": "转班",
    "suspend_resume": "休学复学",
    "grade_promotion": "升年级",
    "graduation": "毕业",
    "makeup_exam": "补考",
    "absent_exam": "缺考",
    "discipline": "违纪",
    "transfer_out": "转学",
    "resume_after_suspend": "休学复学",
    "score_entry": "成绩录入",
    "score_publish": "成绩发布",
    "score_lock": "成绩锁定",
    "config_inherit": "配置继承",
    "semester_archive": "学期归档",
    "attendance_daily": "日常考勤",
    "leave_approval": "请假审批",
    "offline_sync": "离线同步",
    "backup_restore": "备份恢复",
    "multi_device_concurrent": "多设备并发",
}

# ===== 边界值定义 =====

BOUNDARY_VALUES = {
    "student_name_max_len": 20,
    "student_code_format": r"^\d{18}$",  # 18位学籍号
    "id_card_format": r"^\d{17}[\dXx]$",  # 18位身份证
    "phone_format": r"^1[3-9]\d{9}$",  # 手机号
    "score_min": 0,
    "score_max": 150,
    "class_max_size": 60,
    "class_min_size": 1,
    "grade_levels": ["初一", "初二", "初三"],
    "semester_terms": ["1", "2"],
    "academic_year_format": r"^\d{4}-\d{4}$",
}
