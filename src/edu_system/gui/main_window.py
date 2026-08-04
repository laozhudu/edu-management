"""
主窗口 — PyQt5 数据驱动版本（左侧可折叠侧栏 + 内容区，单一导航源）
核心策略：
1. UI 优先显示（骨架屏），窗口 100ms 内出现
2. DB 初始化放入 QThread 后台线程
3. 首屏数据分页加载（200 行），虚拟滚动懒加载
4. 侧栏可折叠：展开 200px(图标+文字) / 折叠 48px(仅图标)
5. 单一导航源：左侧侧栏为唯一导航，数据驱动自 UIConfig
"""

import socket
import sys

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from edu_system.config.ui_config import get_config
from edu_system.core.permissions import Permission, set_current_user
from edu_system.database import get_session, init_db_with_defaults
from edu_system.gui.components import CommandPalette
from edu_system.gui.server_thread import create_server_thread
from edu_system.gui.theme import C, font
from edu_system.gui.views.base import WorkbenchWidget
from edu_system.models import Role, User


def _nav_btn_style(active=False):
    if active:
        return """
            QPushButton {
                background: #34495E; color: white; border: none;
                border-left: 4px solid #3498DB;
                border-radius: 0; padding: 10px 16px; font-size: 10pt; font-weight: bold;
                text-align: left;
            }
            QPushButton:hover { background: #3A5A7E; }
        """
    return """
        QPushButton {
            background: transparent; color: #ECF0F1; border: none;
            border-left: 4px solid transparent;
            border-radius: 0; padding: 10px 16px; font-size: 10pt;
            text-align: left;
        }
        QPushButton:hover { background: #34495E; color: white; border-left: 4px solid #3498DB; }
    """


def _icon_btn_style():
    return """
        QToolButton {
            background: transparent; color: #ECF0F1; border: none;
            border-radius: 4px; padding: 8px; font-size: 10pt;
        }
        QToolButton:hover { background: #34495E; color: white; }
        QToolButton:pressed { background: #2C3E50; }
        QToolButton::menu-indicator { image: none; }
    """


class DBInitThread(QThread):
    """后台初始化数据库线程"""

    finished = pyqtSignal(object)  # session
    progress = pyqtSignal(str)

    def run(self):
        try:
            self.progress.emit("正在初始化数据库...")
            init_db_with_defaults()
            self.progress.emit("正在建立数据库连接...")
            session = get_session()
            self.finished.emit(session)
        except Exception as e:
            self.finished.emit(e)


class CollapsibleSidebar(QFrame):
    """可折叠侧边栏：展开 200px / 折叠 48px"""

    def __init__(self, ui_config, parent=None):
        super().__init__(parent)
        self.ui_config = ui_config
        self._expanded = True
        self._width_expanded = 200
        self._width_collapsed = 48
        self.setFixedWidth(self._width_expanded)
        self.setObjectName("sidebar")
        self.setStyleSheet(f"#sidebar {{ background: {C['sidebar_bg']}; }}")

        self._build_ui()
        self._animation = QPropertyAnimation(self, b"maximumWidth")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部：折叠按钮（学校字样不再重复显示）
        header = QHBoxLayout()
        header.setContentsMargins(8, 12, 8, 8)
        header.setSpacing(8)

        self.collapse_btn = QToolButton()
        self.collapse_btn.setText("◀")
        self.collapse_btn.setFixedSize(28, 28)
        self.collapse_btn.setStyleSheet(_icon_btn_style())
        self.collapse_btn.clicked.connect(self.toggle)
        self.collapse_btn.setToolTip("折叠侧栏")

        header.addStretch()
        header.addWidget(self.collapse_btn)
        layout.addLayout(header)
        layout.addSpacing(16)

        # 工作台按钮（从配置动态生成）
        self.btns = []
        for i, domain in enumerate(self.ui_config.domains_parsed):
            btn = QPushButton(domain["title"])
            btn.setCheckable(True)
            btn.setStyleSheet(_nav_btn_style())
            btn.clicked.connect(lambda checked, idx=i: self._on_btn_clicked(idx))
            layout.addWidget(btn)
            self.btns.append((btn, domain["title"]))

        layout.addStretch()

    def _on_btn_clicked(self, idx):
        for i, (btn, _) in enumerate(self.btns):
            btn.setChecked(i == idx)
            btn.setStyleSheet(_nav_btn_style(i == idx))
        self.workbench_selected.emit(idx)

    def toggle(self):
        self._expanded = not self._expanded
        target = self._width_expanded if self._expanded else self._width_collapsed
        self.collapse_btn.setText("▶" if not self._expanded else "◀")
        self.collapse_btn.setToolTip("展开侧栏" if not self._expanded else "折叠侧栏")

        for btn, title in self.btns:
            btn.setText(title if self._expanded else "")
            btn.setToolTip("" if self._expanded else title)

        self.setMinimumWidth(target)
        self.setMaximumWidth(target)

        self._animation.stop()
        self._animation.setStartValue(self.width())
        self._animation.setEndValue(target)
        self._animation.start()

    # 信号：工作台被选中
    workbench_selected = pyqtSignal(int)


