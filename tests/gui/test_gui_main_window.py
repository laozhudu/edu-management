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
    """内存 SQLite 会话（含 admin 用户 + 默认学期）"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.core.permissions import Permission
    from edu_system.database import init_db_with_defaults
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
    
    # 初始化默认学期（通过 init_db_with_defaults 的默认数据逻辑）
    from edu_system.models import AcademicYear, Semester, SemesterStatus, Grade, Subject, GlobalSetting
    from datetime import date
    
    # 默认年级
    for i, name in enumerate(["初一级", "初二级", "初三级"]):
        if not s.query(Grade).filter_by(name=name).first():
            s.add(Grade(name=name, sort_order=i))
    
    # 默认科目
    defaults = [
        ("语文", 120, 72, 84, 96, 36),
        ("数学", 120, 72, 84, 96, 36),
        ("英语", 120, 72, 84, 96, 36),
        ("政治", 80, 48, 56, 64, 24),
        ("物理", 100, 60, 70, 80, 30),
        ("化学", 80, 48, 56, 64, 24),
        ("历史", 80, 48, 56, 64, 24),
        ("地理", 100, 60, 70, 80, 30),
        ("生物", 100, 60, 70, 80, 30),
        ("体育", 70, 42, 49, 56, 21),
    ]
    for i, (name, fm, pl, gl, el, ll) in enumerate(defaults):
        if not s.query(Subject).filter_by(name=name).first():
            s.add(
                Subject(
                    name=name,
                    full_mark=fm,
                    pass_line=pl,
                    good_line=gl,
                    excellent_line=el,
                    low_line=ll,
                    sort_order=i,
                )
            )
    
    # 默认学年/学期
    ay = s.query(AcademicYear).filter_by(name="2024-2025").first()
    if not ay:
        ay = AcademicYear(
            name="2024-2025", sort_order=0, is_active=True, description="2024-2025 学年"
        )
        s.add(ay)
        s.flush()

    sem1 = s.query(Semester).filter_by(academic_year_id=ay.id, semester="1").first()
    if not sem1:
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

    sem2 = s.query(Semester).filter_by(academic_year_id=ay.id, semester="2").first()
    if not sem2:
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
    
    # 默认缺考标记
    if not s.query(GlobalSetting).filter_by(key="absent_marks").first():
        s.add(GlobalSetting(key="absent_marks", value="-1,0"))
    
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
        assert texts == ["2024-2025 第1学期"], f"顶部栏应只有学期字样，实际: {texts}"

    def test_semester_standard_format(self, main_window):
        """学年度使用标准写法：2024-2025 第1学期"""
        assert main_window.topbar.semester_label.text() == "2024-2025 第1学期"

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
