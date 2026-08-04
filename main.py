#!/usr/bin/env python3
"""
教务管理系统（开发版）
PyQt5 桌面版统一入口（无启动屏，直接进入主界面 → 登录框）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# 崩溃防护：全局异常捕获 + Qt 消息捕获（必须在任何 GUI 代码之前安装）
from edu_system.gui.crash_guard import (
    install_global_excepthook,
    install_qt_message_handler,
    run_preflight,
)

install_global_excepthook()
install_qt_message_handler()

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

APP_NAME = "教务管理系统"


class DBInitWorker(QThread):
    """后台初始化线程：只做 DB 初始化和数据预加载，不创建 GUI 对象"""

    finished = pyqtSignal(object)  # 传回 session
    error = pyqtSignal(str)

    def run(self):
        try:
            # 注意：必须用 edu_system 导入（与全项目一致），
            # 用 src.edu_system 会双份加载模块导致全局状态错乱
            from edu_system.database import get_session, init_db_with_defaults

            init_db_with_defaults()
            session = get_session()

            # 预加载基础数据（年级、班级、学科等），避免首屏卡顿
            from edu_system.models import Class, Grade, Semester, Subject

            _ = list(session.query(Grade).all())
            _ = list(session.query(Class).all())
            _ = list(session.query(Subject).all())
            _ = list(session.query(Semester).all())

            self.finished.emit(session)
        except Exception as e:
            self.error.emit(str(e))


def main():
    # 2. 创建应用
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    f = QFont()
    f.setPointSize(10)
    # 字体：Windows 用微软雅黑；Linux 用文泉驿微米黑（避免 DejaVu fallback 行高挤压）
    if sys.platform == "win32":
        f.setFamily("微软雅黑")
    else:
        f.setFamily("文泉驿微米黑")
    app.setFont(f)

    # 2. 后台初始化 DB
    worker = DBInitWorker()

    def on_db_ready(session):
        # 3. DB 就绪后，在主线程创建 MainWindow
        # 启动自检：config/registry/DB 预检，有问题则明示（不再静默打不开）
        run_preflight()

        from edu_system.gui.main_window import MainWindow

        w = MainWindow(session)  # 传入已初始化的 session
        w.show()
        # 保持窗口引用，防止被 GC
        import builtins

        builtins._main_window_ref = w
        worker.deleteLater()

    def on_error(err):
        from PyQt5.QtWidgets import QMessageBox

        QMessageBox.critical(None, "启动失败", f"数据库初始化失败:\n{err}")
        QTimer.singleShot(3000, app.quit)

    worker.finished.connect(on_db_ready)
    worker.error.connect(on_error)
    worker.start()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
