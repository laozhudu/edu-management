"""
SemesterView 版本历史 Tab GUI 测试（M5-C2）

覆盖：
- 版本历史 Tab 存在（版本列表入口）
- 加载版本列表（版本号/时间/操作者/配置项数）
- 回滚按钮触发确认框 → 执行回滚 → 新版本写入
- 无版本时显示空状态
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
    """内存 SQLite 会话（两个学期 + 配置历史）"""
    from datetime import date

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.models import (
        AcademicYear,
        Base,
        Semester,
        SemesterConfig,
        SemesterConfigHistory,
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
    s.add(sem1)
    s.flush()

    # 当前配置 (v2)
    s.add_all(
        [
            SemesterConfig(semester_id=sem1.id, key="max_class_size", value="60", version=2),
            SemesterConfig(semester_id=sem1.id, key="dorm_fee", value="900", version=2),
        ]
    )
    # 历史快照 v1（回滚目标）
    s.add_all(
        [
            SemesterConfigHistory(
                semester_id=sem1.id,
                key="max_class_size",
                value="50",
                version=1,
                action="SAVE",
                operator="admin",
            ),
            SemesterConfigHistory(
                semester_id=sem1.id,
                key="dorm_fee",
                value="800",
                version=1,
                action="SAVE",
                operator="admin",
            ),
            SemesterConfigHistory(
                semester_id=sem1.id,
                key="max_class_size",
                value="60",
                version=2,
                action="SAVE",
                operator="admin",
            ),
            SemesterConfigHistory(
                semester_id=sem1.id,
                key="dorm_fee",
                value="900",
                version=2,
                action="SAVE",
                operator="admin",
            ),
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


def _find_version_tab(view):
    """切到版本历史 Tab，返回 tab widget"""
    from PyQt5.QtWidgets import QTabWidget

    tabs = view.findChild(QTabWidget)
    assert tabs, "SemesterView 应有 QTabWidget"
    for i in range(tabs.count()):
        if "版本" in tabs.tabText(i):
            tabs.setCurrentIndex(i)
            return tabs.widget(i)
    raise AssertionError("未找到版本历史 Tab")


class TestVersionHistoryTab:
    def test_version_tab_exists(self, view):
        """版本历史 Tab 存在，含学期下拉框 + 版本表格 + 刷新按钮"""
        tab_w = _find_version_tab(view)
        assert tab_w is not None

        combos = tab_w.findChildren(QComboBox)
        assert len(combos) >= 1, "应有学期选择下拉框"

        table = tab_w.findChild(QTableWidget)
        assert table is not None, "应有版本列表表格"

        buttons = tab_w.findChildren(QPushButton)
        texts = [b.text() for b in buttons]
        assert any("刷新" in t for t in texts), f"缺刷新按钮: {texts}"

    def test_versions_loaded(self, view):
        """版本列表加载：显示 v1/v2 两行"""
        tab_w = _find_version_tab(view)
        table = tab_w.findChild(QTableWidget)
        assert table.rowCount() >= 2, f"应有 ≥2 个版本，实际 {table.rowCount()}"

        # 版本号列有 1 和 2
        versions = {table.item(i, 0).text() for i in range(table.rowCount())}
        assert "1" in versions and "2" in versions, f"版本号应为 1,2，实际 {versions}"

    def test_rollback_creates_new_version(self, view, session, monkeypatch):
        """点击回滚 → 确认 → 新版本 v3 写入历史"""
        from PyQt5.QtWidgets import QMessageBox

        monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)

        tab_w = _find_version_tab(view)
        table = tab_w.findChild(QTableWidget)

        # 找到 v1 行（回滚目标）
        target_row = None
        for i in range(table.rowCount()):
            if table.item(i, 0).text() == "1":
                target_row = i
                break
        assert target_row is not None, "应有 v1 行"

        # 点击该行的回滚按钮
        rollback_btn = table.cellWidget(target_row, 4)
        assert rollback_btn is not None, "v1 行应有回滚按钮"
        rollback_btn.click()

        # 回滚后当前配置应为 v1 值（50/800）
        from edu_system.models import SemesterConfig
        from edu_system.services.semester_config import SemesterConfigService

        sem = session.query(SemesterConfig).first().semester_id
        svc = SemesterConfigService(session)
        current = svc._get_all_configs(sem)
        assert current["max_class_size"] == "50", f"回滚后应为 50，实际 {current['max_class_size']}"
        assert current["dorm_fee"] == "800", f"回滚后应为 800，实际 {current['dorm_fee']}"

        # 新版本已写入历史
        versions = svc.get_versions(sem)
        assert versions[0]["version"] == 3, f"新版本应为 v3，实际 {versions[0]['version']}"
        session.rollback()

    def test_rollback_cancelled(self, view, session, monkeypatch):
        """取消回滚：配置不变"""
        from PyQt5.QtWidgets import QMessageBox

        monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.No)
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)

        from edu_system.models import SemesterConfig
        from edu_system.services.semester_config import SemesterConfigService

        sem = session.query(SemesterConfig).first().semester_id
        before = SemesterConfigService(session)._get_all_configs(sem)

        tab_w = _find_version_tab(view)
        table = tab_w.findChild(QTableWidget)
        for i in range(table.rowCount()):
            if table.item(i, 0).text() == "1":
                rollback_btn = table.cellWidget(i, 4)
                rollback_btn.click()
                break

        after = SemesterConfigService(session)._get_all_configs(sem)
        assert before == after, "取消回滚后配置不应变化"
        session.rollback()
