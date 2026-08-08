"""
登录对话框 — 桌面端认证入口

遵循业界登录模式（Carbon Design / IBM Login Pattern）：
- 标题 + 输入区 + 记住选项 + 主按钮 + 错误提示的结构
- 用户名用可编辑下拉：记住的多个用户可直接选择（为多用户准备）
- 错误统一提示「用户名或密码错误」（不暴露用户名是否存在，安全规范）
- 主按钮紧随输入区；取消为次要操作独立成行
- 键盘全流程：Tab 可达，Enter 触发登录

记住选项（QSettings 持久化）：
- 记住我：保存用户名（Remember ID 语义）
- 记住密码：可选（勾选后重开预填密码）
- 自动登录：需同时记住用户名+密码，勾选后凭凭据直接登录（免弹框）
"""

from __future__ import annotations

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
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
_KEY_USERS = "known_users"  # 记住的用户名列表（多用户，逗号分隔）
_KEY_REMEMBER_PASSWORD = "remember_password"
_KEY_PASSWORD = "last_password"
_KEY_AUTOLOGIN = "auto_login"

# 记住用户名上限（避免无限累积）
_MAX_USERS = 8


class LoginDialog(QDialog):
    """登录对话框：验证用户名/密码，成功后注入当前用户

    - 记住我：QSettings 保存用户名（多用户下拉），下次预填
    - 记住密码：可选，重开预填密码
    - 自动登录：记住用户名+密码+勾选 → 凭凭据直接登录（免弹框）
    - 键盘全流程：Tab 顺序 用户名→密码→记住我→登录，Enter 触发
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self._session = session
        self._user = None
        self._settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        # 零代码 UI 配置：样式全部来自 config/ui_config.json 的 login 节
        from edu_system.config.ui_config import get_config

        self._ui_cfg = get_config()
        self.cfg = self._ui_cfg.login
        self.setWindowTitle("登录")
        self.setFixedSize(self.cfg.window_width, self.cfg.window_height)
        self.setModal(True)
        self._build_ui()
        self._load_remembered()
        self._ensure_default_admin()

    # ── UI ──
    def _build_ui(self):
        cfg = self.cfg
        layout = QVBoxLayout(self)
        margins = tuple(int(x) for x in cfg.margins.split(","))
        layout.setContentsMargins(*margins)
        layout.setSpacing(cfg.spacing)

        # 整体垂直居中：上下各留弹性空间
        layout.addStretch(1)

        # 品牌区（卡片式观感：校名 + 系统名，对齐 Web 登录框）
        if getattr(self.cfg, "brand_enabled", True):
            app_cfg = getattr(self._ui_cfg, "app", None) or {}
            school = getattr(app_cfg, "school_name", "") or "教务管理系统"
            sysname = getattr(app_cfg, "name", "") or "教务管理系统"
            title = QLabel(school)
            title.setFont(font(self.cfg.brand_title_font_size, True))
            title.setAlignment(Qt.AlignHCenter)
            title.setStyleSheet(f"color: {C['accent_blue']};")
            layout.addWidget(title)
            sub = QLabel(sysname)
            sub.setFont(font(self.cfg.brand_subtitle_font_size))
            sub.setAlignment(Qt.AlignHCenter)
            sub.setStyleSheet(f"color: {C['text_light']};")
            layout.addWidget(sub)
            layout.addSpacing(16)

        # 用户名（可编辑下拉：记住的多用户直接选择）
        layout.addWidget(self._label("用户名"))
        self.username_combo = QComboBox()
        self.username_combo.setEditable(True)
        self.username_combo.setFont(font(cfg.input_font_size))
        self.username_combo.setMinimumHeight(cfg.input_height)
        self.username_combo.lineEdit().setPlaceholderText("请输入用户名")
        self.username_combo.setStyleSheet(
            f"""
            QComboBox {{
                border: 1px solid {C["line"]}; border-radius: {cfg.input_radius}px;
                padding: 6px 10px; font-size: {cfg.input_font_size}pt;
                background: {C["white"]};
            }}
            QComboBox:focus {{ border: 1px solid {C["accent_blue"]}; }}
            """
        )
        self._combo_height_fix(self.username_combo)
        layout.addWidget(self.username_combo)

        # 密码
        layout.addSpacing(8)
        layout.addWidget(self._label("密码"))
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self._style_input(self.password_edit)
        layout.addWidget(self.password_edit)

        # 首次使用提示（占位不挤压）
        self.hint_label = QLabel("")
        self.hint_label.setFont(font(cfg.hint_font_size))
        self.hint_label.setStyleSheet(f"color: {C['accent_orange']};")
        self.hint_label.setAlignment(Qt.AlignHCenter)
        self.hint_label.setMinimumHeight(16)
        layout.addWidget(self.hint_label)

        layout.addSpacing(8)

        # 记住选项（居中一行，大间距避免挤压）
        row = QHBoxLayout()
        row.setSpacing(cfg.checkbox_spacing)
        self.remember_cb = QCheckBox("记住我")
        self.remember_cb.setFont(font(cfg.checkbox_font_size))
        self.remember_cb.setToolTip("记住用户名，下次自动填充（多用户可切换）")
        self.remember_cb.toggled.connect(self._on_remember_toggled)
        row.addWidget(self.remember_cb)
        self.remember_password_cb = QCheckBox("记住密码")
        self.remember_password_cb.setFont(font(cfg.checkbox_font_size))
        self.remember_password_cb.setToolTip("本机保存密码（自动登录需要）")
        row.addWidget(self.remember_password_cb)
        self.autologin_cb = QCheckBox("自动登录")
        self.autologin_cb.setFont(font(cfg.checkbox_font_size))
        self.autologin_cb.setToolTip("下次启动免输入直接登录（需记住用户名+密码）")
        row.addWidget(self.autologin_cb)
        # 整体居中
        wrap = QHBoxLayout()
        wrap.addStretch()
        wrap.addLayout(row)
        wrap.addStretch()
        layout.addLayout(wrap)

        layout.addSpacing(10)

        # 登录按钮（主按钮，紧随输入区）
        self.login_btn = QPushButton("登  录")
        self.login_btn.setFont(font(cfg.login_font_size, True))
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setMinimumHeight(cfg.login_height)
        self.login_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {C["accent_blue"]}; color: white;
                border: none; border-radius: {cfg.login_radius}px;
                padding: 0 0; font-size: {cfg.login_font_size}pt;
            }}
            QPushButton:hover {{ background: #2f89c9; }}
            QPushButton:pressed {{ background: #2471a3; }}
            """
        )
        self.login_btn.clicked.connect(self._on_login)
        self.login_btn.setDefault(True)
        layout.addWidget(self.login_btn)

        # 错误提示（内联，主按钮下，占位不挤压）
        self.error_label = QLabel("")
        self.error_label.setFont(font(cfg.error_font_size))
        self.error_label.setStyleSheet(f"color: {C['accent_red']};")
        self.error_label.setAlignment(Qt.AlignHCenter)
        self.error_label.setMinimumHeight(20)
        layout.addWidget(self.error_label)

        # 取消（次要，独立一行，与错误提示拉开）
        layout.addSpacing(8)
        cancel_btn = QPushButton("取 消")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFont(font(cfg.cancel_font_size))
        cancel_btn.setMinimumHeight(cfg.cancel_height)
        cancel_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent; color: {C["text_light"]};
                border: none; padding: 0 0; font-size: {cfg.cancel_font_size}pt;
            }}
            QPushButton:hover {{ color: {C["text"]}; }}
            """
        )
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        # 整体垂直居中：底部弹性空间（与顶部对称）
        layout.addStretch(1)

        # Enter 触发登录
        self.password_edit.returnPressed.connect(self._on_login)
        self.username_combo.lineEdit().returnPressed.connect(self.password_edit.setFocus)

    def _combo_height_fix(self, combo: QComboBox):
        """下拉框行高不被挤压：视口与弹出列表项高一致"""
        combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        combo.view().setMinimumWidth(combo.width())

    def _label(self, text: str) -> QLabel:
        cfg = self.cfg
        lbl = QLabel(text)
        lbl.setFont(font(cfg.label_font_size, cfg.label_bold))
        lbl.setStyleSheet(f"color: {C['text']};")
        lbl.setAlignment(Qt.Alignment(Qt.AlignHCenter | Qt.AlignVCenter))
        lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        return lbl

    def _style_input(self, edit: QLineEdit):
        cfg = self.cfg
        edit.setFont(font(cfg.input_font_size))
        edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        edit.setMinimumHeight(cfg.input_height)
        edit.setStyleSheet(
            f"""
            QLineEdit {{
                border: 1px solid {C["line"]}; border-radius: {cfg.input_radius}px;
                padding: 6px 12px; font-size: {cfg.input_font_size}pt;
                background: {C["white"]};
            }}
            QLineEdit:focus {{ border: 1px solid {C["accent_blue"]}; }}
            """
        )

    # ── 用户名（多用户） ──
    @property
    def username_text(self) -> str:
        return self.username_combo.currentText().strip()

    @username_text.setter
    def username_text(self, value: str):
        self.username_combo.setEditText(value)

    def _load_users(self) -> list[str]:
        """读取记住的用户名列表"""
        raw = self._settings.value(_KEY_USERS, "", type=str)
        return [u for u in raw.split(",") if u]

    def _save_user(self, username: str):
        """登录成功后把用户名加入记住列表（去重、上限、置顶）"""
        users = self._load_users()
        users = [u for u in users if u != username]
        users.insert(0, username)
        users = users[:_MAX_USERS]
        self._settings.setValue(_KEY_USERS, ",".join(users))

    # ── 逻辑 ──
    def _load_remembered(self):
        """加载记住的用户名/密码与自动登录标记"""
        remembered = self._settings.value(_KEY_REMEMBER, False, type=bool)
        username = self._settings.value(_KEY_USERNAME, "", type=str)
        remember_pwd = self._settings.value(_KEY_REMEMBER_PASSWORD, False, type=bool)
        password = self._settings.value(_KEY_PASSWORD, "", type=str)
        auto = self._settings.value(_KEY_AUTOLOGIN, False, type=bool)

        # 填充多用户下拉
        for u in self._load_users():
            self.username_combo.addItem(u)
        if remembered and username:
            self.username_combo.setEditText(username)

        self.remember_cb.setChecked(remembered)
        self.remember_password_cb.setChecked(remember_pwd)
        if remember_pwd and password:
            self.password_edit.setText(password)
        if auto:
            self.autologin_cb.setChecked(True)

        # 焦点：有密码直接登录按钮，否则密码框
        if remember_pwd and password:
            self.login_btn.setFocus()
        else:
            self.password_edit.setFocus()

    def _on_remember_toggled(self, checked: bool):
        """记住我切换：勾选时立即保存用户名"""
        if checked:
            self._settings.setValue(_KEY_USERNAME, self.username_text)

    def _save_remembered(self, username: str, password: str):
        """登录成功后保存记住状态"""
        if self.remember_cb.isChecked():
            self._settings.setValue(_KEY_REMEMBER, True)
            self._settings.setValue(_KEY_USERNAME, username)
            self._save_user(username)
        else:
            self._settings.setValue(_KEY_REMEMBER, False)
            self._settings.setValue(_KEY_USERNAME, "")
        if self.remember_password_cb.isChecked():
            self._settings.setValue(_KEY_REMEMBER_PASSWORD, True)
            self._settings.setValue(_KEY_PASSWORD, password)
        else:
            self._settings.setValue(_KEY_REMEMBER_PASSWORD, False)
            self._settings.setValue(_KEY_PASSWORD, "")
        self._settings.setValue(_KEY_AUTOLOGIN, self.autologin_cb.isChecked())

    def has_auto_login(self) -> bool:
        """是否有自动登录条件（记住用户名+记住密码+勾选自动登录）"""
        return (
            self._settings.value(_KEY_AUTOLOGIN, False, type=bool)
            and bool(self._settings.value(_KEY_USERNAME, "", type=str))
            and bool(self._settings.value(_KEY_PASSWORD, "", type=str))
        )

    def try_auto_login(self) -> bool:
        """自动登录：凭记住的凭据直接登录（免弹框）

        返回 True 表示自动登录成功（用户已注入），False 需手动登录。
        """
        if not self.has_auto_login():
            return False
        username = self._settings.value(_KEY_USERNAME, "", type=str)
        password = self._settings.value(_KEY_PASSWORD, "", type=str)
        self.username_combo.setEditText(username)
        self.password_edit.setText(password)
        self._on_login()
        return self._user is not None

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

        username = self.username_text
        password = self.password_edit.text()

        if not username or not password:
            self._show_error("请输入用户名和密码")
            return

        user = self._session.query(User).filter_by(username=username).first()
        if not user:
            self._show_error("用户名或密码错误")
            return
        if not user.is_active:
            self._show_error("账号已停用，请联系管理员")
            return
        if not verify_password(password, user.password_hash):
            self._show_error("用户名或密码错误")
            return

        # 认证成功：注入当前用户
        set_current_user(user)
        self._user = user
        self._save_remembered(username, password)
        self.accept()

    def _show_error(self, msg: str):
        self.error_label.setText(msg)
        self.password_edit.clear()
        self.password_edit.setFocus()

    # ── 结果 ──
    def get_user(self):
        """登录成功的用户对象；未登录返回 None"""
        return self._user
