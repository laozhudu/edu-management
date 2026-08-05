"""
数据锁定工具栏 GUI 测试（M5-C3）

覆盖：
- 锁定工具栏存在（实体类型/级别/理由/加锁/解锁/锁状态）
- 权限控制：无 DATA_UNLOCK 权限时锁定/解锁按钮禁用
- 理由必填：空理由加锁被拦截（警告）
- 批量锁定：逗号分隔多 ID 全部加锁
- 加锁/解锁/锁状态联动（DataLock 表落库）
"""

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui  # 仅 GUI job（xvfb）运行

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PyQt5.QtWidgets import QApplication, QComboBox, QLineEdit, QMessageBox, QPushButton


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def session():
    """内存 SQLite 会话（含 semester + DataLock 表）"""
    from datetime import date

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.models import (
        AcademicYear,
        Base,
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
        academic_year_id=ay.id, year_start=2024, semester="1",
        label="2024-2025 第1学期", sort_order=1, is_active=True,
        status=SemesterStatus.active, start_date=date(2024, 9, 1),
        end_date=date(2025, 1, 15),
    )
    s.add(sem)
    s.commit()
    yield s
    s.close()


@pytest.fixture
def toolbar(qapp, session):
    from edu_system.gui.views.base import LockToolbar

    tb = LockToolbar(session)
    tb.show()
    yield tb
    tb.close()


def _fill(toolbar, etype="student", ids="1", level="hard", reason="测试锁定"):
    toolbar.type_cb.setCurrentText(etype)
    toolbar.id_edit.setText(ids)
    toolbar.level_cb.setCurrentText(level)
    toolbar.reason_edit.setText(reason)


class TestLockToolbar:
    def test_toolbar_components_exist(self, toolbar):
        """工具栏含实体类型/级别/理由/加锁/解锁/锁状态"""
        combos = toolbar.findChildren(QComboBox)
        texts = [c.currentText() for c in combos]
        assert any("student" in t for t in texts), f"应有实体类型选择: {texts}"
        assert any(t in {"hard", "soft", "semester"} for t in texts), f"应有锁级别: {texts}"

        edits = toolbar.findChildren(QLineEdit)
        assert len(edits) >= 2, "应有 ID 输入 + 理由输入"

        buttons = toolbar.findChildren(QPushButton)
        btns = [b.text() for b in buttons]
        assert "加锁" in btns and "解锁" in btns and "锁状态" in btns, f"缺操作按钮: {btns}"

    def test_permission_control(self, toolbar, monkeypatch):
        """无 DATA_UNLOCK 权限：锁定/解锁按钮禁用（权限控制按钮）"""
        from edu_system.core.permissions import set_current_user

        set_current_user(None)  # 未登录 → 无权限
        # 重新应用权限
        toolbar._apply_permission()
        assert not toolbar.lock_btn.isEnabled(), "无权限时加锁按钮应禁用"
        assert not toolbar.unlock_btn.isEnabled(), "无权限时解锁按钮应禁用"
        # 锁状态查询无需权限，仍可用
        assert toolbar.status_btn.isEnabled()
        set_current_user(None)

    def test_permission_granted(self, toolbar, session, monkeypatch):
        """有 DATA_UNLOCK 权限：加锁按钮可用"""
        from edu_system.core.permissions import Permission, set_current_user
        from edu_system.models import Role, User

        admin_role = Role(
            name="admin", description="管理员",
            permissions=",".join([p.value for p in Permission]),
        )
        session.add(admin_role)
        session.flush()
        admin = User(username="admin", display_name="管理员", role_id=admin_role.id)
        session.add(admin)
        session.commit()

        set_current_user(admin)
        toolbar._apply_permission()
        assert toolbar.lock_btn.isEnabled(), "有权限时加锁按钮应可用"
        set_current_user(None)

    def test_reason_required(self, toolbar, monkeypatch):
        """理由必填：空理由加锁被拦截"""
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)
        _fill(toolbar, reason="")
        assert toolbar._get_reason() is None, "空理由应返回 None（拦截）"

    def test_batch_lock_and_status(self, toolbar, session, monkeypatch):
        """批量锁定多 ID + 锁状态查询（DataLock 落库）"""
        from edu_system.core.permissions import Permission, set_current_user
        from edu_system.models import DataLock, Role, User
        from edu_system.services.locks import LockLevel

        admin_role = Role(
            name="admin", description="管理员",
            permissions=",".join([p.value for p in Permission]),
        )
        session.add(admin_role)
        session.flush()
        admin = User(username="admin", display_name="管理员", role_id=admin_role.id)
        session.add(admin)
        session.commit()
        set_current_user(admin)
        toolbar._apply_permission()

        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)

        # 批量锁定 student 1,2,3
        _fill(toolbar, etype="student", ids="1,2,3", level="hard", reason="批量测试")
        toolbar.lock_btn.click()

        locks = (
            session.query(DataLock)
            .filter(DataLock.entity_type == "student")
            .order_by(DataLock.entity_id)
            .all()
        )
        assert len(locks) == 3, f"应锁定 3 个学生，实际 {len(locks)}"
        assert [x.entity_id for x in locks] == [1, 2, 3]
        assert all(x.lock_level == LockLevel.HARD.value for x in locks)
        assert all(x.reason == "批量测试" for x in locks)

        # 解锁后清空
        _fill(toolbar, etype="student", ids="1,2,3", level="hard", reason="批量测试")
        toolbar.unlock_btn.click()
        remaining = (
            session.query(DataLock).filter(DataLock.entity_type == "student").count()
        )
        assert remaining == 0, f"解锁后应无锁，实际 {remaining}"

        session.rollback()
        set_current_user(None)