class TopModuleBar(QFrame):
    """顶部模块栏：品牌 + 面包屑 + 当前学期 + 命令面板"""

    def __init__(self, ui_config, parent=None):
        super().__init__(parent)
        self._ui_config = ui_config
        self._current_wb = 0
        self.setFixedHeight(36)
        self.setObjectName("topbar")
        self.setStyleSheet(
            f"#topbar {{ background: {C['sidebar_bg']}; border-bottom: 1px solid #2C3E50; }}"
        )
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # 顶部栏仅保留居中显示的当前学年学期
        # （与菜单字体样式一致：普通字号、浅灰无强调色背景，符合业界审美）
        self.semester_label = QLabel("2026-2027学年度第一学期")
        self.semester_label.setFont(font(9))
        self.semester_label.setStyleSheet(f"color: {C['text_light']};")
        layout.addStretch()  # 左占位，让学期居中
        layout.addWidget(self.semester_label)
        layout.addStretch()  # 右占位，真正居中

    def set_semester(self, text: str):
        self.semester_label.setText(text)


class MainWindow(QMainWindow):
    def __init__(self, session=None):
        super().__init__()
        self._ui_config = get_config()
        self.setWindowTitle(self._ui_config.window_title)
        self.resize(1280, 780)
        self.session = session
        self._db_thread = None
        self._workbenches = []
        self._server_thread = None  # 嵌入式服务器线程
        self._current_domain_idx = 0
        self._current_tab_idx = 0

        # 1. 极速构建 UI 骨架（无 DB 操作），目标 < 100ms 显示窗口
        self._build_skeleton_ui()

        # 2. 如果没有传入 session，启动后台 DB 初始化线程
        if self.session is None:
            self._start_db_init()
        else:
            # 延迟到事件循环：确保主窗口先 show（登录框 parent 已显示，远程桌面下可见）
            from PyQt5.QtCore import QTimer

            QTimer.singleShot(0, lambda: self._on_db_ready(self.session))

    def keyPressEvent(self, event):
        """处理全局快捷键"""
        if event.key() == Qt.Key_K and event.modifiers() == Qt.ControlModifier:
            self._command_palette.show_palette()
        else:
            super().keyPressEvent(event)

    def _build_skeleton_ui(self):
        """极速构建 UI 骨架：左侧可折叠侧栏 + 顶部栏 + 内容区（骨架屏）"""
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 左侧可折叠侧栏
        self.sidebar = CollapsibleSidebar(self._ui_config)
        self.sidebar.workbench_selected.connect(self._on_sidebar_selected)
        root.addWidget(self.sidebar)

        # 右侧：垂直布局 = 顶部栏 + 内容区
        right = QWidget()
        right.setObjectName("right")
        right.setStyleSheet(f"#right {{ background: {C['bg_light']}; }}")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        # 顶部栏
        self.topbar = TopModuleBar(self._ui_config)
        rv.addWidget(self.topbar)

        # 内容区 - QStackedWidget 切换工作台
        self.content_stack = QStackedWidget()

        # 骨架屏占位
        self.skeleton_label = QLabel("正在初始化系统...")
        self.skeleton_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.skeleton_label.setFont(font(14))
        self.skeleton_label.setStyleSheet(f"color: {C['text_light']}; background: {C['bg_light']};")
        self.content_stack.addWidget(self.skeleton_label)
        self.content_stack.setCurrentWidget(self.skeleton_label)

        rv.addWidget(self.content_stack, 1)
        right.setLayout(rv)
        root.addWidget(right, 1)

        # 状态栏
        self.statusBar().showMessage("正在启动系统...")
        self.statusBar().setSizeGripEnabled(False)

        # 命令面板（Ctrl+K）
        self._command_palette = CommandPalette(self._ui_config, self)
        self._command_palette.action_triggered.connect(self._on_command_palette_action)

    def _start_db_init(self):
        """启动后台 DB 初始化线程"""
        self._db_thread = DBInitThread()
        self._db_thread.progress.connect(self.statusBar().showMessage)
        self._db_thread.finished.connect(self._on_db_ready)
        self._db_thread.start()

        # 启动嵌入式 FastAPI 服务器
        self._start_server()

    def _start_server(self):
        """启动嵌入式 FastAPI 服务器"""
        self._server_thread = create_server_thread(
            host="0.0.0.0", port=8080, app_module="edu_system.api.main:app"
        )

        # 连接信号
        self._server_thread.signals.started.connect(self._on_server_started)
        self._server_thread.signals.stopped.connect(self._on_server_stopped)
        self._server_thread.signals.error.connect(self._on_server_error)
        self._server_thread.signals.log.connect(self._on_server_log)

        # 启动线程
        self._server_thread.start()

    def _on_server_started(self, host: str, port: int):
        """服务器启动成功回调"""
        local_ip = self._get_local_ip()
        self.statusBar().showMessage(f"嵌入式服务已启动: http://{local_ip}:{port}")
        self._update_network_info(local_ip, port)

    def _on_server_stopped(self):
        """服务器停止回调"""
        self.statusBar().showMessage("嵌入式服务已停止")

    def _on_server_error(self, error: str):
        """服务器错误回调"""
        QMessageBox.critical(self, "服务器错误", f"嵌入式服务启动失败:\n{error}")
        self.statusBar().showMessage("嵌入式服务启动失败")

    def _on_server_log(self, log: str):
        """服务器日志回调"""

    def _get_local_ip(self) -> str:
        """获取本机局域网 IP"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def _update_network_info(self, ip: str, port: int):
        pass

    def _on_db_ready(self, result):
        """DB 初始化完成回调"""
        if isinstance(result, Exception):
            self.statusBar().showMessage(f"初始化失败: {result}")
            self.skeleton_label.setText(f"初始化失败: {result}")
            return

        self.session = result

        # 初始化默认权限用户（admin，拥有所有权限）
        user = self.session.query(User).filter_by(username="admin").first()
        if not user:
            role = self.session.query(Role).filter_by(name="admin").first()
            if not role:
                role = Role(
                    name="admin",
                    description="超级管理员",
                    permissions=",".join([p.value for p in Permission]),
                )
                self.session.add(role)
                self.session.flush()
            user = User(username="admin", display_name="系统管理员", role=role, is_active=True)
            self.session.add(user)
            self.session.commit()

        # 登录验证：模态登录框（阻塞直到用户登录/取消），验证通过才进入主界面
        # 注：exec_() 嵌套在 finished 信号回调中是安全的（主事件循环已运行）；
        # 之前"卡死"真因是首次引导 QMessageBox 模态弹窗，已改为内联提示
        # 已有登录态（如测试/热重载场景）则跳过登录框，直接进入主界面（幂等）
        from edu_system.core.permissions import get_current_user

        current = get_current_user()
        if current is not None:
            self._enter_main(current)
            return

        from edu_system.gui.dialogs import LoginDialog

        login_dlg = LoginDialog(self.session, parent=self)
        if login_dlg.exec_() == LoginDialog.Accepted:
            user = login_dlg.get_user()
            set_current_user(user)
            self._enter_main(user)
        else:
            # 用户取消登录 → 退出应用
            self.close()

    def _enter_main(self, user):
        """登录成功后进入主界面"""
        # 隐藏骨架屏
        self.skeleton_label.hide()

        # 数据驱动构建所有工作台
        self._build_all_workbenches()

        # 设置侧栏首个按钮选中
        self.sidebar.btns[0][0].setChecked(True)
        self.sidebar.btns[0][0].setStyleSheet(_nav_btn_style(True))

        # 更新学期显示
        self._update_semester_display()

        self.statusBar().showMessage("就绪", 3000)

    def _update_semester_display(self):
        """更新顶部栏学期显示（从数据库读取当前激活学期）"""
        if self.session is None:
            return
        from edu_system.services.semester import SemesterService
        svc = SemesterService(self.session)
        current = svc.get_active()
        if current:
            self.topbar.set_semester(current.label)
        else:
            self.topbar.set_semester("未设置当前学期")

    def _build_all_workbenches(self):
        """根据 UIConfig 动态构建所有工作台"""
        self._workbenches = []

        for domain in self._ui_config.domains_parsed:
            # tabs: [TabConfig{id,title,view,default}] → WorkbenchWidget 期望 [(title, view_id), ...]
            tab_configs = []
            for t in domain["tabs"]:
                title = t.title if hasattr(t, "title") else t["title"]
                view = t.view if hasattr(t, "view") else t["view"]
                tab_configs.append((title, view))
            wb = WorkbenchWidget(None, tab_configs, domain["title"])
            if self.session is not None:
                wb.set_session(self.session)
            self._workbenches.append(wb)
            self.content_stack.addWidget(wb)

    def _on_sidebar_selected(self, idx):
        """侧栏按钮点击"""
        self._load_workbench(idx)

    def _load_workbench(self, idx):
        """加载指定工作台"""
        content_idx = idx + 1  # 0 是 skeleton
        if content_idx == self.content_stack.currentIndex() and idx < len(self._workbenches):
            return

        self.content_stack.setCurrentIndex(idx + 1)
        wb = self._workbenches[idx]
        wb.ensure_loaded()

    def _on_command_palette_action(self, view_id: str):
        """处理命令面板触发的动作"""
        # 先记录访问（用于最近访问）
        for domain in self._ui_config.domains_parsed:
            for tab in domain["tabs"]:
                tab_view = tab.view if hasattr(tab, "view") else tab["view"]
                tab_title = tab.title if hasattr(tab, "title") else tab["title"]
                if tab_view == view_id:
                    if hasattr(self, "_recent_visits"):
                        self._recent_visits.add_visit(view_id, tab_title)
                        if hasattr(self, "_update_recent_list"):
                            self._update_recent_list()
                    break

        # 加载对应工作台
        for idx, domain in enumerate(self._ui_config.domains_parsed):
            for tab in domain["tabs"]:
                tab_view = tab.view if hasattr(tab, "view") else tab["view"]
                if tab_view == view_id:
                    self._load_workbench(idx)
                    # 同步侧栏选中状态
                    self.sidebar.btns[idx][0].setChecked(True)
                    self.sidebar.btns[idx][0].setStyleSheet(_nav_btn_style(True))
                    for i, (btn, _) in enumerate(self.sidebar.btns):
                        if i != idx:
                            btn.setChecked(False)
                            btn.setStyleSheet(_nav_btn_style(False))
                    return

    def closeEvent(self, event):
        if self.session:
            self.session.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    f = QFont()
    f.setPointSize(9)
    f.setFamily("Microsoft YaHei")
    app.setFont(f)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
