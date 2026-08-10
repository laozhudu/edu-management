"""
基类视图 + 工作台容器 + 通用列选择对话框
"""

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from edu_system.core.permissions import Permission, has_permission


class BaseView(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session

    # ── G1：统一底座便捷方法（消除各视图重复手搓 _btn/确认框）──
    def btn(self, text: str, color: str = "primary"):
        """统一按钮工厂（对齐 components.Toolbar 样式）"""
        from edu_system.gui.components import make_button

        return make_button(text, color)

    def confirm(self, title: str, message: str, destructive: bool = False) -> bool:
        """统一确认对话框（对齐 components.ConfirmDialog）"""
        from edu_system.gui.components import ConfirmDialog

        dlg = ConfirmDialog(title, message, destructive=destructive, parent=self)
        return dlg.exec_() == QDialog.Accepted

    def make_empty_state(self, **kwargs) -> QWidget:
        """统一空状态组件"""
        from edu_system.gui.components import EmptyState

        return EmptyState(**kwargs)


class LockToolbar(QWidget):
    """数据锁定工具栏（C3）：锁定/解锁/批量/理由必填 + 权限控制

    供 BaseView 派生视图复用：add_lock_toolbar() 挂载到工具栏区。
    无 DATA_UNLOCK 权限时按钮全部禁用（权限控制）。
    """

    # 实体类型候选（与数据锁定 API 对齐）
    ENTITY_TYPES = [
        "student",
        "class",
        "score",
        "exam",
        "exam_scores",
        "student_movement",
        "exam_numbers",
        "semester",
        "teacher",
    ]

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._build_ui()
        self._apply_permission()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(4)

        lay.addWidget(QLabel("锁定:"))
        self.type_cb = QComboBox()
        self.type_cb.addItems(self.ENTITY_TYPES)
        self.type_cb.setMaximumWidth(130)
        lay.addWidget(self.type_cb)

        lay.addWidget(QLabel("ID:"))
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("实体ID（批量逗号分隔）")
        self.id_edit.setMaximumWidth(140)
        lay.addWidget(self.id_edit)

        lay.addWidget(QLabel("级别:"))
        self.level_cb = QComboBox()
        self.level_cb.addItems(["hard", "soft", "semester"])
        self.level_cb.setMaximumWidth(80)
        lay.addWidget(self.level_cb)

        lay.addWidget(QLabel("理由:"))
        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("锁定理由（必填）")
        self.reason_edit.setMinimumWidth(150)
        lay.addWidget(self.reason_edit)

        self.lock_btn = QPushButton("加锁")
        self.lock_btn.clicked.connect(self._do_lock)
        lay.addWidget(self.lock_btn)

        self.unlock_btn = QPushButton("解锁")
        self.unlock_btn.clicked.connect(self._do_unlock)
        lay.addWidget(self.unlock_btn)

        self.status_btn = QPushButton("锁状态")
        self.status_btn.clicked.connect(self._do_status)
        lay.addWidget(self.status_btn)

        lay.addStretch()

    # ===== 权限控制 =====

    def _apply_permission(self):
        """无 DATA_UNLOCK 权限：禁用锁定/解锁操作（权限控制按钮）"""
        allowed = has_permission(Permission.DATA_UNLOCK)
        for btn in (self.lock_btn, self.unlock_btn):
            btn.setEnabled(allowed)
            if not allowed:
                btn.setToolTip("需要 DATA_UNLOCK 权限")

    # ===== 操作 =====

    def _get_args(self) -> tuple | None:
        """解析参数，返回 (entity_type, ids, level) 或 None"""
        entity_type = self.type_cb.currentText()
        raw = self.id_edit.text().strip()
        if not raw:
            QMessageBox.warning(self, "参数缺失", "请输入实体ID")
            return None
        try:
            ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            QMessageBox.warning(self, "参数错误", "实体ID必须为数字，批量用逗号分隔")
            return None
        if not ids:
            QMessageBox.warning(self, "参数缺失", "请输入有效实体ID")
            return None
        level = self.level_cb.currentText()
        return entity_type, ids, level

    def _get_reason(self) -> str | None:
        """理由必填校验"""
        reason = self.reason_edit.text().strip()
        if not reason:
            QMessageBox.warning(self, "理由必填", "请填写锁定理由")
            return None
        return reason

    def _get_semester_id(self) -> int:
        """取当前激活学期（锁定记录按学期隔离）"""
        from edu_system.database import get_active_semester

        sid = get_active_semester()
        return sid or 0

    def _do_lock(self):
        from edu_system.services.locks import DataLockService, LockLevel

        parsed = self._get_args()
        if not parsed:
            return
        entity_type, ids, level = parsed
        reason = self._get_reason()
        if reason is None:
            return

        svc = DataLockService(self.session)
        lock_level = LockLevel(level)
        semester_id = self._get_semester_id()
        # 从登录用户取操作人
        from edu_system.core.permissions import get_current_user

        user = get_current_user()
        operator = user.username if user else "system"

        created = 0
        for eid in ids:
            svc.lock(
                semester_id=semester_id,
                entity_type=entity_type,
                entity_id=eid,
                lock_level=lock_level,
                locked_by=operator,
                reason=reason,
            )
            created += 1
        self.session.commit()
        QMessageBox.information(self, "加锁完成", f"已锁定 {created} 个实体（{entity_type}）")

    def _do_unlock(self):
        from edu_system.services.locks import DataLockService

        parsed = self._get_args()
        if not parsed:
            return
        entity_type, ids, level = parsed

        svc = DataLockService(self.session)
        semester_id = self._get_semester_id()
        unlocked = 0
        for eid in ids:
            svc.unlock(
                semester_id=semester_id,
                entity_type=entity_type,
                entity_id=eid,
                unlocker="gui",
                force=True,
            )
            unlocked += 1
        self.session.commit()
        QMessageBox.information(self, "解锁完成", f"已解锁 {unlocked} 个实体（{entity_type}）")

    def _do_status(self):
        from edu_system.services.locks import DataLockService

        parsed = self._get_args()
        if not parsed:
            return
        entity_type, ids, _ = parsed

        svc = DataLockService(self.session)
        semester_id = self._get_semester_id()
        lines = []
        for eid in ids:
            lock = svc.get_lock(semester_id=semester_id, entity_type=entity_type, entity_id=eid)
            if lock:
                lines.append(
                    f"{entity_type}#{eid}: {lock.lock_level} | {lock.reason} | {lock.locked_by}"
                )
            else:
                lines.append(f"{entity_type}#{eid}: 未锁定")
        QMessageBox.information(self, "锁状态", "\n".join(lines) or "无锁定记录")


def build_lock_toolbar(session: Session, parent=None) -> LockToolbar:
    """便捷工厂：构造锁定工具栏（供各视图挂载）"""
    return LockToolbar(session, parent)


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

    def __init__(
        self,
        session: Session | None,
        tab_configs: list[tuple[str, int]],
        title: str = "",
        server_thread=None,
    ):
        super().__init__()
        self.session = session
        self.server_thread = server_thread
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

    def set_server_thread(self, server_thread):
        """设置服务器线程引用，传递给需要的视图"""
        self.server_thread = server_thread
        for view in self._instances.values():
            if hasattr(view, "set_server_thread"):
                view.set_server_thread(server_thread)

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

            # 如果视图需要服务器线程，传递给它
            if self.server_thread and hasattr(real_view, "set_server_thread"):
                real_view.set_server_thread(self.server_thread)

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
