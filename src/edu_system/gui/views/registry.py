"""
视图注册表 — 将 view_id 映射到实际视图类
桌面端与 Web 端共享此映射契约
"""

from typing import Any

# 视图 ID -> (视图类, 所需参数)
VIEW_REGISTRY = {
    # 首页域
    "overview": ("edu_system.gui.views.dashboard", "DashboardView", ["session"]),
    "quick": ("edu_system.gui.views.dashboard", "QuickActionsView", ["session"]),
    "status": ("edu_system.gui.views.dashboard", "DataStatusView", ["session"]),
    # 学生管理域
    "student_list": ("edu_system.gui.views.student", "StudentView", ["session"]),
    "student_register": ("edu_system.gui.views.remaining", "RegistrationView", ["session"]),
    "student_movement": ("edu_system.gui.views.remaining", "EnrollmentView", ["session"]),
    "student_promotion": ("edu_system.gui.views.remaining", "PromotionView", ["session"]),
    # 成绩管理域
    "score_entry": ("edu_system.gui.views.score", "ScoreView", ["session"]),
    "score_query": ("edu_system.gui.views.score", "ScoreView", ["session"]),
    "score_stats": ("edu_system.gui.views.score_stats", "ScoreStatsView", ["session"]),
    "score_rank": ("edu_system.gui.views.score", "ScoreView", ["session"]),
    # 考试管理域
    "exam_manage": ("edu_system.gui.views.exam", "ExamView", ["session", "view_id"]),
    "exam_rooms": ("edu_system.gui.views.exam", "ExamView", ["session", "view_id"]),
    "exam_invigilation": ("edu_system.gui.views.exam", "ExamView", ["session", "view_id"]),
    "exam_admit": ("edu_system.gui.views.exam", "ExamView", ["session", "view_id"]),
    # 教师管理域
    "teacher_list": ("edu_system.gui.views.teacher", "TeacherView", ["session", "view_id"]),
    "teacher_assign": ("edu_system.gui.views.teacher", "TeacherView", ["session", "view_id"]),
    # 班级管理域
    "class_list": ("edu_system.gui.views.class_management", "ClassView", ["session"]),
    # 教室管理域
    "classroom_list": ("edu_system.gui.views.classroom", "ClassroomView", ["session"]),
    # 学期设置域
    "semester": ("edu_system.gui.views.semester", "SemesterView", ["session"]),
    # 系统设置域
    "users": ("edu_system.gui.views.user_permission", "UserPermissionView", ["session"]),
    "data_maintenance": (
        "edu_system.gui.views.data_maintenance",
        "DataMaintenanceView",
        ["session"],
    ),
    "system_config": ("edu_system.gui.views.system_config", "SystemConfigView", ["session"]),
    "init": ("edu_system.gui.views.init_system", "InitView", ["session"]),
    "dict": ("edu_system.gui.views.dict_manager", "DictManagerView", ["session"]),
    "report": ("edu_system.gui.views.report", "ReportView", ["session", "view_id"]),
}


def build_view(view_id: str, session: Any) -> Any:
    """
    根据 view_id 实例化对应的视图类

    Args:
        view_id: 视图标识符（对应 ui_config.json 中的 view 字段）
        session: SQLAlchemy Session

    Returns:
        视图实例

    Raises:
        ValueError: view_id 未注册
    """
    if view_id not in VIEW_REGISTRY:
        raise ValueError(f"未知视图 ID: {view_id}")

    module_path, class_name, param_names = VIEW_REGISTRY[view_id]

    # 动态导入模块
    module = __import__(module_path, fromlist=[class_name])
    view_class = getattr(module, class_name)

    # 构造参数：session 必传 + 视图 id（用于定位视类内部 Tab）
    kwargs = {}
    for name in param_names or ["session"]:
        if name == "session":
            kwargs[name] = session
        elif name == "view_id":
            kwargs[name] = view_id

    return view_class(**kwargs)


def get_registered_views() -> list[str]:
    """获取所有已注册的 view_id 列表"""
    return list(VIEW_REGISTRY.keys())


def register_view(
    view_id: str, module_path: str, class_name: str, param_names: list[str] | None = None
) -> None:
    """运行时注册新视图（供插件/扩展使用）"""
    if param_names is None:
        param_names = ["session"]
    VIEW_REGISTRY[view_id] = (module_path, class_name, param_names)
