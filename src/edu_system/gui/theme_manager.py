"""
主题切换管理器（Sprint 4.2.6）

- 亮色/暗色两套设计令牌（LIGHT/DARK）
- 手动切换 / 系统跟随 / 持久化（QSettings）
- 实时生效：切换后发信号，由主窗口重刷 QSS
"""

from PyQt5.QtCore import QObject, QSettings, pyqtSignal

# ── 亮色令牌（与 theme.C 对齐）──
LIGHT = {
    "sidebar_bg": "#2C3E50",
    "sidebar_fg": "white",
    "text": "#2C3E50",
    "text_light": "#95A5A6",
    "bg_light": "#F5F6FA",
    "white": "#FFFFFF",
    "line": "#E0E4E8",
    "accent_blue": "#3498DB",
    "accent_blue_hover": "#2f89c9",
    "accent_blue_pressed": "#2471a3",
    "accent_green": "#27AE60",
    "accent_green_hover": "#229954",
    "accent_red": "#E74C3C",
    "accent_orange": "#E67E22",
    "accent_purple": "#8E44AD",
    "accent_teal": "#1ABC9C",
    "accent_warn": "#F39C12",
    "table_alt_bg": "#EBF5FB",
    "table_header_bg": "#D9E1F2",
    "table_header_border": "#CCC",
    "table_border": "#DDD",
    "table_grid": "#EEE",
    "sidebar_hover": "#34495E",
    "bg_error": "#FFF0F0",
    "bg_muted": "#F5F5F5",
}

# ── 暗色令牌（与 LIGHT 同键）──
DARK = {
    "sidebar_bg": "#1E2A38",
    "sidebar_fg": "#E8ECF1",
    "text": "#E8ECF1",
    "text_light": "#8FA3B8",
    "bg_light": "#1E2430",
    "white": "#14181F",
    "line": "#2E3A48",
    "accent_blue": "#4FA3E3",
    "accent_blue_hover": "#63B0EA",
    "accent_blue_pressed": "#3B8CC9",
    "accent_green": "#34C77B",
    "accent_green_hover": "#3FD488",
    "accent_red": "#E86B5E",
    "accent_orange": "#F0944A",
    "accent_purple": "#A56FC9",
    "accent_teal": "#3ED0B2",
    "accent_warn": "#F5B041",
    "table_alt_bg": "#232B38",
    "table_header_bg": "#2A3648",
    "table_header_border": "#3A4858",
    "table_border": "#33404F",
    "table_grid": "#2A3644",
    "sidebar_hover": "#2A3A4E",
    "bg_error": "#3A2222",
    "bg_muted": "#232A33",
}

THEMES = {"light": LIGHT, "dark": DARK}


class ThemeManager(QObject):
    """主题管理：切换/持久化/系统跟随"""

    theme_changed = pyqtSignal(str)
    density_changed = pyqtSignal(str)

    # 密度档位（行高倍率，UI 消费方据此调整 spacing/padding/行高）
    DENSITIES = {
        "compact": 0.85,
        "normal": 1.0,
        "comfortable": 1.2,
    }

    def __init__(self):
        super().__init__()
        self._settings = QSettings("edu_system", "theme")
        # 模式: light / dark / system
        self._mode = self._settings.value("mode", "system", type=str)
        self._theme = self._current_theme()
        # 密度: compact / normal / comfortable
        self._density = self._settings.value("density", "normal", type=str)
        if self._density not in self.DENSITIES:
            self._density = "normal"

    # ── 查询 ──
    @property
    def mode(self) -> str:
        return self._mode

    @property
    def theme(self) -> str:
        return self._theme

    def tokens(self) -> dict:
        """当前主题令牌字典"""
        return THEMES[self._theme]

    def _current_theme(self) -> str:
        """按模式解析实际主题"""
        if self._mode == "system":
            return self._system_theme()
        return self._mode if self._mode in THEMES else "light"

    @staticmethod
    def _system_theme() -> str:
        """系统深浅色跟随（Qt 无直接 API，用 palette 近似）"""
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return "light"
        try:
            from PyQt5.QtGui import QPalette

            base = app.palette().color(QPalette.Window).lightness()
            result = "dark" if base < 128 else "light"
        except Exception:
            result = "light"
        return result

    # ── 密度 ──
    @property
    def density(self) -> str:
        """当前密度档位: compact / normal / comfortable"""
        return self._density

    @property
    def density_factor(self) -> float:
        """当前密度行高倍率"""
        return self.DENSITIES[self._density]

    def set_density(self, density: str) -> str:
        """设置密度档位，持久化并广播"""
        if density not in self.DENSITIES:
            raise ValueError(f"无效密度档位: {density}")
        if density != self._density:
            self._density = density
            self._settings.setValue("density", density)
            self.density_changed.emit(density)
        return density

    def cycle_density(self) -> str:
        """循环切换密度（compact → normal → comfortable），返回新档位"""
        order = list(self.DENSITIES)
        idx = order.index(self._density)
        return self.set_density(order[(idx + 1) % len(order)])

    # ── 切换 ──
    def set_mode(self, mode: str):
        """设置模式: light / dark / system，持久化并生效"""
        if mode not in ("light", "dark", "system"):
            raise ValueError(f"无效主题模式: {mode}")
        self._mode = mode
        self._settings.setValue("mode", mode)
        new_theme = self._current_theme()
        if new_theme != self._theme:
            self._theme = new_theme
            self.theme_changed.emit(new_theme)
        return new_theme

    def toggle(self) -> str:
        """亮暗切换（手动模式用），返回新主题"""
        new_mode = "dark" if self._theme == "light" else "light"
        return self.set_mode(new_mode)

    def apply_to(self, qss_template: str) -> str:
        """用当前主题令牌渲染 QSS 模板（f-string 模板含 {token} 引用）"""
        return qss_template.format(**self.tokens())


# 单例
theme_manager = ThemeManager()
