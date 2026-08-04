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
}

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
}}
"""
