"""视图工厂"""

from PyQt5.QtWidgets import QWidget
from sqlalchemy.orm import Session

from edu_system.gui.views.base import BaseView, WorkbenchWidget

# 工作台配置（模块级常量，供 main_window 导入）
WORKBENCH_CONFIGS = [
    # 学生管理
    (
        0,
        "学生管理",
        [
            ("学生信息", 0),
            ("学籍变动", 5),
            ("新生注册", 6),
            ("升年级/毕业", 7),
        ],
    ),
    # 教师管理 - TeacherView 内部已有两个标签页
    (
        1,
        "教师管理",
        [
            ("教师管理", 1),
        ],
    ),
    # 考试管理 - ExamView / ScoreView / ReportView 是不同视图
    (
        2,
        "考试管理",
        [
            ("考试管理", 2),
            ("成绩管理", 3),
            ("报表生成", 4),
        ],
    ),
    # 基础配置
    (
        3,
        "基础配置",
        [
            ("学期设置", 8),
            ("班级信息", 10),
            ("教室位置", 11),
        ],
    ),
    # 系统维护
    (
        4,
        "系统维护",
        [
            ("系统设置", 13),
            ("数据维护", 9),
            ("初始化系统", 12),
        ],
    ),
]


def build_view(idx: int, session: Session) -> QWidget:
    from edu_system.gui.views.class_management import ClassView
    from edu_system.gui.views.classroom import ClassroomView
    from edu_system.gui.views.exam import ExamView
    from edu_system.gui.views.init_system import InitView
    from edu_system.gui.views.remaining import EnrollmentView, PromotionView, RegistrationView
    from edu_system.gui.views.report import ReportView
    from edu_system.gui.views.score import ScoreView
    from edu_system.gui.views.semester import SemesterView
    from edu_system.gui.views.settings import SettingsView
    from edu_system.gui.views.student import StudentView
    from edu_system.gui.views.system_config import SystemConfigView
    from edu_system.gui.views.teacher import TeacherView

    mapping = {
        0: StudentView,
        1: TeacherView,
        2: ExamView,
        3: ScoreView,
        4: ReportView,
        5: EnrollmentView,
        6: RegistrationView,
        6: RegistrationView,
        7: PromotionView,
        8: SemesterView,
        9: SettingsView,
        10: ClassView,
        11: ClassroomView,
        12: InitView,
        13: SystemConfigView,
    }
    cls = mapping.get(idx)
    return cls(session) if cls else BaseView(session)


def build_workbench(idx: int, session: Session) -> QWidget:
    """构建工作台，idx 0-4 对应 5 个工作台"""

    for wb_idx, title, tabs in WORKBENCH_CONFIGS:
        if wb_idx == idx:
            return WorkbenchWidget(None, tabs, title)  # session=None 先占位
    return BaseView(None)
