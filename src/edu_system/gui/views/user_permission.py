"""
UserPermissionView — 用户权限管理视图（v3.7.0 B：权限桌面端修复）

对齐 Web users.html 功能：用户列表（账号/姓名/角色/状态）、
新增/编辑/停用/重置密码、角色列表 + 权限点展示。
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from edu_system.gui.theme import C, font
from edu_system.models import Role, User


def _btn(txt, color):
    b = QPushButton(txt)
    b.setStyleSheet(
        f"QPushButton {{ background:{color}; color:white; border:none; border-radius:3px; "
        f"padding:3px 12px; font-size:9pt; }} QPushButton:hover {{ background:#2C3E50; }}"
    )
    return b


class UserPermissionView(QWidget):
    """用户权限管理（users 页签）"""

    def __init__(self, session):
        super().__init__()
        self.session = session
        self._build_ui()
        self._reload()

    def refresh(self):
        self._reload()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        tb = QHBoxLayout()
        tb.setSpacing(4)
        tb.addWidget(QLabel("用户权限管理"))
        tb.addStretch()
        b_refresh = _btn("刷新", "#95A5A6")
        b_refresh.clicked.connect(self._reload)
        tb.addWidget(b_refresh)
        b_add = _btn("新增用户", C["accent_green"])
        b_add.clicked.connect(self._add_user)
        tb.addWidget(b_add)
        lay.addLayout(tb)

        # 用户表
        grp = QGroupBox("用户列表")
        grp.setFont(font(10, True))
        gl = QVBoxLayout(grp)
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(["ID", "账号", "姓名", "角色", "状态", "操作"])
        self._table.setFont(font(9))
        self._table.verticalHeader().hide()
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setStyleSheet(
            f"QTableWidget {{ font-size:9pt; border:1px solid {C['table_border']}; background:white; }}"
            f"QTableWidget::item {{ padding:4px; }}"
        )
        gl.addWidget(self._table)
        lay.addWidget(grp)

        # 角色列表
        role_grp = QGroupBox("角色")
        role_grp.setFont(font(10, True))
        rl = QVBoxLayout(role_grp)
        self._role_table = QTableWidget(0, 2)
        self._role_table.setHorizontalHeaderLabels(["角色", "说明"])
        self._role_table.setFont(font(9))
        self._role_table.verticalHeader().hide()
        self._role_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._role_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._role_table.horizontalHeader().setStretchLastSection(True)
        rl.addWidget(self._role_table)
        lay.addWidget(role_grp)

    def _reload(self):
        self._load_users()
        self._load_roles()

    def _load_users(self):
        users = self.session.query(User).order_by(User.id).all()
        self._table.setRowCount(len(users))
        for i, u in enumerate(users):
            role_name = u.role.name if u.role else "—"
            self._table.setItem(i, 0, QTableWidgetItem(str(u.id)))
            self._table.setItem(i, 1, QTableWidgetItem(u.username))
            self._table.setItem(i, 2, QTableWidgetItem(u.display_name or ""))
            self._table.setItem(i, 3, QTableWidgetItem(role_name))
            self._table.setItem(i, 4, QTableWidgetItem("启用" if u.is_active else "停用"))

            # 操作按钮
            w = QWidget()
            bl = QHBoxLayout(w)
            bl.setContentsMargins(2, 0, 2, 0)
            bl.setSpacing(2)
            b_edit = _btn("编辑", "#3498DB")
            b_edit.clicked.connect(lambda _, uid=u.id: self._edit_user(uid))
            bl.addWidget(b_edit)
            b_pwd = _btn("重置密码", "#F39C12")
            b_pwd.clicked.connect(lambda _, uid=u.id: self._reset_pwd(uid))
            bl.addWidget(b_pwd)
            b_toggle = _btn(
                "停用" if u.is_active else "启用", "#E74C3C" if u.is_active else "#27AE60"
            )
            b_toggle.clicked.connect(lambda _, uid=u.id: self._toggle_active(uid))
            bl.addWidget(b_toggle)
            self._table.setCellWidget(i, 5, w)

    def _load_roles(self):
        roles = self.session.query(Role).order_by(Role.id).all()
        self._role_table.setRowCount(len(roles))
        for i, r in enumerate(roles):
            self._role_table.setItem(i, 0, QTableWidgetItem(r.name))
            self._role_table.setItem(i, 1, QTableWidgetItem(r.description or ""))

    def _add_user(self):
        self._user_dialog(None)

    def _edit_user(self, uid):
        self._user_dialog(uid)

    def _user_dialog(self, uid: int | None):
        dlg = QDialog(self)
        dlg.setWindowTitle("编辑用户" if uid else "新增用户")
        dlg.setMinimumWidth(360)
        form = QFormLayout(dlg)
        form.setSpacing(8)

        user = self.session.get(User, uid) if uid else None
        ed_user = QLineEdit(user.username if user else "")
        ed_user.setFont(font(9))
        form.addRow("账号", ed_user)
        ed_name = QLineEdit(user.display_name or "" if user else "")
        ed_name.setFont(font(9))
        form.addRow("姓名", ed_name)
        ed_pwd = QLineEdit()
        ed_pwd.setFont(font(9))
        ed_pwd.setPlaceholderText("留空则不修改" if uid else "必填")
        form.addRow("密码", ed_pwd)

        role_cb = QComboBox()
        role_cb.setFont(font(9))
        for r in self.session.query(Role).order_by(Role.id).all():
            role_cb.addItem(r.name, r.id)
        if user and user.role:
            idx = role_cb.findData(user.role_id)
            role_cb.setCurrentIndex(max(idx, 0))
        form.addRow("角色", role_cb)

        btn_row = QHBoxLayout()
        b_ok = _btn("保存", C["accent_green"])
        b_cancel = _btn("取消", "#95A5A6")

        def do_save():
            username = ed_user.text().strip()
            if not username:
                QMessageBox.warning(dlg, "提示", "账号不能为空")
                return
            try:
                if uid:
                    u = self.session.get(User, uid)
                    if not u:
                        QMessageBox.warning(dlg, "提示", "用户不存在")
                        return
                    u.username = username
                    u.display_name = ed_name.text().strip()
                    u.role_id = role_cb.currentData()
                    if ed_pwd.text():
                        from edu_system.api.deps import get_password_hash

                        u.password_hash = get_password_hash(ed_pwd.text())
                    self.session.commit()
                else:
                    from edu_system.api.deps import get_password_hash

                    if not ed_pwd.text():
                        QMessageBox.warning(dlg, "提示", "新用户密码必填")
                        return
                    nu = User(
                        username=username,
                        display_name=ed_name.text().strip(),
                        role_id=role_cb.currentData(),
                        password_hash=get_password_hash(ed_pwd.text()),
                        is_active=True,
                    )
                    self.session.add(nu)
                    self.session.commit()
                dlg.accept()
                self._reload()
            except Exception as e:
                self.session.rollback()
                QMessageBox.warning(dlg, "错误", str(e))

        b_ok.clicked.connect(do_save)
        b_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(b_ok)
        btn_row.addWidget(b_cancel)
        form.addRow(btn_row)
        dlg.exec_()

    def _reset_pwd(self, uid):
        from edu_system.api.deps import get_password_hash

        user = self.session.get(User, uid)
        if not user:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"重置密码 — {user.username}")
        form = QFormLayout(dlg)
        ed = QLineEdit()
        ed.setFont(font(9))
        form.addRow("新密码", ed)
        row = QHBoxLayout()
        b_ok = _btn("确认", C["accent_green"])
        b_no = _btn("取消", "#95A5A6")
        b_no.clicked.connect(dlg.reject)

        def do():
            if not ed.text():
                QMessageBox.warning(dlg, "提示", "密码不能为空")
                return
            user.password_hash = get_password_hash(ed.text())
            self.session.commit()
            dlg.accept()
            QMessageBox.information(self, "完成", "密码已重置")

        b_ok.clicked.connect(do)
        row.addWidget(b_ok)
        row.addWidget(b_no)
        form.addRow(row)
        dlg.exec_()

    def _toggle_active(self, uid):
        user = self.session.get(User, uid)
        if not user:
            return
        user.is_active = not user.is_active
        self.session.commit()
        self._reload()
