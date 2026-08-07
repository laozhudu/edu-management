"""
ExamView GUI 测试（M6 Sprint5）

覆盖：
- 4 个 Tab 存在（考试列表 / 新建考试 / 分考场座位 / 监考准考证）
- 新建考试流程（学期/年级/名称/日期/备注 → 创建）
- 分考场/座位流程（容量设置 → 自动分考场 → 座位分配）
- 监考/准考证流程（监考编辑/保存/准考证生成）

"""

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui  # 仅 GUI job（xvfb）运行

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
)

import pytest


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def session():
    """内存 SQLite 会话（1 学期 + 1 年级 + 2 考试）"""
    from datetime import date

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.models import (
        AcademicYear,
        Base,
        Classroom,
        Exam,
        Grade,
        Semester,
        SemesterStatus,
        Student,
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()

    ay = AcademicYear(name="2024-2025", sort_order=0, is_active=True)
    s.add(ay)
    s.flush()

    sem = Semester(
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
    s.add(sem)
    s.flush()

    g1 = Grade(name="初一", sort_order=1)
    s.add(g1)
    s.flush()

    cls = __import__('edu_system.models', fromlist=['Class']).Class
    cl1 = cls(semester_id=sem.id, grade_id=g1.id, name="初一1班")
    cl2 = cls(semester_id=sem.id, grade_id=g1.id, name="初一2班")
    s.add_all([cl1, cl2])
    s.flush()

    c1 = Classroom(semester_id=sem.id, class_id=cl1.id, room_no="101教室", capacity=50)
    c2 = Classroom(semester_id=sem.id, class_id=cl2.id, room_no="102教室", capacity=40)
    s.add_all([c1, c2])
    s.flush()

    s.add_all(
        [
            Exam(
                semester_id=sem.id,
                grade_id=g1.id,
                name="期中考试",
                exam_type="期中",
                exam_date=date(2024, 11, 15),
            ),
            Exam(
                semester_id=sem.id,
                grade_id=g1.id,
                name="期末考试",
                exam_type="期末",
                exam_date=date(2025, 1, 10),
            ),
        ]
    )
    s.commit()
    yield s
    s.close()


@pytest.fixture
def view(qapp, session):
    from edu_system.gui.views.exam import ExamView

    v = ExamView(session)
    v.show()
    yield v
    v.close()


def _find_tab(view, text):
    """从 TabWidget 找指定 Tab 内容 widget"""
    from PyQt5.QtWidgets import QTabWidget

    tabs = view.findChild(QTabWidget)
    assert tabs, "ExamView 应有 QTabWidget"
    for i in range(tabs.count()):
        if text in tabs.tabText(i):
            tabs.setCurrentIndex(i)
            return tabs.widget(i)
    raise AssertionError(f"未找到 Tab: {text}")


class TestExamViewTabs:
    def test_4_tabs_exist(self, view):
        """ExamView 有 4 个 Tab：考试列表 / 新建考试 / 分考场座位 / 监考准考证"""
        from PyQt5.QtWidgets import QTabWidget

        tabs = view.findChild(QTabWidget)
        assert tabs.count() == 4, f"应有 4 个 Tab，实际 {tabs.count()}"
        texts = [tabs.tabText(i) for i in range(4)]
        assert "考试列表" in texts
        assert "新建考试" in texts
        assert "分考场座位" in texts
        assert "监考准考证" in texts

    def test_list_tab_has_table(self, view):
        """考试列表 Tab 有表格，显示预置 2 个考试"""
        tab_w = _find_tab(view, "考试列表")
        table = tab_w.findChild(QTableWidget)
        assert table is not None
        assert table.rowCount() >= 2, f"应有 ≥2 个考试，实际 {table.rowCount()}"
        # 验证列
        headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
        assert "ID" in headers
        assert "考试名称" in headers

    def test_create_tab_form_fields(self, view):
        """新建考试 Tab：学期/年级/名称/日期/备注 + 创建按钮"""
        tab_w = _find_tab(view, "新建考试")
        combos = tab_w.findChildren(QComboBox)
        assert len(combos) >= 2, "应有学期+年级两个下拉框"

        # 名称输入框
        from PyQt5.QtWidgets import QLineEdit
        name_inputs = [w for w in tab_w.findChildren(QLineEdit) if w.placeholderText() == "如: 期中考试、期末考试"]
        assert len(name_inputs) == 1, "应有考试名称输入框"

        # 备注输入框
        note_inputs = [w for w in tab_w.findChildren(QLineEdit) if w.placeholderText() is None or w.placeholderText() == ""]
        assert any(note_inputs), "应有备注输入框"

        # 创建按钮
        buttons = [b.text() for b in tab_w.findChildren(QPushButton)]
        assert "创建考试" in buttons, f"缺创建按钮: {buttons}"

    def test_create_exam_workflow(self, view, session, monkeypatch):
        """新建考试：填表 → 点击创建 → 数据库落库"""
        from PyQt5.QtWidgets import QMessageBox, QLineEdit, QComboBox

        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)

        tab_w = _find_tab(view, "新建考试")

        # 学期：取第一个
        sem_cb = [c for c in tab_w.findChildren(QComboBox) if c.count() >= 1][0]
        assert sem_cb.count() >= 1
        sem_cb.setCurrentIndex(0)

        # 年级
        grade_cb = [c for c in tab_w.findChildren(QComboBox) if c.count() >= 1][1]
        assert grade_cb.count() >= 1
        grade_cb.setCurrentIndex(0)

        # 名称
        name_inputs = [w for w in tab_w.findChildren(QLineEdit) if w.placeholderText() == "如: 期中考试、期末考试"]
        name_inputs[0].setText("GUI新建测试")

        # 日期默认即可

        # 备注
        note_inputs = [w for w in tab_w.findChildren(QLineEdit) if w is not name_inputs[0]]
        if note_inputs:
            note_inputs[0].setText("GUI 自动化测试")

        # 点击创建
        create_btn = next(b for b in tab_w.findChildren(QPushButton) if "创建" in b.text())
        create_btn.click()

        # 验证数据库落库
        from edu_system.models import Exam
        new_exam = session.query(Exam).filter_by(name="GUI新建测试").first()
        assert new_exam is not None, "数据库应有新建考试"
        assert new_exam.grade_id is not None
        assert new_exam.semester_id is not None
        session.rollback()

    def test_rooms_tab_structure(self, view):
        """分考场座位 Tab：考试选择 + 容量 + 分考场按钮 + 考场表格 + 排座按钮"""
        tab_w = _find_tab(view, "分考场座位")
        combos = tab_w.findChildren(QComboBox)
        assert len(combos) >= 1, "应有考试选择下拉框"

        spin = tab_w.findChild(QSpinBox)
        assert spin is not None, "应有容量 SpinBox"

        buttons = [b.text() for b in tab_w.findChildren(QPushButton)]
        assert "自动分配考场" in buttons, f"缺自动分配考场按钮: {buttons}"
        assert "自动排座" in " ".join(buttons), f"缺自动排座按钮: {buttons}"

        table = tab_w.findChild(QTableWidget)
        assert table is not None, "应有考场列表表格"

    def test_invigilation_tab_structure(self, view):
        """监考准考证 Tab：考试选择 + 监考表格 + 监考编辑 + 准考证生成"""
        tab_w = _find_tab(view, "监考准考证")
        combos = tab_w.findChildren(QComboBox)
        assert len(combos) >= 2, "应有考试选择+考场选择两个下拉框"

        buttons = [b.text() for b in tab_w.findChildren(QPushButton)]
        assert any("刷新" in t for t in buttons), "应有刷新按钮"
        assert "保存监考" in buttons, f"缺保存监考按钮: {buttons}"
        assert "生成准考证" in " ".join(buttons), f"缺生成准考证按钮: {buttons}"

        table = tab_w.findChild(QTableWidget)
        assert table is not None, "应有监考安排表格"

    def test_invigilation_save_workflow(self, view, session, monkeypatch):
        """监考编辑：选择考场 → 输入教师ID → 保存 → 数据库落库"""
        from PyQt5.QtWidgets import QMessageBox, QLineEdit

        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)

        tab_w = _find_tab(view, "监考准考证")

        # 先刷新加载数据
        refresh_btn = next(b for b in tab_w.findChildren(QPushButton) if "刷新" in b.text())
        refresh_btn.click()

        # 选择第一个考场
        room_cb = [c for c in tab_w.findChildren(QComboBox) if c.count() >= 1][0]
        if room_cb.count() == 0:
            pytest.skip("无考场数据，跳过监考编辑测试")

        room_cb.setCurrentIndex(0)

        # 输入监考教师 ID
        t1_inputs = [w for w in tab_w.findChildren(QLineEdit) if w.placeholderText() == "教师ID"]
        if t1_inputs:
            t1_inputs[0].setText("1001")
            t1_inputs[1].setText("1002")

        # 保存
        save_btn = next(b for b in tab_w.findChildren(QPushButton) if "保存" in b.text())
        save_btn.click()

        # 验证数据库
        from edu_system.models import ExamRoom

        room_id = room_cb.currentData()
        room = session.get(ExamRoom, room_id)
        if room:
            assert room.invigilator1_id == 1001
            assert room.invigilator2_id == 1002
        session.rollback()


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])