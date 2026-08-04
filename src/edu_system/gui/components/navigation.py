"""
侧边栏导航组件 - 基于 Fluent Design
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import CaptionLabel
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import NavigationItemPosition, NavigationPushButton, NavigationWidget

from ..design_system import ColorRole, Spacing, Typography, get_color, get_font, get_spacing


class NavSection(Enum):
    """导航分区"""

    MAIN = "main"  # 主要功能
    TEACHING = "teaching"  # 教学管理
    ACADEMIC = "academic"  # 教务管理
    SYSTEM = "system"  # 系统设置


@dataclass
class NavItem:
    """导航项"""

    route_key: str  # 路由键
    title: str  # 显示标题
    icon: Any = FIF.HOME  # Fluent 图标
    section: NavSection = NavSection.MAIN
    badge: str = ""  # 徽标文本（如 "9+"）
    tooltip: str = ""  # 悬浮提示
    enabled: bool = True  # 是否启用
    roles: list[str] = None  # 允许的角色


# 默认导航配置
DEFAULT_NAV_ITEMS = [
    # 主要功能
    NavItem("dashboard", "仪表盘", FIF.HOME, NavSection.MAIN, tooltip="系统概览"),
    NavItem("stats", "统计分析", FIF.PIE_SINGLE, NavSection.MAIN, tooltip="成绩统计、质量分析"),
    # 教学管理
    NavItem("students", "学生档案", FIF.PEOPLE, NavSection.TEACHING, tooltip="学生信息、学籍管理"),
    NavItem(
        "teachers", "教师管理", FIF.EDUCATION, NavSection.TEACHING, tooltip="教师信息、任课安排"
    ),
    NavItem("classes", "班级管理", FIF.LIBRARY, NavSection.TEACHING, tooltip="班级、分班、调课"),
    NavItem("exams", "考试管理", FIF.DOCUMENT, NavSection.TEACHING, tooltip="考试安排、监考、成绩"),
    NavItem("scores", "成绩录入", FIF.EDIT, NavSection.TEACHING, tooltip="成绩录入、导入、排名"),
    NavItem(
        "attendance", "考勤管理", FIF.CALENDAR, NavSection.TEACHING, tooltip="考勤打卡、请假、统计"
    ),
    # 教务管理
    NavItem(
        "academic_years",
        "学年学期",
        FIF.DATE_TIME,
        NavSection.ACADEMIC,
        tooltip="学年/学期配置、切换、归档",
    ),
    NavItem(
        "settings", "系统配置", FIF.SETTING, NavSection.ACADEMIC, tooltip="全局/学期级配置、继承"
    ),
    NavItem(
        "data_locks", "数据锁定", FIF.CANCEL, NavSection.ACADEMIC, tooltip="软/硬/学期锁、批量操作"
    ),
    NavItem(
        "reports", "报表打印", FIF.PRINT, NavSection.ACADEMIC, tooltip="成绩单、名册、证书套打"
    ),
    # 系统设置
    NavItem("users", "用户权限", FIF.PEOPLE, NavSection.SYSTEM, tooltip="用户、角色、权限管理"),
    NavItem(
        "services",
        "服务管理",
        FIF.APPLICATION,
        NavSection.SYSTEM,
        tooltip="API 服务启用、限流、权限",
    ),
    NavItem(
        "scheduler", "定时任务", FIF.HISTORY, NavSection.SYSTEM, tooltip="备份、归档、统计重算调度"
    ),
    NavItem("storage", "文件存储", FIF.FOLDER, NavSection.SYSTEM, tooltip="附件、导入导出文件管理"),
    NavItem("audit", "审计日志", FIF.INFO, NavSection.SYSTEM, tooltip="操作审计、数据变更追踪"),
]


class SidebarWidget(QWidget):
    """侧边栏导航组件"""

    # 信号：导航项点击
    navigation_clicked = pyqtSignal(str)  # route_key

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nav_items: dict[str, NavItem] = {}
        self._buttons: dict[str, NavigationPushButton] = {}
        self._current_route = ""
        self._collapsed = False

        self._setup_ui()
        self._register_default_items()

    def _setup_ui(self):
        self.setFixedWidth(260)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部 Logo 区域
        self.logo_widget = QWidget()
        self.logo_widget.setFixedHeight(64)
        self.logo_widget.setStyleSheet(
            f"""
            background-color: {get_color(ColorRole.SURFACE)};
            border-bottom: 1px solid {get_color(ColorRole.OUTLINE_VARIANT)};
        """
        )
        logo_layout = QHBoxLayout(self.logo_widget)
        logo_layout.setContentsMargins(16, 0, 16, 0)

        from edu_system.config.ui_config import get_config

        _school = getattr(get_config(), "school_name", "示例学校") or "示例学校"
        self.logo_label = QLabel(_school)
        self.logo_label.setFont(get_font(Typography.TITLE_LARGE))
        self.logo_label.setStyleSheet(f"color: {get_color(ColorRole.PRIMARY)};")
        logo_layout.addWidget(self.logo_label)
        logo_layout.addStretch()

        # 折叠按钮
        from qfluentwidgets import TransparentToolButton

        self.collapse_btn = TransparentToolButton(FIF.MENU)
        self.collapse_btn.setFixedSize(32, 32)
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        logo_layout.addWidget(self.collapse_btn)

        main_layout.addWidget(self.logo_widget)

        # 导航区域（使用 Fluent NavigationWidget）
        self.nav_widget = NavigationWidget()
        self.nav_widget.setExpandWidth(260)
        self.nav_widget.setMinimumWidth(64)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidget(self.nav_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        main_layout.addWidget(scroll, 1)

        # 底部版本信息
        self.version_label = CaptionLabel("开发版")
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.setStyleSheet(
            f"""
            color: {get_color(ColorRole.OUTLINE)};
            padding: {get_spacing(Spacing.SM)}px;
            border-top: 1px solid {get_color(ColorRole.OUTLINE_VARIANT)};
        """
        )
        main_layout.addWidget(self.version_label)

    def _register_default_items(self):
        """注册默认导航项"""
        for item in DEFAULT_NAV_ITEMS:
            self.add_navigation_item(item)

    def add_navigation_item(self, item: NavItem):
        """添加导航项"""
        self._nav_items[item.route_key] = item

        # 创建导航按钮
        btn = NavigationPushButton(item.icon, item.title, self.nav_widget)
        btn.setToolTip(item.tooltip or item.title)

        if item.badge:
            # NavigationPushButton 不直接支持 badge，这里简化处理
            pass

        # 连接点击信号
        btn.clicked.connect(lambda checked, key=item.route_key: self._on_item_clicked(key))

        # 根据分区添加到不同位置
        if item.section == NavSection.MAIN:
            self.nav_widget.addItem(
                routeKey=item.route_key,
                icon=item.icon,
                text=item.title,
                onClick=lambda key=item.route_key: self._on_item_clicked(key),
                position=NavigationItemPosition.TOP,
            )
        elif item.section == NavSection.TEACHING:
            self.nav_widget.addItem(
                routeKey=item.route_key,
                icon=item.icon,
                text=item.title,
                onClick=lambda key=item.route_key: self._on_item_clicked(key),
                position=NavigationItemPosition.TOP,
            )
        elif item.section == NavSection.ACADEMIC:
            self.nav_widget.addItem(
                routeKey=item.route_key,
                icon=item.icon,
                text=item.title,
                onClick=lambda key=item.route_key: self._on_item_clicked(key),
                position=NavigationItemPosition.TOP,
            )
        elif item.section == NavSection.SYSTEM:
            self.nav_widget.addItem(
                routeKey=item.route_key,
                icon=item.icon,
                text=item.title,
                onClick=lambda key=item.route_key: self._on_item_clicked(key),
                position=NavigationItemPosition.BOTTOM,
            )

        self._buttons[item.route_key] = btn

    def _on_item_clicked(self, route_key: str):
        """导航项点击"""
        if route_key == self._current_route:
            return

        self._current_route = route_key
        self.nav_widget.setCurrentItem(route_key)
        self.navigation_clicked.emit(route_key)

    def set_current_route(self, route_key: str):
        """设置当前选中路由"""
        if route_key in self._nav_items:
            self._on_item_clicked(route_key)

    def get_current_route(self) -> str:
        return self._current_route

    def _toggle_collapse(self):
        """切换折叠状态"""
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.setFixedWidth(64)
            self.logo_label.hide()
            self.nav_widget.setExpandWidth(64)
            self.collapse_btn.setIcon(FIF.MENU)
        else:
            self.setFixedWidth(260)
            self.logo_label.show()
            self.nav_widget.setExpandWidth(260)
            self.collapse_btn.setIcon(FIF.MENU)

    def set_item_enabled(self, route_key: str, enabled: bool):
        """设置导航项启用状态"""
        if route_key in self._buttons:
            self._buttons[route_key].setEnabled(enabled)
            self._nav_items[route_key].enabled = enabled

    def set_item_badge(self, route_key: str, badge: str):
        """设置徽标"""
        if route_key in self._nav_items:
            self._nav_items[route_key].badge = badge
            # NavigationPushButton 需要自定义绘制 badge

    def update_user_role(self, roles: list[str]):
        """根据用户角色更新导航可见性"""
        for route_key, item in self._nav_items.items():
            if item.roles:
                visible = any(r in roles for r in item.roles)
                if route_key in self._buttons:
                    self._buttons[route_key].setVisible(visible)


class TopBarWidget(QWidget):
    """顶部栏 - 搜索、通知、用户菜单、命令面板"""

    # 信号
    search_requested = pyqtSignal(str)
    command_palette_requested = pyqtSignal()
    user_menu_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(48)
        self.setStyleSheet(
            f"""
            background-color: {get_color(ColorRole.SURFACE)};
            border-bottom: 1px solid {get_color(ColorRole.OUTLINE_VARIANT)};
        """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # 左侧：面包屑/页面标题
        self.title_label = QLabel("仪表盘")
        self.title_label.setFont(get_font(Typography.TITLE_MEDIUM))
        self.title_label.setStyleSheet(f"color: {get_color(ColorRole.ON_SURFACE)};")
        layout.addWidget(self.title_label)
        layout.addStretch()

        # 中间：全局搜索
        from qfluentwidgets import SearchLineEdit

        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText("搜索学生、教师、班级... (Ctrl+F)")
        self.search_input.setFixedWidth(360)
        self.search_input.setFixedHeight(36)
        self.search_input.searchSignal.connect(self.search_requested)
        layout.addWidget(self.search_input)

        layout.addStretch()

        # 右侧：功能按钮
        from qfluentwidgets import AvatarWidget, TransparentToolButton

        # 命令面板按钮
        self.cmd_palette_btn = TransparentToolButton(FIF.SEARCH)
        self.cmd_palette_btn.setToolTip("命令面板 (Ctrl+K)")
        self.cmd_palette_btn.setFixedSize(36, 36)
        self.cmd_palette_btn.clicked.connect(self.command_palette_requested.emit)
        layout.addWidget(self.cmd_palette_btn)

        # 通知按钮
        self.notify_btn = TransparentToolButton(FIF.BELL)
        self.notify_btn.setToolTip("通知中心")
        self.notify_btn.setFixedSize(36, 36)
        layout.addWidget(self.notify_btn)

        # 用户头像
        self.avatar = AvatarWidget("教务主任")
        self.avatar.setRadius(18)
        self.avatar.setFixedSize(36, 36)
        self.avatar.clicked.connect(self.user_menu_requested.emit)
        layout.addWidget(self.avatar)

    def set_title(self, title: str, breadcrumb: list[str] = None):
        """设置页面标题和面包屑"""
        if breadcrumb:
            text = " > ".join(breadcrumb + [title])
        else:
            text = title
        self.title_label.setText(text)

    def set_user(self, name: str, avatar_path: str = None):
        """设置用户信息"""
        self.avatar.setText(name)
        if avatar_path:
            self.avatar.setImage(avatar_path)


# ===== 全局实例 =====

sidebar = None
top_bar = None


def create_sidebar(parent=None) -> SidebarWidget:
    """创建侧边栏"""
    global sidebar
    sidebar = SidebarWidget(parent)
    return sidebar


def create_top_bar(parent=None) -> TopBarWidget:
    """创建顶部栏"""
    global top_bar
    top_bar = TopBarWidget(parent)
    return top_bar
