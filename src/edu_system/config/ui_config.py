"""
UI 配置加载器 — 配置驱动 UI 的核心层
统一配置源：config/ui_config.json
所有可见元素（品牌/学校/版本/域/页签/图标/热键/状态栏/权限）单一来源
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """应用标识配置（品牌/学校/版本，全部可改，支持模板变量）"""

    name: str = "教务管理系统"
    name_short: str = "教务管理"
    school_name: str = "示例学校"
    window_title: str = "{school} {name} v{version}"
    version: str = "2.0.0"
    version_display: str = "v2.0"
    footer: str = "{school} · v{version}"


class TopBarConfig(BaseModel):
    """顶部栏配置"""

    show_semester_switcher: bool = True
    semester_placeholder: str = "{year} 第{n}学期"
    show_search: bool = True
    search_placeholder: str = "搜索学生 / 班级 / 考试… (⌘K)"
    show_command_palette: bool = True
    show_user_menu: bool = True
    show_notifications: bool = True
    shortcuts: dict[str, str] = Field(
        default_factory=lambda: {
            "command_palette": "Ctrl+K",
            "score_entry": "Ctrl+E",
            "refresh": "F5",
        }
    )


class ThemeConfig(BaseModel):
    """主题配置"""

    brand: str = "{school}{name}"
    accent_color: str = "#3498DB"
    sidebar_bg: str = "#2C3E50"
    sidebar_hover: str = "#34495E"
    content_bg: str = "#F5F6FA"
    density: str = "compact"  # compact / comfortable


class TabConfig(BaseModel):
    """页签配置"""

    id: str
    title: str
    view: str
    default: bool = False
    permissions: list[str] = Field(default_factory=list)  # 空=登录即可见


class DomainConfig(BaseModel):
    """一级域配置"""

    id: str
    title: str
    icon: str = ""
    order: int = 0
    badge_source: str | None = None  # student_count 等（用于侧栏角标）
    permissions: list[str] = Field(default_factory=list)  # 空=登录即可见（角色过滤）
    tabs: list[TabConfig]


class StatusBarItem(BaseModel):
    type: str
    label: str


class StatusBarConfig(BaseModel):
    left: list[dict[str, str]] = Field(default_factory=list)
    right: list[dict[str, str]] = Field(default_factory=list)


class UIConfig(BaseModel):
    """顶级 UI 配置"""

    app: Any = None
    topbar: Any = None
    theme: Any = None
    domains: list[dict[str, Any]] = Field(default_factory=list)
    statusbar: dict[str, list[dict[str, str]]] = Field(default_factory=dict)

    # 模板渲染用的变量值缓存
    _tmpl_vars: dict[str, str] = {}

    def model_post_init(self, __context: Any) -> None:
        # 延迟实例化子配置对象，避免循环导入
        from .ui_config import AppConfig, StatusBarConfig, ThemeConfig, TopBarConfig

        object.__setattr__(self, "app", AppConfig(**(self.app or {})))
        object.__setattr__(self, "topbar", TopBarConfig(**(self.topbar or {})))
        object.__setattr__(self, "theme", ThemeConfig(**(self.theme or {})))
        object.__setattr__(self, "statusbar", StatusBarConfig(**(self.statusbar or {})))
        self._build_template_vars()

    def _build_template_vars(self) -> None:
        self._tmpl_vars = {
            "school": self.app.school_name,
            "name": self.app.name,
            "version": self.app.version,
            "version_display": self.app.version_display,
        }

    def render(self, template: str) -> str:
        """渲染 {placeholders} 模板变量"""
        out = template
        for k, v in self._tmpl_vars.items():
            out = out.replace("{" + k + "}", str(v))
        return out

    @property
    def window_title(self) -> str:
        return self.render(self.app.window_title)

    @property
    def footer_text(self) -> str:
        return self.render(self.app.footer)

    @property
    def brand_text(self) -> str:
        return self.render(self.theme.brand)

    @property
    def domains_parsed(self) -> list[dict]:
        """返回解析后的域列表（包含已实例化的 DomainConfig）"""
        from .ui_config import DomainConfig, TabConfig

        result = []
        for d in self.domains:
            tabs = [TabConfig(**t) for t in d.get("tabs", [])]
            dc = DomainConfig(
                id=d["id"],
                title=d["title"],
                icon=d.get("icon", ""),
                order=d.get("order", 0),
                badge_source=d.get("badge_source"),
                permissions=d.get("permissions", []),
                tabs=tabs,
            )
            result.append(
                {
                    "id": dc.id,
                    "title": dc.title,
                    "icon": dc.icon,
                    "order": dc.order,
                    "badge_source": dc.badge_source,
                    "permissions": dc.permissions,
                    "tabs": tabs,
                }
            )
        return sorted(result, key=lambda x: x["order"])

    def filter_domains(self, user_roles: list[str]) -> list[dict]:
        """按用户角色过滤可见域"""
        visible = []
        for d in self.domains_parsed:
            perms = d.get("permissions", [])
            if not perms or any(r in perms for r in user_roles):
                visible_tabs = []
                for tab in d["tabs"]:
                    tab_perms = tab.permissions
                    if not tab_perms or any(r in tab_perms for r in user_roles):
                        visible_tabs.append(tab)
                if visible_tabs:
                    visible.append({**d, "tabs": visible_tabs})
        return visible


# 默认配置文件路径
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "ui_config.json"


def _load_config_from_file(path: Path) -> Any:
    """从文件加载配置"""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    from .ui_config import UIConfig

    return UIConfig(**data)


def _default_ui_config() -> Any:
    """返回内嵌默认配置（无外部文件时兜底）"""
    return UIConfig(
        app={},
        topbar={},
        theme={},
        domains=[
            {
                "id": "home",
                "title": "首页",
                "icon": "◈",
                "order": 0,
                "tabs": [
                    {"id": "overview", "title": "学期概览", "view": "overview", "default": True},
                    {"id": "quick", "title": "快捷操作", "view": "quick"},
                    {"id": "status", "title": "待办·数据状态", "view": "status"},
                ],
            },
            {
                "id": "students",
                "title": "学生管理",
                "icon": "▤",
                "order": 1,
                "permissions": ["admin", "academic_staff"],
                "tabs": [
                    {
                        "id": "student_list",
                        "title": "学生信息",
                        "view": "student_list",
                        "default": True,
                        "permissions": ["admin", "academic_staff"],
                    },
                    {
                        "id": "student_register",
                        "title": "新生注册",
                        "view": "student_register",
                        "permissions": ["admin"],
                    },
                    {
                        "id": "student_movement",
                        "title": "学籍变动",
                        "view": "student_movement",
                        "permissions": ["admin", "academic_staff"],
                    },
                    {
                        "id": "student_promotion",
                        "title": "升留级/毕业",
                        "view": "student_promotion",
                        "permissions": ["admin"],
                    },
                ],
            },
            {
                "id": "scores",
                "title": "成绩管理",
                "icon": "▦",
                "order": 2,
                "tabs": [
                    {
                        "id": "score_entry",
                        "title": "成绩录入",
                        "view": "score_entry",
                        "default": True,
                    },
                    {"id": "score_query", "title": "成绩查询", "view": "score_query"},
                    {"id": "score_stats", "title": "成绩统计", "view": "score_stats"},
                    {"id": "score_rank", "title": "排名分析", "view": "score_rank"},
                ],
            },
            {
                "id": "exams",
                "title": "考试管理",
                "icon": "◈",
                "order": 3,
                "tabs": [
                    {
                        "id": "exam_manage",
                        "title": "考试管理",
                        "view": "exam_manage",
                        "default": True,
                    },
                    {"id": "exam_rooms", "title": "考场座位", "view": "exam_rooms"},
                    {"id": "exam_invigilation", "title": "监考安排", "view": "exam_invigilation"},
                    {"id": "exam_admit", "title": "准考证", "view": "exam_admit"},
                ],
            },
            {
                "id": "teachers",
                "title": "教师管理",
                "icon": "◇",
                "order": 4,
                "tabs": [
                    {
                        "id": "teacher_list",
                        "title": "教师信息",
                        "view": "teacher_list",
                        "default": True,
                    },
                    {"id": "teacher_assign", "title": "任课安排", "view": "teacher_assign"},
                ],
            },
            {
                "id": "system",
                "title": "系统设置",
                "icon": "⚙",
                "order": 5,
                "tabs": [
                    {"id": "semester", "title": "学期设置", "view": "semester", "default": True},
                    {"id": "classes", "title": "班级科目", "view": "classes"},
                    {"id": "classrooms", "title": "教室位置", "view": "classrooms"},
                    {"id": "users", "title": "用户权限", "view": "users"},
                    {"id": "data_maintenance", "title": "数据维护", "view": "data_maintenance"},
                    {"id": "system_config", "title": "系统设置", "view": "system_config"},
                    {"id": "init", "title": "初始化系统", "view": "init"},
                ],
            },
        ],
        statusbar={"left": [{"type": "connection", "label": "已连接"}], "right": []},
    )


# 默认配置文件路径
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "ui_config.json"


# 导出单例（惰性初始化）
_config_instance: Any = None


def load_config(path: str | Path | None = None) -> Any:
    """加载 UI 配置（支持路径 / 默认路径 / 内嵌默认）"""
    p = Path(path) if path else _DEFAULT_CONFIG_PATH
    if p.exists():
        return _load_config_from_file(p)
    return _default_ui_config()


def get_config(path: str | Path | None = None) -> Any:
    """获取 UI 配置单例（惰性加载，支持热重载）"""
    global _config_instance  # noqa: PLW0603
    if _config_instance is None:
        _config_instance = load_config(path)
    return _config_instance


def reload_config(path: str | Path | None = None) -> Any:
    """重新加载配置（开发调试用）"""
    global _config_instance  # noqa: PLW0603
    _config_instance = load_config(path)
    return _config_instance


# 默认配置文件路径
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "ui_config.json"


# 导出单例（惰性初始化）
_config_instance: Any = None
