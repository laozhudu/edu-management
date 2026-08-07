"""
ReportView 模板管理 + 批量打印 Tab GUI 测试（M6 Sprint6）

覆盖：
- 报表生成 Tab 存在（考试选择 + 6 个生成按钮）
- 模板管理 Tab 存在（注册输入 + 模板列表）
- 模板注册流程（选择文件 → 扫描变量 → 列表刷新）
- 批量打印 Tab 存在（考试选择 + 生成按钮 + 进度条）
"""

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui  # 仅 GUI job（xvfb）运行

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PyQt5.QtWidgets import QApplication, QComboBox, QPushButton, QTableWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def session():
    """内存 SQLite 会话（一个考试 + 一个模板）"""
    from datetime import date

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.models import (
        AcademicYear,
        Base,
        Exam,
        Grade,
        ReportTemplate,
        Semester,
        SemesterStatus,
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

    g = Grade(name="初一", sort_order=1)
    s.add(g)
    s.flush()

    s.add(Exam(semester_id=sem.id, grade_id=g.id, name="期中考试", exam_type="期中"))
    s.add(
        ReportTemplate(
            name="成绩单模板",
            template_type="word",
            file_path="/tmp/tpl.docx",
            version=1,
            is_active=True,
            description="测试模板",
            created_by="admin",
            variables="[]",
        )
    )
    s.commit()
    yield s
    s.close()


@pytest.fixture
def view(qapp, session):
    from edu_system.gui.views.report import ReportView

    v = ReportView(session)
    v.show()
    yield v
    v.close()


def _find_tab(view, text):
    from PyQt5.QtWidgets import QTabWidget

    tabs = view.findChild(QTabWidget)
    assert tabs, "ReportView 应有 QTabWidget"
    for i in range(tabs.count()):
        if text in tabs.tabText(i):
            tabs.setCurrentIndex(i)
            return tabs.widget(i)
    raise AssertionError(f"未找到 Tab: {text}")


class TestReportTabs:
    def test_generate_tab_exists(self, view):
        """报表生成 Tab：考试选择 + 生成按钮"""
        tab_w = _find_tab(view, "报表生成")
        combos = tab_w.findChildren(QComboBox)
        assert len(combos) >= 1, "应有考试选择下拉框"

        buttons = [b.text() for b in tab_w.findChildren(QPushButton)]
        assert any("成绩报表" in t for t in buttons), f"缺成绩报表按钮: {buttons}"
        assert any("成绩单" in t for t in buttons), f"缺成绩单按钮: {buttons}"
        assert any("奖状" in t for t in buttons), f"缺奖状按钮: {buttons}"

    def test_template_tab_exists(self, view):
        """模板管理 Tab：注册输入 + 模板列表"""
        tab_w = _find_tab(view, "模板管理")
        table = tab_w.findChild(QTableWidget)
        assert table is not None, "应有模板列表表格"

        # 预置模板应显示
        assert table.rowCount() >= 1, f"应有 ≥1 个模板，实际 {table.rowCount()}"
        assert table.item(0, 0).text() == "成绩单模板"
        assert table.item(0, 1).text() == "word"
        assert "v1" in table.item(0, 2).text()

    def test_batch_tab_exists(self, view):
        """批量打印 Tab：考试选择 + 生成按钮 + 进度条"""
        tab_w = _find_tab(view, "批量打印")
        combos = tab_w.findChildren(QComboBox)
        assert len(combos) >= 1, "应有考试选择下拉框"

        buttons = [b.text() for b in tab_w.findChildren(QPushButton)]
        assert any("批量生成" in t for t in buttons), f"缺批量生成按钮: {buttons}"
        assert any("打印" in t for t in buttons), f"缺打印按钮: {buttons}"

        from PyQt5.QtWidgets import QProgressBar

        progress = tab_w.findChild(QProgressBar)
        assert progress is not None, "应有进度条"

    def test_template_register_flow(self, view, session, monkeypatch, tmp_path):
        """模板注册流程：文件选择 → 变量扫描 → 列表刷新"""
        from PyQt5.QtWidgets import QFileDialog, QLineEdit, QMessageBox

        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)

        # 创建测试模板文件（Excel 含 {{name}} 占位符）
        tpl_file = tmp_path / "score_template.xlsx"
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws["A1"] = "姓名: {{name}}  总分: {{total}}"
        wb.save(str(tpl_file))

        monkeypatch.setattr(
            QFileDialog, "getOpenFileName", lambda *a, **k: (str(tpl_file), "")
        )

        tab_w = _find_tab(view, "模板管理")
        name_input = tab_w.findChild(QLineEdit)
        name_input.setText("新模板")

        # 点击注册按钮
        reg_btn = next(b for b in tab_w.findChildren(QPushButton) if "注册" in b.text())
        reg_btn.click()

        # 模板列表刷新，新增一行
        table = tab_w.findChild(QTableWidget)
        names = {table.item(i, 0).text() for i in range(table.rowCount())}
        assert "新模板" in names, f"注册后应有新模板，实际 {names}"

        # 数据库已写入
        from edu_system.models import ReportTemplate

        tpl = session.query(ReportTemplate).filter_by(name="新模板").first()
        assert tpl is not None, "数据库应有新模板"
        assert tpl.template_type == "excel"
        session.rollback()
