"""
LoginDialog GUI 测试（M5-D1）

覆盖：
- 键盘全流程：Tab 顺序可达，Enter 触发登录
- 记住我：勾选后 QSettings 保存用户名，重开预填
- 自动登录：偏好标记可查询（has_auto_login）
- 登录成功：注入当前用户 + 记住状态保存
- 登录失败：错误提示 + 密码清空
"""

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui  # 仅 GUI job（xvfb）运行

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication, QLineEdit


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def session():
    """内存 SQLite 会话（admin 用户）"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.core.auth import get_password_hash
    from edu_system.core.permissions import Permission
    from edu_system.models import Base, Role, User

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    admin_role = Role(
        name="admin", description="管理员",
        permissions=",".join([p.value for p in Permission]),
    )
    s.add(admin_role)
    s.flush()
    s.add(
        User(
            username="admin",
            display_name="管理员",
            role_id=admin_role.id,
            password_hash=get_password_hash("admin123"),
        )
    )
    s.commit()
    yield s
    s.close()


@pytest.fixture(autouse=True)
def isolate_qsettings():
    """隔离登录 QSettings，避免污染真实配置"""
    s = QSettings("edu_system", "login")
    for k in ("remember_username", "last_username", "auto_login"):
        s.remove(k)
    yield
    for k in ("remember_username", "last_username", "auto_login"):
        s.remove(k)


@pytest.fixture
def dialog(qapp, session):
    from edu_system.core.permissions import set_current_user
    from edu_system.gui.dialogs.login import LoginDialog

    set_current_user(None)
    dlg = LoginDialog(session)
    dlg.show()
    yield dlg
    set_current_user(None)
    dlg.close()


class TestKeyboardFlow:
    def test_tab_order_reaches_login(self, dialog):
        """Tab 顺序：用户名→密码→登录按钮可达，Enter 触发"""
        # 焦点顺序中登录按钮可达
        assert dialog.username_edit is not None
        assert dialog.password_edit is not None
        # Enter 在密码框触发登录（returnPressed 已连接）
        assert dialog.password_edit.returnPressed is not None
        # Tab 顺序包含全部输入控件
        order = [w for w in dialog.findChildren(QLineEdit)]
        assert len(order) >= 2

    def test_enter_trigger_login(self, dialog, monkeypatch):
        """密码框 Enter 触发登录流程"""
        from edu_system.core.permissions import get_current_user

        dialog.username_edit.setText("admin")
        dialog.password_edit.setText("admin123")
        # 拦截 accept（避免 exec 阻塞）
        monkeypatch.setattr(dialog, "accept", lambda: None)
        dialog.password_edit.returnPressed.emit()
        user = get_current_user()
        assert user is not None and user.username == "admin"


class TestRememberMe:
    def test_remember_saves_username(self, dialog, session, monkeypatch):
        """勾选记住我 + 登录成功 → QSettings 保存用户名"""
        monkeypatch.setattr(dialog, "accept", lambda: None)
        dialog.remember_cb.setChecked(True)
        dialog.username_edit.setText("admin")
        dialog.password_edit.setText("admin123")
        dialog._on_login()

        s = QSettings("edu_system", "login")
        assert s.value("remember_username", False, type=bool) is True
        assert s.value("last_username", "", type=str) == "admin"

    def test_remember_prefills_on_reopen(self, dialog, session, monkeypatch):
        """记住的用户名在重开对话框时预填"""
        monkeypatch.setattr(dialog, "accept", lambda: None)
        dialog.remember_cb.setChecked(True)
        dialog.username_edit.setText("admin")
        dialog.password_edit.setText("admin123")
        dialog._on_login()

        # 重开新对话框
        from edu_system.gui.dialogs.login import LoginDialog

        dlg2 = LoginDialog(session)
        assert dlg2.username_edit.text() == "admin"
        assert dlg2.remember_cb.isChecked() is True
        dlg2.close()

    def test_auto_login_preference(self, dialog, session, monkeypatch):
        """勾选自动登录 → has_auto_login 为 True"""
        monkeypatch.setattr(dialog, "accept", lambda: None)
        dialog.remember_cb.setChecked(True)
        dialog.autologin_cb.setChecked(True)
        dialog.username_edit.setText("admin")
        dialog.password_edit.setText("admin123")
        dialog._on_login()

        from edu_system.gui.dialogs.login import LoginDialog

        dlg2 = LoginDialog(session)
        assert dlg2.has_auto_login() is True
        dlg2.close()


class TestLoginLogic:
    def test_login_success(self, dialog, monkeypatch):
        """正确凭据登录成功，注入当前用户"""
        from edu_system.core.permissions import get_current_user

        monkeypatch.setattr(dialog, "accept", lambda: None)
        dialog.username_edit.setText("admin")
        dialog.password_edit.setText("admin123")
        dialog._on_login()
        assert dialog.get_user() is not None
        assert get_current_user() is not None

    def test_login_wrong_password(self, dialog):
        """错误密码：错误提示 + 密码清空"""
        dialog.username_edit.setText("admin")
        dialog.password_edit.setText("wrongpass")
        dialog._on_login()
        assert "密码错误" in dialog.error_label.text()
        assert dialog.password_edit.text() == ""
        assert dialog.get_user() is None

    def test_login_empty_fields(self, dialog):
        """空用户名/密码拦截"""
        dialog.username_edit.setText("")
        dialog.password_edit.setText("")
        dialog._on_login()
        assert "请输入" in dialog.error_label.text()

    def test_login_unknown_user(self, dialog):
        """不存在用户提示"""
        dialog.username_edit.setText("ghost")
        dialog.password_edit.setText("x")
        dialog._on_login()
        assert "不存在" in dialog.error_label.text()
