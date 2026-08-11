"""
通用组件 — FilterBar / Toolbar / PaginationBar / StatusBadge / EmptyState / ConfirmDialog / BatchActionBar
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from edu_system.gui.theme import C, font

# ============================================================
# make_button — 统一按钮工厂（G1：消除各视图重复手搓 _btn）
# 颜色映射：primary=蓝 / success=绿 / danger=红 / warning=橙 / neutral=灰
# ============================================================

_BTN_COLORS = {
    "primary": "#3498DB",
    "success": "#27AE60",
    "danger": "#E74C3C",
    "warning": "#E67E22",
    "neutral": "#95A5A6",
}


def make_button(text: str, color: str = "primary", size: str = "md") -> QPushButton:
    """统一按钮工厂（对齐若依 Element 按钮风格）"""
    bg = _BTN_COLORS.get(color, _BTN_COLORS["primary"])
    pad = "3px 12px" if size == "sm" else ("6px 16px" if size == "md" else "8px 24px")
    fs = "8pt" if size == "sm" else ("9pt" if size == "md" else "10pt")
    b = QPushButton(text)
    b.setStyleSheet(
        f"QPushButton {{ background:{bg}; color:white; border:none; border-radius:4px; "
        f"padding:{pad}; font-size:{fs}; }} "
        f"QPushButton:hover {{ background:{C['sidebar_hover']}; }} "
        f"QPushButton:disabled {{ background:#ccc; }}"
    )
    b.setCursor(Qt.PointingHandCursor)
    return b


def btn(text: str, hex_color: str, w: int | None = None) -> QPushButton:
    """兼容按钮工厂（S1 收编：替代各视图重复定义的 _btn）

    签名与原 _btn(txt, color, w) 完全一致，可直接替换：
    _btn("新增", C["accent_green"])  →  btn("新增", C["accent_green"])
    """
    from edu_system.gui.theme import C as _C

    b = QPushButton(text)
    hover = _C.get("sidebar_hover", "#34495E")
    b.setStyleSheet(
        f"QPushButton {{ background: {hex_color}; color: white; border: none; "
        f"border-radius: 3px; padding: 4px 10px; font-size: 9pt; }} "
        f"QPushButton:hover {{ background: {hover}; }} "
        f"QPushButton:disabled {{ background: #ccc; }}"
    )
    if w:
        b.setFixedWidth(w)
    b.setCursor(Qt.PointingHandCursor)
    return b


class Toolbar(QFrame):
    """统一工具栏：主操作高亮、次操作次要"""

    action_triggered = pyqtSignal(str)

    def __init__(self, actions: list[dict], parent=None):
        """
        Args:
            actions: 动作列表，每项包含:
                - id: 动作标识符
                - text: 显示文本
                - icon: 可选图标路径
                - primary: 是否主操作
                - tooltip: 提示文本
        """
        super().__init__()
        self._actions = actions
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self._layout.setSpacing(8)
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("toolbar")
        self.setStyleSheet(f"""
            #toolbar {{ background: {C["white"]}; border: 1px solid {C["line"]}; border-radius: 6px; padding: 4px; }}
            QPushButton {{ border: 1px solid {C["line"]}; border-radius: 4px; padding: 6px 14px; font-size: 9pt; }}
        """)

        for action in self._actions:
            btn = QPushButton(action.get("text", ""))
            btn.setProperty("primary", action.get("primary", False))
            if action.get("tooltip"):
                btn.setToolTip(action["tooltip"])
            btn.clicked.connect(lambda _, aid=action["id"]: self.action_triggered.emit(aid))
            self._layout.addWidget(btn)

        self._layout.addStretch()


class EmptyState(QWidget):
    """空状态：引导插画 + 标题 + 描述 + 主操作按钮"""

    action_clicked = pyqtSignal(str)

    def __init__(
        self,
        title: str = "暂无数据",
        description: str = "暂时没有相关记录",
        icon: str = "📭",
        action_text: str = "",
        action_id: str = "",
        parent=None,
    ):
        super().__init__()
        self._action_id = action_id
        self._action_text = action_text
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(font(48))
        icon_lbl.setAlignment(Qt.AlignHCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setFont(font(16, True))
        title_lbl.setStyleSheet(f"color: {C['text']};")
        title_lbl.setAlignment(Qt.AlignHCenter)
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setFont(font(10))
        desc_lbl.setStyleSheet(f"color: {C['text_light']};")
        desc_lbl.setAlignment(Qt.AlignHCenter)
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        if action_text:
            self.action_btn = QPushButton(action_text)
            self.action_btn.setStyleSheet(f"""
                QPushButton {{ background: {C["accent_blue"]}; color: white; border: none;
                               border-radius: 6px; padding: 8px 24px; font-size: 10pt; }}
                QPushButton:hover {{ background: #2f89c9; }}
            """)
            layout.addWidget(self.action_btn)
            self.action_btn.clicked.connect(lambda: self.action_clicked.emit(self._action_id))

    def set_action(self, action_text: str, action_id: str):
        pass


class ConfirmDialog(QDialog):
    """通用确认/撤销对话框"""

    def __init__(
        self,
        title: str,
        message: str,
        confirm_text: str = "确定",
        cancel_text: str = "取消",
        destructive: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        self._build_ui(title, message, confirm_text, cancel_text, destructive)

    def _build_ui(
        self, title: str, message: str, confirm_text: str, cancel_text: str, destructive: bool
    ):
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        msg = QLabel(message)
        msg.setFont(font(10))
        msg.setWordWrap(True)
        msg.setStyleSheet(f"color: {C['text']};")
        layout.addWidget(msg)

        btn_box = QDialogButtonBox()
        confirm_btn = btn_box.addButton("确定", QDialogButtonBox.AcceptRole)
        cancel_btn = btn_box.addButton("取消", QDialogButtonBox.RejectRole)

        if destructive:
            confirm_btn.setStyleSheet(f"""
                QPushButton {{ background: {C["accent_red"]}; color: white; border: none;
                               border-radius: 6px; padding: 8px 24px; font-size: 10pt; }}
                QPushButton:hover {{ background: #c0392b; }}
            """)
        else:
            confirm_btn.setStyleSheet(f"""
                QPushButton {{ background: {C["accent_blue"]}; color: white; border: none;
                               border-radius: 6px; padding: 8px 24px; font-size: 10pt; }}
                QPushButton:hover {{ background: #2f89c9; }}
            """)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C["text"]}; border: 1px solid {C["line"]};
                           border-radius: 6px; padding: 8px 24px; font-size: 10pt; }}
            QPushButton:hover {{ background: {C["line"]}; }}
        """)

        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)


class CommandPalette(QFrame):
    """命令面板：Ctrl+K 打开，搜索/跳转到任意页面/功能"""

    action_triggered = pyqtSignal(str)  # view_id

    def __init__(self, ui_config, parent=None):
        super().__init__(parent)
        self._ui_config = ui_config
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setVisible(False)
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("commandPalette")
        self.setStyleSheet(f"""
            #commandPalette {{ background: {C["white"]}; border: 1px solid {C["line"]}; border-radius: 8px; padding: 0; }}
            QLabel {{ color: {C["text"]}; font-size: 10pt; }}
            QLineEdit {{ border: none; background: transparent; font-size: 11pt; padding: 12px; }}
            QListWidget {{ border: none; background: transparent; outline: none; }}
            QListWidget::item {{ padding: 10px 16px; border-bottom: 1px solid {C["line"]}; }}
            QListWidget::item:selected {{ background: {C["bg_light"]}; color: {C["accent_blue"]}; }}
            QListWidget::item:hover {{ background: {C["bg_light"]}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 搜索框
        search_container = QFrame()
        search_container.setStyleSheet(
            f"background: {C['bg_light']}; border-bottom: 1px solid {C['line']}; padding: 8px 16px;"
        )
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(12, 8, 12, 8)

        shortcut_lbl = QLabel("⌘K")
        shortcut_lbl.setFont(font(10))
        shortcut_lbl.setStyleSheet(f"color: {C['text_light']}; padding-right: 8px;")
        search_layout.addWidget(shortcut_lbl)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索页面、功能、操作...")
        self.search_input.textChanged.connect(self._filter_items)
        self.search_input.setStyleSheet("border: none; background: transparent; font-size: 11pt;")
        search_layout.addWidget(self.search_input)

        self.layout().addWidget(search_container)

        # 结果列表
        from PyQt5.QtWidgets import QListWidget

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_item_clicked)
        self.layout().addWidget(self.results_list)

    def show_palette(self):
        """显示命令面板，居中显示"""
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(
                self.parent().mapToGlobal(self.parent().rect().center()) - self.rect().center()
            )
        self.search_input.clear()
        self._populate_all()
        self.show()
        self.raise_()
        self.search_input.setFocus()

    def hide_palette(self):
        self.hide()

    def _populate_all(self):
        """填充所有可用命令"""
        self.results_list.clear()
        # 从 UIConfig 获取所有视图
        for domain in self._ui_config.domains_parsed:
            for tab in domain.get("tabs", []):
                title = tab.title if hasattr(tab, "title") else tab["title"]
                view = tab.view if hasattr(tab, "view") else tab["view"]
                self._add_item(title, view)

    def _add_item(self, title: str, view_id: str):
        from PyQt5.QtWidgets import QListWidgetItem

        item = QListWidgetItem(title)
        item.setData(Qt.UserRole, view_id)
        self.results_list.addItem(item)

    def _filter_items(self, text: str):
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            match = text.lower() in item.text().lower()
            item.setHidden(not match)

    def _on_item_clicked(self, item):
        view_id = item.data(Qt.UserRole)
        self.action_triggered.emit(view_id)
        self.hide()


class TablePrefsService:
    """表格列宽/列显隐持久化，基于 Setting 表（随数据库跨设备同步）。

    与 student.py 既有方案（student_view_columns / student_table_col_widths）
    同源同模式；此处为通用封装，供各业务视图复用。

    用法：
        prefs = TablePrefsService(session, "teacher_list")
        prefs.restore(table)    # 表格填充后调用
        prefs.save(table)       # 列宽变化时调用
    """

    def __init__(self, session, view_key: str):
        from edu_system.models import Setting

        self._session = session
        self._Setting = Setting
        self._widths_key = f"{view_key}_col_widths"
        self._vis_key = f"{view_key}_col_visibility"

    def _get(self, key: str) -> str:
        entry = self._session.query(self._Setting).filter_by(key=key).first()
        return entry.value if entry and entry.value else ""

    def _set(self, key: str, value: str) -> None:
        entry = self._session.query(self._Setting).filter_by(key=key).first()
        if entry:
            entry.value = value
        else:
            self._session.add(self._Setting(key=key, value=value))
        self._session.commit()

    # ── 列宽 ──
    def save(self, table) -> None:
        header = table.horizontalHeader()
        widths = [str(header.sectionSize(c)) for c in range(table.columnCount())]
        self._set(self._widths_key, ",".join(widths))
        vis = ["1" if not table.isColumnHidden(c) else "0" for c in range(table.columnCount())]
        self._set(self._vis_key, ",".join(vis))

    def restore(self, table) -> None:
        # 列宽
        wv = self._get(self._widths_key)
        if wv:
            for i, w in enumerate(wv.split(",")):
                if i < table.columnCount() and w.isdigit():
                    table.setColumnWidth(i, int(w))
        # 显隐（第 0 列恒显示）
        vv = self._get(self._vis_key)
        if vv:
            for i, v in enumerate(vv.split(",")):
                if 0 < i < table.columnCount():
                    table.setColumnHidden(i, v != "1")

    def toggle_column(self, table, col_idx: int) -> None:
        if col_idx == 0:
            return
        table.setColumnHidden(col_idx, not table.isColumnHidden(col_idx))
        self.save(table)

    def reset(self) -> None:
        self._set(self._widths_key, "")
        self._set(self._vis_key, "")
