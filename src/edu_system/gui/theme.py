"""
统一主题 — PyQt5 QSS 样式表
"""

import sys

from PyQt5.QtGui import QFont


# ── 字体（Windows 用微软雅黑；Linux 用文泉驿微米黑，避免 DejaVu fallback 行高挤压）──
def font(size=9, bold=False):
    f = QFont()
    f.setPointSize(size)
    f.setBold(bold)
    if sys.platform == "win32":
        f.setFamily("微软雅黑")
    else:
        f.setFamily("文泉驿微米黑")
    return f


# ── 配色（设计令牌：全 UI 统一引用，改此处全局生效）──
C = {
    # 基础
    "sidebar_bg": "#2C3E50",
    "sidebar_fg": "white",
    "text": "#2C3E50",
    "text_light": "#95A5A6",
    "bg_light": "#F5F6FA",
    "white": "#FFFFFF",
    "line": "#E0E4E8",
    # 强调色
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
    # 表格（统一各视图表格样式）
    "table_alt_bg": "#EBF5FB",  # 斑马纹
    "table_header_bg": "#D9E1F2",  # 表头背景
    "table_header_border": "#CCC",  # 表头边框
    "table_border": "#DDD",  # 表格外框
    "table_grid": "#EEE",  # 网格线
    "sidebar_hover": "#34495E",  # 侧栏按钮悬停
    # 状态背景
    "bg_error": "#FFF0F0",
    "bg_muted": "#F5F5F5",
    # AntD 风格系统页（system_config/data_maintenance/system_settings_layout 共用）
    "antd_blue": "#1890ff",  # 主蓝（选中/按钮/标签值）
    "antd_blue_hover": "#40a9ff",
    "antd_red": "#ff4d4f",  # 危险/停止
    "antd_green": "#52c41a",  # 成功/启动
    "antd_warn": "#faad14",  # 清理警告
    "antd_title": "#1a1a2e",  # 深色标题
    "antd_border": "#d9d9d9",  # 边框
    "antd_bg_warn": "#FFF3CD",  # 警告底色
    "antd_warn_amber": "#FFC107",
    "antd_teal": "#2E86C1",  # 按钮 Hover（局部）
}

# ── 主题预设（U1：若依风格一键切换）──
# 若依经典配色：深色侧栏 #2f4050 + Element 蓝 #409EFF + 浅灰内容 #f0f2f5
RUOYI_THEME = {
    "sidebar_bg": "#2f4050",
    "sidebar_hover": "#293846",
    "sidebar_fg": "#bfcbd9",
    "text": "#2f4050",
    "text_light": "#97a8be",
    "bg_light": "#f0f2f5",
    "white": "#FFFFFF",
    "line": "#e5e6e7",
    "accent_blue": "#409EFF",
    "accent_blue_hover": "#66b1ff",
    "accent_blue_pressed": "#337ecc",
    "accent_green": "#67c23a",
    "accent_green_hover": "#85ce61",
    "accent_red": "#f56c6c",
    "accent_orange": "#e6a23c",
    "accent_purple": "#8E44AD",
    "accent_teal": "#1ABC9C",
    "accent_warn": "#e6a23c",
    "table_alt_bg": "#f5f7fa",
    "table_header_bg": "#ebeef5",
    "table_header_border": "#dcdfe6",
    "table_border": "#dcdfe6",
    "table_grid": "#ebeef5",
    "bg_error": "#fef0f0",
    "bg_muted": "#f5f7fa",
    "antd_blue": "#409EFF",
    "antd_blue_hover": "#66b1ff",
    "antd_red": "#f56c6c",
    "antd_green": "#67c23a",
    "antd_warn": "#e6a23c",
    "antd_title": "#2f4050",
    "antd_border": "#dcdfe6",
    "antd_bg_warn": "#fdf6ec",
    "antd_warn_amber": "#e6a23c",
    "antd_teal": "#409EFF",
}

# 主题开关（默认经典；apply_theme("ruoyi") 切换）
_ACTIVE_THEME = "classic"


def apply_theme(name: str = "classic") -> None:
    """切换全局配色预设（classic=默认 / ruoyi=若依风格）

    就地更新 C 字典（SIDEBAR_BTN/TABLE_STYLE 等 f-string 常量在
    应用启动时基于 C 生成，切换后需重建 QSS 的调用方重新 setStyleSheet）。
    """
    global _ACTIVE_THEME
    preset = RUOYI_THEME if name == "ruoyi" else None
    if preset is None:
        # 恢复默认（从文件源值重建）
        _reset_classic()
    else:
        C.update(preset)
    _ACTIVE_THEME = name


def _reset_classic() -> None:
    """恢复经典主题默认值（与 C 初始定义一致）"""
    C.update(
        {
            "sidebar_bg": "#2C3E50",
            "sidebar_hover": "#34495E",
            "sidebar_fg": "white",
            "text": "#2C3E50",
            "text_light": "#95A5A6",
            "bg_light": "#F5F6FA",
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
            "bg_error": "#FFF0F0",
            "bg_muted": "#F5F5F5",
            "antd_blue": "#1890ff",
            "antd_blue_hover": "#40a9ff",
            "antd_red": "#ff4d4f",
            "antd_green": "#52c41a",
            "antd_warn": "#faad14",
            "antd_title": "#1a1a2e",
            "antd_border": "#d9d9d9",
            "antd_bg_warn": "#FFF3CD",
            "antd_warn_amber": "#FFC107",
            "antd_teal": "#2E86C1",
        }
    )


# ── 侧栏按钮样式 ──
SIDEBAR_BTN = f"""
QPushButton {{
    color: white; border: none; border-radius: 4px;
    padding: 5px 10px; text-align: left; font-size: 9pt;
}}
QPushButton:hover {{ background-color: {C["sidebar_hover"]}; }}
"""

# ── 内容区表格样式 ──
TABLE_STYLE = f"""
QTableWidget {{
    font-size: 9pt; border: 1px solid {C["table_border"]}; gridline-color: {C["table_grid"]};
    alternate-background-color: {C["table_alt_bg"]};
}}
QHeaderView::section {{
    background: {C["table_header_bg"]}; font-weight: bold; font-size: 9pt;
    padding: 4px; border: 1px solid {C["table_header_border"]};
    color: {C["text"]};
}}
QTableWidget::item {{ padding: 2px 5px; }}
QTableWidget::item:selected {{ background: {C["accent_blue"]}; color: white; }}
"""
