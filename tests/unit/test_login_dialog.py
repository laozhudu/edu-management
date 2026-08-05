"""LoginDialog 单元测试 — 认证流程（安全关键路径）"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PyQt5.QtWidgets import QApplication

from edu_system.core.auth import get_password_hash, verify_password


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
    role = Role(
        name="admin",
        description="超级管理员",
        permissions=",".join([p.value for p in Permission]),
    )
    s.add(role)
    s.flush()
    admin = User(username="admin", display_name="系统管理员", role=role, is_active=True)
    s.add(admin)
    s.commit()
    yield s
    s.close()


def _make_dialog(session, username: str, password: str):
    from edu_system.gui.dialogs import LoginDialog

    dlg = LoginDialog(session)
    dlg.username_combo.setEditText(username)
    dlg.password_edit.setText(password)
    return dlg


def test_first_login_uses_default_password(qapp, session):
    """首次登录：admin 无密码 → 自动初始化默认密码 admin123，可登录"""
    from edu_system.gui.dialogs import DEFAULT_PASSWORD

    dlg = _make_dialog(session, "admin", DEFAULT_PASSWORD)
    dlg._on_login()
    assert dlg.result() == dlg.Accepted
    assert dlg.get_user() is not None
    assert dlg.get_user().username == "admin"
    # 密码已哈希存储（默认密码）
    from edu_system.models import User

    admin = session.query(User).filter_by(username="admin").first()
    assert admin.password_hash
    assert verify_password(DEFAULT_PASSWORD, admin.password_hash)


def test_first_login_shows_default_hint(qapp, session):
    """首次启动：登录框显示默认账号提示并预填"""
    from edu_system.gui.dialogs import DEFAULT_ADMIN, DEFAULT_PASSWORD, LoginDialog

    dlg = LoginDialog(session)
    assert dlg.username_combo.currentText() == DEFAULT_ADMIN
    assert dlg.password_edit.text() == DEFAULT_PASSWORD
    assert DEFAULT_ADMIN in dlg.hint_label.text()
    assert DEFAULT_PASSWORD in dlg.hint_label.text()


def test_wrong_password_rejected(qapp, session):
    """已设密码后，错误密码被拒绝"""
    from edu_system.models import User

    admin = session.query(User).filter_by(username="admin").first()
    admin.password_hash = get_password_hash("correct")
    session.commit()

    dlg = _make_dialog(session, "admin", "wrong")
    dlg._on_login()
    assert dlg.result() != dlg.Accepted
    assert "密码错误" in dlg.error_label.text()


def test_correct_password_accepted(qapp, session):
    """已设密码后，正确密码通过"""
    from edu_system.models import User

    admin = session.query(User).filter_by(username="admin").first()
    admin.password_hash = get_password_hash("correct")
    session.commit()

    dlg = _make_dialog(session, "admin", "correct")
    dlg._on_login()
    assert dlg.result() == dlg.Accepted
    assert dlg.get_user().username == "admin"


def test_unknown_user_rejected(qapp, session):
    """不存在的用户被拒绝"""
    dlg = _make_dialog(session, "nobody", "x")
    dlg._on_login()
    assert dlg.result() != dlg.Accepted
    assert "用户名或密码错误" in dlg.error_label.text()


def test_empty_input_rejected(qapp, session):
    """空用户名/密码被拒绝"""
    dlg = _make_dialog(session, "", "")
    dlg._on_login()
    assert dlg.result() != dlg.Accepted
    assert "请输入用户名和密码" in dlg.error_label.text()
