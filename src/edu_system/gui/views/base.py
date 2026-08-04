"""
基类视图 + 工作台容器 + 通用列选择对话框
"""

from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session


class BaseView(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session


class ColumnSelectorDialog(QDialog):
    """通用列选择对话框：全选/全不选 + 复选框列表"""

    def __init__(self, parent, columns: dict, checked_keys: list = None, title: str = "选择列"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.columns = columns
        self.checked_keys = set(checked_keys) if checked_keys else set()

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cw = QWidget()
        cl = QVBoxLayout(cw)
        cl.setSpacing(2)

        self.checks = {}
        for key, label in columns.items():
            cb = QCheckBox(label)
            cb.setChecked(key in self.checked_keys)
            cl.addWidget(cb)
            self.checks[key] = cb
        scroll.setWidget(cw)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        all_btn = QPushButton("全选")
        all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in self.checks.values()])
        none_btn = QPushButton("全不选")
        none_btn.clicked.connect(lambda: [cb.setChecked(False) for cb in self.checks.values()])
        btn_row.addWidget(all_btn)
        btn_row.addWidget(none_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        ok = QPushButton("确定")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        bl = QHBoxLayout()
        bl.addWidget(ok)
        bl.addWidget(cancel)
        layout.addLayout(bl)

    def get_selected(self) -> list:
        return [k for k, cb in self.checks.items() if cb.isChecked()]


class WorkbenchWidget(QWidget):
    """工作台：顶部标签页 + 下方堆栈视图，懒加载"""

    def __init__(self, session: Session, tab_configs: list[tuple[str, int]], title: str = ""):
        super().__init__()
        self.session = session
        self.tab_configs = tab_configs  # [(tab_name, view_idx), ...]
        self._instances = {}  # tab_index -> widget (use tab index as key to support duplicate view_idx)
        self._loaded = False
        self.title = title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标签栏
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

        # 为每个标签创建占位页
        for tab_name, view_idx in tab_configs:
            placeholder = QWidget()
            self.tabs.addTab(placeholder, tab_name)
            # 存储 view_idx 到 tab 的数据
            self.tabs.tabBar().setTabData(self.tabs.count() - 1, view_idx)

        # 不自动加载，等待 ensure_loaded() 调用

    def set_session(self, session: Session):
        """DB 初始化完成后注入 session"""
        self.session = session
        # 如果已经加载过，需要把 session 传给已加载的实例
        for view in self._instances.values():
            if hasattr(view, "session"):
                view.session = session

    def ensure_loaded(self):
        """确保当前标签页已加载（首次显示工作台时调用）"""
        if self._loaded:
            return
        if self.session is None:
            # Session 还未就绪，稍后重试
            from PyQt5.QtCore import QTimer

            QTimer.singleShot(50, self.ensure_loaded)
            return
        self._loaded = True
        self.load_current_tab()

    def _on_tab_changed(self, index: int):
        view_idx = self.tabs.tabBar().tabData(index)
        if view_idx is None:
            return

        # 懒加载真实视图 - 使用 tab index 作为 key 支持重复 view_idx
        if index not in self._instances:
            if view_idx == -1:
                # 特殊处理：报表生成
                from edu_system.gui.views.report import ReportView

                real_view = ReportView(self.session)
            else:
                from edu_system.gui.views.registry import build_view

                # Ensure session is available
                if self.session is None:
                    return
                real_view = build_view(view_idx, self.session)
            self._instances[index] = real_view

            # 保存标签文本（在 removeTab 之前）
            tab_text = self.tabs.tabText(index)

            # 替换占位页
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, real_view, tab_text)
            self.tabs.tabBar().setTabData(index, view_idx)
            self.tabs.setCurrentIndex(index)
        else:
            # 已加载，刷新数据
            real_view = self._instances[index]
            if hasattr(real_view, "refresh"):
                real_view.refresh()

    def load_current_tab(self):
        """显式加载当前标签页（用于工作台首次显示）"""
        self._on_tab_changed(self.tabs.currentIndex())
