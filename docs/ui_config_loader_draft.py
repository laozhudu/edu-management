"""
UI 配置加载器 — 设计草案（供讨论，未接入工程）

目标：桌面端(PyQt5) 与 Web 端共享同一份 ui_config JSON，
通过 view 标识符统一路由到视图工厂，实现"改配置不改代码"。

place: src/edu_system/config/ui.py  (规划)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# ============================================================
# 配置模型（与 ui_config.json 一一对应）
# ============================================================


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


class AppConfig(BaseModel):
    """应用标识配置（品牌/学校/版本，全部可改）"""

    name: str = "教务系统"
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
    search_placeholder: str = ""
    show_user_menu: bool = True
    show_notifications: bool = False


class ThemeConfig(BaseModel):
    """主题配置"""

    brand: str = "{school}{name}"
    accent_color: str = "#3498DB"
    sidebar_bg: str = "#2C3E50"
    sidebar_hover: str = "#34495E"
    content_bg: str = "#F5F6FA"
    density: str = "compact"  # compact / comfortable


class StatusBarItem(BaseModel):
    type: str
    label: str


class StatusBarConfig(BaseModel):
    left: list[StatusBarItem] = Field(default_factory=list)
    right: list[StatusBarItem] = Field(default_factory=list)


class UIConfig(BaseModel):
    """顶级 UI 配置"""

    app: AppConfig = AppConfig()
    theme: ThemeConfig = ThemeConfig()
    topbar: TopBarConfig = TopBarConfig()
    domains: list[DomainConfig] = Field(default_factory=list)
    statusbar: StatusBarConfig = StatusBarConfig()

    def render(self, template: str) -> str:
        """渲染 {placeholders} 模板变量（school/name/version/...）"""
        vals = {
            "school": self.app.school_name,
            "name": self.app.name,
            "version": self.app.version,
        }
        out = template
        for k, v in vals.items():
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
    def domain_map(self) -> dict[str, DomainConfig]:
        return {d.id: d for d in self.domains}

    def domain(self, domain_id: str) -> DomainConfig | None:
        return self.domain_map.get(domain_id)

    def find_view(self, view_id: str) -> tuple[str, TabConfig] | None:
        """按 view 标识符查找所属域 + 页签"""
        for d in self.domains:
            for tab in d.tabs:
                if tab.view == view_id:
                    return d.id, tab
        return None

    def first_domain(self) -> DomainConfig | None:
        return min(self.domains, key=lambda d: d.order) if self.domains else None


# ============================================================
# 配置加载
# ============================================================

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "ui_config.json"


def load_config(path: str | Path | None = None) -> UIConfig:
    """加载 UI 配置（支持路径 / 默认路径 / 内嵌默认）"""
    p = Path(path) if path else _DEFAULT_CONFIG_PATH
    if p.exists():
        return UIConfig.model_validate_json(p.read_text(encoding="utf-8"))
    return UIConfig()  # 无配置时返回默认（单页 UI 兜底）


# ============================================================
# 视图工厂（桌面端与 Web 端共用同一映射契约）
# ============================================================
# 约定：view 标识符 -> (桌面 PyQt 工厂, Web 模板名)
# 桌面端在 gui/views/registry.py 实现；Web 端在 api/views_registry.py 实现。
# 两边各自维护一个 view 标识符到实现的映射；ui_config 只消费这些标识符。
VIEW_REGISTRY_PROTOCOL = {
    # "student_list": {"qt": build_student_view, "web_template": "student_list.html"},
    # ...
}
