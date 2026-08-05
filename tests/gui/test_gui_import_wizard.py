"""
导入向导 GUI 测试（M5-D2）

覆盖：
- 向导组件齐全（文件区/映射表单/预览表/操作按钮）
- 文件解析：_set_file 后解析按钮启用，解析填充映射下拉
- 字段映射收集：标准列名 → 源列名
- 规则预览：质量报告展示 + 入库按钮按错误状态启用
- 入库流程：insert_fn 被调用（模拟）
"""

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui  # 仅 GUI job（xvfb）运行

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PyQt5.QtWidgets import QApplication, QTableWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def session():
    """内存 SQLite 会话（admin + 学期 + 班级）"""
    from datetime import date

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.core.permissions import Permission
    from edu_system.models import (
        AcademicYear,
        Base,
        Class,
        Grade,
        Role,
        Semester,
        SemesterStatus,
        User,
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    admin_role = Role(
        name="admin", description="管理员",
        permissions=",".join([p.value for p in Permission]),
    )
    s.add(admin_role)
    s.flush()
    s.add(User(username="admin", display_name="管理员", role_id=admin_role.id))

    ay = AcademicYear(name="2024-2025", sort_order=0, is_active=True)
    s.add(ay)
    s.flush()
    sem = Semester(
        academic_year_id=ay.id, year_start=2024, semester="1",
        label="2024-2025 第1学期", sort_order=1, is_active=True,
        status=SemesterStatus.active, start_date=date(2024, 9, 1),
        end_date=date(2025, 1, 15),
    )
    s.add(sem)
    s.flush()

    grade = Grade(name="一年级", sort_order=1)
    s.add(grade)
    s.flush()
    s.add(Class(name="一班", grade_id=grade.id, semester_id=sem.id))
    s.commit()
    yield s
    s.close()


def _make_xlsx(path: Path, rows: list[dict] | None = None):
    """生成含表头的 xlsx"""
    from openpyxl import Workbook

    rows = rows or [
        {"学号": "20240001", "姓名": "张三", "性别": "男", "班级": "一班", "年级": "一年级"},
        {"学号": "20240002", "姓名": "李四", "性别": "女", "班级": "一班", "年级": "一年级"},
    ]
    wb = Workbook()
    ws = wb.active
    headers = list(rows[0].keys())
    ws.append(headers)
    for r in rows:
        ws.append([r[h] for h in headers])
    wb.save(path)
    wb.close()
    return path


@pytest.fixture
def wizard(qapp, session):
    from edu_system.gui.views.import_wizard import ImportWizard

    w = ImportWizard(session)
    w.show()
    yield w
    w.close()


class TestWizardComponents:
    def test_components_exist(self, wizard):
        """向导组件齐全：文件区/解析/预览表/操作按钮"""
        assert wizard.load_btn is not None
        assert wizard.preview_btn is not None
        assert wizard.import_btn is not None
        assert isinstance(wizard._preview_table, QTableWidget)
        # 映射表单有 6 个标准字段下拉
        assert len(wizard._map_widgets) == 6

    def test_initial_button_states(self, wizard):
        """初始状态：解析/预览/入库均禁用"""
        assert not wizard.load_btn.isEnabled()
        assert not wizard.preview_btn.isEnabled()
        assert not wizard.import_btn.isEnabled()

    def test_set_file_enables_load(self, wizard):
        """选择文件后解析按钮启用"""
        wizard._set_file("/tmp/fake.xlsx")
        assert wizard.load_btn.isEnabled()
        assert "fake.xlsx" in wizard._file_label.text()


class TestParseAndMapping:
    @pytest.fixture(autouse=True)
    def _no_msgbox(self, monkeypatch):
        """屏蔽模态弹窗（offscreen 无人点击会阻塞）"""
        monkeypatch.setattr(
            "edu_system.gui.views.import_wizard.QMessageBox.information",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "edu_system.gui.views.import_wizard.QMessageBox.critical",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "edu_system.gui.views.import_wizard.QMessageBox.warning",
            lambda *a, **k: None,
        )

    def test_parse_fills_mapping(self, wizard, tmp_path):
        """解析文件后映射下拉填充源列"""
        f = _make_xlsx(tmp_path / "students.xlsx")
        wizard._file_path = str(f)
        wizard._parse_file()
        assert wizard._df is not None
        assert len(wizard._df) == 2
        # 学号下拉自动匹配「学号」
        cb = wizard._map_widgets["student_code"]
        assert cb.currentData() == "学号", f"学号应自动匹配: {cb.currentData()}"

    def test_parse_invalid_file(self, wizard, tmp_path):
        """无效文件解析失败提示"""
        bad = tmp_path / "bad.txt"
        bad.write_text("not a table")
        wizard._file_path = str(bad)
        wizard._parse_file()
        assert wizard._df is None

    def test_build_mapping(self, wizard, tmp_path):
        """映射收集：标准列 → 源列"""
        f = _make_xlsx(tmp_path / "students.xlsx")
        wizard._file_path = str(f)
        wizard._parse_file()
        mapping = wizard._build_mapping()
        assert mapping.get("学号") == "学号"
        assert mapping.get("姓名") == "姓名"


class TestPreviewAndImport:
    @pytest.fixture(autouse=True)
    def _no_msgbox(self, monkeypatch):
        """屏蔽模态弹窗（offscreen 无人点击会阻塞）"""
        monkeypatch.setattr(
            "edu_system.gui.views.import_wizard.QMessageBox.information",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "edu_system.gui.views.import_wizard.QMessageBox.warning",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "edu_system.gui.views.import_wizard.QMessageBox.critical",
            lambda *a, **k: None,
        )

    def test_preview_shows_report(self, wizard, tmp_path):
        """规则预览展示质量报告"""
        f = _make_xlsx(tmp_path / "students.xlsx")
        wizard._file_path = str(f)
        wizard._parse_file()
        wizard._preview()
        assert wizard._stage is not None
        assert "验证报告" in wizard._report_label.text()
        # 无错误 → 入库按钮启用
        assert wizard.import_btn.isEnabled()

    def test_import_calls_insert(self, wizard, tmp_path, monkeypatch):
        """入库调用 insert_fn（mock ImportService）"""
        f = _make_xlsx(tmp_path / "students.xlsx")
        wizard._file_path = str(f)
        wizard._parse_file()
        wizard._preview()

        calls = {"n": 0}

        def fake_import_students(self, path, mapping=None):
            calls["n"] += 1
            return 2

        monkeypatch.setattr(
            "edu_system.services.importer.ImportService.import_students_from_excel",
            fake_import_students,
        )
        monkeypatch.setattr(
            "edu_system.gui.views.import_wizard.QMessageBox.information",
            lambda *a, **k: None,
        )

        wizard._import()
        assert calls["n"] == 1
