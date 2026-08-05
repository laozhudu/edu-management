"""
登录对话框 — 桌面端认证入口

流程：主窗口显示后弹出 → 输入用户名/密码 → verify_password 校验
→ set_current_user 注入会话 → 进入主界面

- 首次启动：admin 用户无密码时，用默认密码 admin123 初始化（内联提示）
- 失败：错误提示 + 重试
"""

from __future__ import annotations

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from edu_system.core.auth import verify_password
from edu_system.core.permissions import set_current_user
from edu_system.gui.theme import C, font

# 默认管理员账号（首次启动自动初始化）
DEFAULT_ADMIN = "admin"
DEFAULT_PASSWORD = "admin123"

# QSettings 存储键（记住我/自动登录）
_SETTINGS_ORG = "edu_system"
_SETTINGS_APP = "login"
_KEY_REMEMBER = "remember_username"
_KEY_USERNAME = "last_username"
_KEY_AUTOLOGIN = "auto_login"


class LoginDialog(QDialog):
    """登录对话框：验证用户名/密码，成功后注入当前用户

    - 记住我：QSettings 保存用户名，下次预填
    - 自动登录：记住凭据后跳过对话框直接登录
    - 键盘全流程：Tab 顺序 用户名→密码→记住我→登录，Enter 触发
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self._session = session
        self._user = None
        self._settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        self.setWindowTitle("登录 — 教务管理系统")
        self.setFixedSize(420, 380)
        self.setModal(True)
        self._build_ui()
        self._load_remembered()
        self._ensure_default_admin()

    # ── UI ──
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 26, 32, 22)
        layout.setSpacing(10)

        # 用户名
        layout.addWidget(self._label("用户名"))
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("请输入用户名")
        self.username_edit.setText(DEFAULT_ADMIN)
        self._style_input(self.username_edit)
        layout.addWidget(self.username_edit)

        # 密码（与上方用户名框拉开间距，"密码"标签上方留白更足）
        layout.addSpacing(22)
        layout.addWidget(self._label("密码"))
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self._style_input(self.password_edit)
        layout.addWidget(self.password_edit)

        # 默认账号提示（首次使用）
        self.hint_label = QLabel("")
        self.hint_label.setFont(font(9))
        self.hint_label.setStyleSheet(f"color: {C['accent_orange']};")
        self.hint_label.setAlignment(Qt.AlignHCenter)
        self.hint_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(self.hint_label)

        layout.addSpacing(8)

        # 登录按钮（占满整行，醒目，行高充足）
        login_btn = QPushButton("登  录")
        login_btn.setFont(font(11, True))
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        login_btn.setMinimumHeight(42)
        login_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {C["accent_blue"]}; color: white;
                border: none; border-radius: 6px;
                padding: 0 0; font-size: 11pt;
            }}
            QPushButton:hover {{ background: #2f89c9; }}
            QPushButton:pressed {{ background: #2471a3; }}
            """
        )
        login_btn.clicked.connect(self._on_login)
        login_btn.setDefault(True)
        layout.addWidget(login_btn)

        # 取消按钮（次要，行高充足不挤压）
        cancel_btn = QPushButton("取 消")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFont(font(10))
        cancel_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        cancel_btn.setMinimumHeight(34)
        cancel_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent; color: {C["text_light"]};
                border: none; padding: 0 0; font-size: 10pt;
            }}
            QPushButton:hover {{ color: {C["text"]}; }}
            """
        )
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        # 记住我/自动登录（QSettings 持久化）
        row = QHBoxLayout()
        row.setSpacing(6)
        self.remember_cb = QCheckBox("记住用户名")
        self.remember_cb.setFont(font(9))
        self.remember_cb.toggled.connect(self._on_remember_toggled)
        row.addWidget(self.remember_cb)
        self.autologin_cb = QCheckBox("自动登录")
        self.autologin_cb.setFont(font(9))
        row.addWidget(self.autologin_cb)
        row.addStretch()
        layout.addLayout(row)

        # 错误提示（占位，不挤占布局）
        self.error_label = QLabel("")
        self.error_label.setFont(font(9))
        self.error_label.setStyleSheet(f"color: {C['accent_red']};")
        self.error_label.setAlignment(Qt.AlignHCenter)
        layout.addWidget(self.error_label)

        # Enter 键触发登录
        self.password_edit.returnPressed.connect(self._on_login)
        self.username_edit.returnPressed.connect(self.password_edit.setFocus)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(font(10, True))
        lbl.setStyleSheet(f"color: {C['text']};")
        lbl.setAlignment(Qt.Alignment(Qt.AlignHCenter | Qt.AlignVCenter))  # 标签居中
        lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        return lbl

    def _style_input(self, edit: QLineEdit):
        edit.setFont(font(10))
        edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        edit.setMinimumHeight(44)
        edit.setAlignment(Qt.Alignment(Qt.AlignHCenter | Qt.AlignVCenter))  # 输入文字居中
        # 注意：QSS padding 只设左右，上下由 minimumHeight 撑开，
        # 避免 padding+font 高度超过控件高度导致文字被裁剪
        edit.setStyleSheet(
            f"""
            QLineEdit {{
                border: 1px solid {C["line"]}; border-radius: 5px;
                padding: 0 12px; font-size: 10pt; background: {C["white"]};
            }}
            QLineEdit:focus {{ border: 1px solid {C["accent_blue"]}; }}
            """
        )

    # ── 逻辑 ──
    def _load_remembered(self):
        """加载记住的用户名与自动登录标记"""
        remembered = self._settings.value(_KEY_REMEMBER, False, type=bool)
        username = self._settings.value(_KEY_USERNAME, "", type=str)
        auto = self._settings.value(_KEY_AUTOLOGIN, False, type=bool)
        self.remember_cb.setChecked(remembered)
        if remembered and username:
            self.username_edit.setText(username)
            self.password_edit.setFocus()
        if auto:
            self.autologin_cb.setChecked(True)

    def _on_remember_toggled(self, checked: bool):
        """记住我切换：勾选时立即保存用户名"""
        if checked:
            self._settings.setValue(_KEY_USERNAME, self.username_edit.text().strip())

    def _save_remembered(self, username: str):
        """登录成功后保存记住状态"""
        if self.remember_cb.isChecked():
            self._settings.setValue(_KEY_REMEMBER, True)
            self._settings.setValue(_KEY_USERNAME, username)
        else:
            self._settings.setValue(_KEY_REMEMBER, False)
            self._settings.setValue(_KEY_USERNAME, "")
        self._settings.setValue(_KEY_AUTOLOGIN, self.autologin_cb.isChecked())

    def has_auto_login(self) -> bool:
        """是否有自动登录偏好（记住用户名 + 勾选自动登录）

        密码不明文存储（安全），自动登录 = 预填用户名 + 聚焦密码框，
        用户 Enter 即登录（键盘全流程可达）。
        """
        return (
            self._settings.value(_KEY_AUTOLOGIN, False, type=bool)
            and bool(self._settings.value(_KEY_USERNAME, "", type=str))
        )

    def _ensure_default_admin(self):
        """确保 admin 有密码：无密码时用默认密码初始化（首次启动）"""
        from edu_system.models import User

        user = self._session.query(User).filter_by(username=DEFAULT_ADMIN).first()
        if user and not user.password_hash:
            from edu_system.core.auth import get_password_hash

            user.password_hash = get_password_hash(DEFAULT_PASSWORD)
            self._session.commit()
            self.hint_label.setText(
                f"首次启动已初始化默认账号：{DEFAULT_ADMIN} / {DEFAULT_PASSWORD}"
            )
            self.password_edit.setText(DEFAULT_PASSWORD)
            self.password_edit.setFocus()

    def _on_login(self):
        from edu_system.models import User

        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            self._show_error("请输入用户名和密码")
            return

        user = self._session.query(User).filter_by(username=username).first()
        if not user:
            self._show_error("用户不存在")
            return
        if not user.is_active:
            self._show_error("账号已停用，请联系管理员")
            return
        if not verify_password(password, user.password_hash):
            self._show_error("密码错误，请重试")
            return

        # 认证成功：注入当前用户
        set_current_user(user)
        self._user = user
        self._save_remembered(username)
        self.accept()

    def _show_error(self, msg: str):
        self.error_label.setText(msg)
        self.password_edit.clear()
        self.password_edit.setFocus()

    # ── 结果 ──
    def get_user(self):
        """登录成功的用户对象；未登录返回 None"""
        return self._user
