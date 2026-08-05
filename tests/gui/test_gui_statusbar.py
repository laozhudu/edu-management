"""
主窗口状态栏局域网信息 GUI 测试（M5-D4）

覆盖：
- 状态栏含局域网地址 label（http://ip:port）
- 服务开关按钮（停止服务/启动服务切换）
- 二维码按钮存在
- _toggle_server 逻辑（模拟 ServerThread 状态）
"""

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui  # 仅 GUI job（xvfb）运行

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PyQt5.QtWidgets import QApplication, QLabel, QPushButton


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def session():
    """内存 SQLite 会话（admin 用户 + 默认学期）"""
    from datetime import date

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.core.permissions import Permission
    from edu_system.models import (
        AcademicYear,
        Base,
        GlobalSetting,
        Role,
        Semester,
        SemesterStatus,
        User,
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    admin_role = Role(
        name="admin",
        description="超级管理员",
        permissions=",".join([p.value for p in Permission]),
    )
    s.add(admin_role)
    s.flush()

    ay = AcademicYear(name="2024-2025", sort_order=0, is_active=True)
    s.add(ay)
    s.flush()

    sem1 = Semester(
        academic_year_id=ay.id,
        year_start=2024,
        semester="1",
        label="2024-2025 第1学期",
        sort_order=1,
        is_active=True,
        status=SemesterStatus.active,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 1, 15),
    )
    s.add(sem1)
    s.flush()

    sem2 = Semester(
        academic_year_id=ay.id,
        year_start=2024,
        semester="2",
        label="2024-2025 第2学期",
        sort_order=2,
        is_active=False,
        status=SemesterStatus.draft,
        start_date=date(2025, 2, 15),
        end_date=date(2025, 7, 15),
    )
    s.add(sem2)
    s.flush()

    if not s.query(GlobalSetting).filter_by(key="absent_marks").first():
        s.add(GlobalSetting(key="absent_marks", value="-1,0"))

    s.add(User(username="admin", display_name="管理员", role_id=admin_role.id))
    s.commit()
    yield s
    s.close()


@pytest.fixture
def main_window(qapp, session, monkeypatch):
    """构造 MainWindow（拦截 DB 初始化，预置登录态）"""
    from edu_system.core.permissions import set_current_user
    from edu_system.gui.main_window import MainWindow
    from edu_system.models import User

    monkeypatch.setattr(MainWindow, "_start_db_init", lambda self: None)
    w = MainWindow(session)
    # 预置登录态（同 test_gui_main_window 模式）
    admin = session.query(User).filter_by(username="admin").first()
    set_current_user(admin)
    # 手动触发 DB 就绪回调进入主界面（result = session）
    w._on_db_ready(session)
    w.show()
    yield w
    set_current_user(None)
    w.close()


def _call_update(mw):
    """调用 _update_network_info 填充状态栏"""
    mw._update_network_info("192.168.1.100", 8080)


class TestStatusBarNetwork:
    def test_net_label_shows_address(self, main_window):
        """状态栏显示局域网地址 + 端口"""
        _call_update(main_window)
        assert hasattr(main_window, "_net_label")
        assert main_window._net_label.text() == "局域网: http://192.168.1.100:8080"

    def test_server_switch_button(self, main_window):
        """服务开关按钮存在且初始为「停止服务」"""
        _call_update(main_window)
        assert hasattr(main_window, "_srv_switch_btn")
        assert main_window._srv_switch_btn.text() == "停止服务"

    def test_qr_button_exists(self, main_window):
        """二维码按钮存在"""
        _call_update(main_window)
        assert hasattr(main_window, "_qr_btn")
        assert main_window._qr_btn.text() == "二维码"

    def test_status_bar_contains_widgets(self, main_window):
        """状态栏实际包含持久控件"""
        _call_update(main_window)
        labels = [lb.text() for lb in main_window.statusBar().findChildren(QLabel)]
        assert any("局域网" in t for t in labels), f"状态栏缺地址: {labels}"
        buttons = [b.text() for b in main_window.statusBar().findChildren(QPushButton)]
        assert "停止服务" in buttons and "二维码" in buttons, f"状态栏缺按钮: {buttons}"

    def test_toggle_server_no_thread_safe(self, main_window):
        """无 server_thread 时切换安全返回"""
        _call_update(main_window)
        main_window._toggle_server()  # 不应抛异常
        assert True

    def test_toggle_server_starts_when_stopped(self, main_window, monkeypatch):
        """服务未运行：切换触发 start"""

        class FakeThread:
            def __init__(self):
                self.calls = []
                self._running = False

            def isRunning(self):
                return self._running

            def start(self):
                self.calls.append("start")
                self._running = True

            def stop(self):
                self.calls.append("stop")
                self._running = False

        ft = FakeThread()
        main_window._server_thread = ft
        _call_update(main_window)
        main_window._toggle_server()
        assert ft.calls == ["start"]

    def test_toggle_server_stops_when_running(self, main_window):
        """服务运行中：切换触发 stop"""

        class FakeThread:
            def __init__(self):
                self.calls = []
                self._running = True

            def isRunning(self):
                return self._running

            def start(self):
                self.calls.append("start")

            def stop(self):
                self.calls.append("stop")

        ft = FakeThread()
        main_window._server_thread = ft
        _call_update(main_window)
        main_window._toggle_server()
        assert ft.calls == ["stop"]
