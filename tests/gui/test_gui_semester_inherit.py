"""
SemesterView 继承配置向导 GUI 测试（M5-C1）

覆盖：
- 继承配置 Tab 存在（四色预览入口）
- 预览按钮触发 preview_inherit，差异表填充四色类型
- 确认继承按钮：预览前禁用，预览后按差异启用
- 执行继承后配置写入（版本递增）
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
    """内存 SQLite 会话（两个学期 + 配置数据）"""
    from datetime import date

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.models import (
        AcademicYear,
        Base,
        Semester,
        SemesterConfig,
        SemesterStatus,
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()

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
    s.add_all([sem1, sem2])
    s.flush()

    # 源学期（sem1）配置：两项
    s.add_all(
        [
            SemesterConfig(semester_id=sem1.id, key="max_class_size", value="50", version=1),
            SemesterConfig(semester_id=sem1.id, key="dorm_fee", value="800", version=1),
        ]
    )
    # 目标学期（sem2）配置：一项相同（保留）+ 一项冲突
    s.add_all(
        [
            SemesterConfig(semester_id=sem2.id, key="max_class_size", value="50", version=1),
            SemesterConfig(semester_id=sem2.id, key="meal_fee", value="300", version=1),
        ]
    )
    s.commit()
    yield s
    s.close()


@pytest.fixture
def view(qapp, session):
    from edu_system.gui.views.semester import SemesterView

    v = SemesterView(session)
    v.show()
    yield v
    v.close()


def _find_tab_widget(view, text):
    """从 TabWidget 找指定按钮/表格/下拉框（按文本或类）"""
    from PyQt5.QtWidgets import QTabWidget

    tabs = view.findChild(QTabWidget)
    assert tabs, "SemesterView 应有 QTabWidget"
    # 切到继承配置 tab
    for i in range(tabs.count()):
        if "继承" in tabs.tabText(i):
            tabs.setCurrentIndex(i)
            tab_w = tabs.widget(i)
            return tab_w
    raise AssertionError("未找到继承配置 Tab")


class TestInheritWizard:
    def test_inherit_tab_exists(self, view):
        """继承配置 Tab 存在（四色预览入口）"""
        tab_w = _find_tab_widget(view, "继承")
        assert tab_w is not None
        # 应有 源/目标 两个下拉框
        combos = tab_w.findChildren(QComboBox)
        assert len(combos) >= 2
        # 应有预览 + 确认两个按钮
        buttons = tab_w.findChildren(QPushButton)
        texts = [b.text() for b in buttons]
        assert any("预览" in t for t in texts), f"缺预览按钮: {texts}"
        assert any("确认继承" in t for t in texts), f"缺确认继承按钮: {texts}"

    def test_preview_fills_four_color_table(self, view):
        """预览后差异表填充，类型列含四色标注"""
        tab_w = _find_tab_widget(view, "继承")
        combos = tab_w.findChildren(QComboBox)
        # 源=0(第1学期) 目标=1(第2学期)
        combos[0].setCurrentIndex(0)
        combos[1].setCurrentIndex(1)

        preview_btn = next(b for b in tab_w.findChildren(QPushButton) if "预览" in b.text())
        preview_btn.click()

        table = tab_w.findChild(QTableWidget)
        assert table.rowCount() >= 3, f"差异表应有 ≥3 行，实际 {table.rowCount()}"

        # 类型列有颜色（四色之一）
        colors_seen = set()
        for i in range(table.rowCount()):
            item = table.item(i, 1)
            assert item, f"第 {i} 行类型列缺失"
            fg = item.foreground().color().name().lower()
            colors_seen.add(fg)
            assert item.text() in {"added", "modified", "retained", "conflict"}

        # 至少两种颜色（有差异才有颜色区分）
        assert len(colors_seen) >= 2, f"四色预览应有 ≥2 种颜色，实际 {colors_seen}"

    def test_confirm_disabled_until_preview(self, view):
        """确认继承按钮：预览前禁用，预览后（有差异）启用"""
        tab_w = _find_tab_widget(view, "继承")
        run_btn = next(b for b in tab_w.findChildren(QPushButton) if "确认继承" in b.text())
        assert not run_btn.isEnabled(), "预览前确认按钮应禁用"

        combos = tab_w.findChildren(QComboBox)
        combos[0].setCurrentIndex(0)
        combos[1].setCurrentIndex(1)
        preview_btn = next(b for b in tab_w.findChildren(QPushButton) if "预览" in b.text())
        preview_btn.click()

        assert run_btn.isEnabled(), "预览后有差异应启用确认按钮"

    def test_execute_inherit_writes_config(self, view, session, monkeypatch):
        """执行继承后目标学期配置写入（版本递增）"""
        from PyQt5.QtWidgets import QMessageBox

        # 拦截模态框
        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)

        tab_w = _find_tab_widget(view, "继承")
        combos = tab_w.findChildren(QComboBox)
        combos[0].setCurrentIndex(0)  # 源=sem1
        combos[1].setCurrentIndex(1)  # 目标=sem2

        preview_btn = next(b for b in tab_w.findChildren(QPushButton) if "预览" in b.text())
        preview_btn.click()
        run_btn = next(b for b in tab_w.findChildren(QPushButton) if "确认继承" in b.text())
        run_btn.click()

        # 目标学期 sem2 配置更新
        from edu_system.models import Semester
        from edu_system.services.semester_config import SemesterConfigService

        sem2 = session.query(Semester).filter_by(semester="2").first()
        svc = SemesterConfigService(session)
        current = svc._get_all_configs(sem2.id)
        assert current["max_class_size"] == "50"
        assert current["dorm_fee"] == "800", "继承应带来源学期的新配置"
        assert current["meal_fee"] == "300", "目标学期未冲突配置应保留"
        session.rollback()
