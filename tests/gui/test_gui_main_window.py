"""
MainWindow GUI 加固测试
覆盖：顶部栏学期居中显示、侧边栏收缩展开无异常、界面无冗余学校字样
防止后续 UI 改动引入回归
"""

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui  # 仅 GUI job（xvfb）运行

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PyQt5.QtWidgets import QApplication, QLabel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def session():
    """内存 SQLite 会话（含 admin 用户）"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.core.permissions import Permission
    from edu_system.models import Base, Role, User

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    admin_role = Role(
        name="admin",
        description="超级管理员",
        permissions=",".join([p.value for p in Permission]),
    )
    s.add(admin_role)
    s.add(User(username="admin", password_hash="x", role=admin_role))
    s.commit()
    yield s
    s.close()


@pytest.fixture
def main_window(qapp, session):
    from edu_system.core.permissions import set_current_user
    from edu_system.gui.main_window import MainWindow
    from edu_system.models import User

    w = MainWindow(session)
    # 预置登录态：跳过 LoginDialog 模态框（_on_db_ready 检测已有登录态直接进入主界面）
    admin = session.query(User).filter_by(username="admin").first()
    set_current_user(admin)
    w.show()
    yield w
    set_current_user(None)  # 清理登录态
    w.close()


class TestTopBar:
    def test_topbar_only_semester(self, main_window):
        """顶部栏仅显示当前学年学期（无搜索框/面包屑等其他字样）"""
        topbar = main_window.topbar
        texts = [lbl.text() for lbl in topbar.findChildren(QLabel) if lbl.text()]
        assert texts == ["2026-2027学年度第一学期"], f"顶部栏应只有学期字样，实际: {texts}"

    def test_semester_standard_format(self, main_window):
        """学年度使用标准写法：2026-2027学年度第一学期"""
        assert main_window.topbar.semester_label.text() == "2026-2027学年度第一学期"

    def test_semester_not_green(self, main_window):
        """学期标签不使用绿色强调（业界审美：浅灰普通样式）"""
        qss = main_window.topbar.semester_label.styleSheet()
        assert "accent_green" not in qss
        assert "27AE60" not in qss  # 绿色 hex 不出现

    def test_semester_centered(self, main_window):
        """学期标签水平居中（偏差 < 30px）"""
        topbar = main_window.topbar
        sw = topbar.semester_label.width()
        tw = topbar.width()
        x = topbar.semester_label.x()
        center_off = abs((x + sw / 2) - tw / 2)
        assert center_off < 30, f"学期未居中，偏差 {center_off}px"


class TestSidebar:
    def test_toggle_no_error(self, main_window):
        """侧边栏收缩/展开不抛异常（历史 bug：logo_label 残留引用）"""
        w = main_window
        w.sidebar.toggle()  # 收缩
        assert w.sidebar.width() <= w.sidebar._width_expanded
        w.sidebar.toggle()  # 展开
        assert w.sidebar.width() >= w.sidebar._width_collapsed

    def test_double_toggle_no_error(self, main_window):
        """连续两次收缩（动画中）不抛异常"""
        w = main_window
        w.sidebar.toggle()
        w.sidebar.toggle()
        w.sidebar.toggle()
        assert True  # 到达此处即无异常


class TestNoRedundantBranding:
    def test_no_logo_in_sidebar(self, main_window):
        """侧边栏不再显示学校 logo（用户要求删除冗余字样）"""
        sidebar = main_window.sidebar
        texts = [lbl.text() for lbl in sidebar.findChildren(QLabel) if lbl.text()]
        assert not any("城南" in t or "教务系统" in t for t in texts), f"侧边栏残留字样: {texts}"

    def test_no_breadcrumb_attr(self, main_window):
        """顶部栏无 breadcrumb 属性（已移除）"""
        assert not hasattr(main_window.topbar, "breadcrumb")
