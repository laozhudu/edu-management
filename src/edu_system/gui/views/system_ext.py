"""
SystemExtView — 系统扩展视图（M2：公告/登录日志/在线用户）
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from edu_system.gui.theme import C, font
from edu_system.models import LoginLog, Notice, OnlineUser


def _btn(txt, color):
    from edu_system.gui.components import btn

    return btn(txt, color)

class SystemExtView(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self._build_ui()
        self.refresh()

    def refresh(self):
        self._load_notices()
        self._load_login_logs()
        self._load_online()

    def _build_ui(self):
        from PyQt5.QtWidgets import QTabWidget

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(6)
        self._tabs = QTabWidget()
        self._tabs.setFont(font(9))
        self._tabs.addTab(self._build_notice_tab(), "通知公告")
        self._tabs.addTab(self._build_loginlog_tab(), "登录日志")
        self._tabs.addTab(self._build_online_tab(), "在线用户")
        lay.addWidget(self._tabs)

    # ── 公告 ──
    def _build_notice_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(4, 4, 4, 4)
        tb = QHBoxLayout()
        tb.addWidget(QLabel("通知公告"))
        tb.addStretch()
        b_add = _btn("发布公告", C["accent_green"])
        b_add.clicked.connect(self._add_notice)
        tb.addWidget(b_add)
        b_ref = _btn("刷新", "#95A5A6")
        b_ref.clicked.connect(self._load_notices)
        tb.addWidget(b_ref)
        lay.addLayout(tb)
        self._notice_table = QTableWidget(0, 5)
        self._notice_table.setHorizontalHeaderLabels(["ID", "标题", "类型", "发布人", "阅读数"])
        self._notice_table.setFont(font(9))
        self._notice_table.verticalHeader().hide()
        self._notice_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._notice_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._notice_table.horizontalHeader().setStretchLastSection(True)
        self._notice_table.setStyleSheet(
            f"QTableWidget {{ font-size:9pt; border:1px solid {C['table_border']}; background:white; }}"
        )
        lay.addWidget(self._notice_table)
        return tab

    def _load_notices(self):
        self._notice_table.setRowCount(0)
        notices = self.session.query(Notice).order_by(Notice.id.desc()).all()
        self._notice_table.setRowCount(len(notices))
        for i, n in enumerate(notices):
            self._notice_table.setItem(i, 0, QTableWidgetItem(str(n.id)))
            self._notice_table.setItem(i, 1, QTableWidgetItem(n.title))
            self._notice_table.setItem(
                i, 2, QTableWidgetItem("公告" if n.notice_type == "announce" else "通知")
            )
            self._notice_table.setItem(i, 3, QTableWidgetItem(n.publisher or ""))
            self._notice_table.setItem(i, 4, QTableWidgetItem(str(n.read_count or 0)))

    def _add_notice(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("发布公告")
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg)
        ed_title = QLineEdit()
        ed_title.setPlaceholderText("标题")
        ed_title.setFont(font(9))
        lay.addWidget(ed_title)
        ed_content = QTextEdit()
        ed_content.setPlaceholderText("内容")
        ed_content.setFont(font(9))
        ed_content.setFixedHeight(120)
        lay.addWidget(ed_content)
        row = QHBoxLayout()
        b_ok = _btn("发布", C["accent_green"])

        def do():
            if not ed_title.text().strip():
                QMessageBox.warning(dlg, "提示", "标题不能为空")
                return
            self.session.add(
                Notice(
                    title=ed_title.text().strip(),
                    content=ed_content.toPlainText(),
                    notice_type="notice",
                    publisher="admin",
                )
            )
            self.session.commit()
            dlg.accept()
            self._load_notices()

        b_ok.clicked.connect(do)
        b_no = _btn("取消", "#95A5A6")
        b_no.clicked.connect(dlg.reject)
        row.addWidget(b_ok)
        row.addWidget(b_no)
        lay.addLayout(row)
        dlg.exec_()

    # ── 登录日志 ──
    def _build_loginlog_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(4, 4, 4, 4)
        tb = QHBoxLayout()
        tb.addWidget(QLabel("登录日志"))
        tb.addStretch()
        b_ref = _btn("刷新", "#95A5A6")
        b_ref.clicked.connect(self._load_login_logs)
        tb.addWidget(b_ref)
        lay.addLayout(tb)
        self._loginlog_table = QTableWidget(0, 5)
        self._loginlog_table.setHorizontalHeaderLabels(["时间", "账号", "状态", "IP", "说明"])
        self._loginlog_table.setFont(font(9))
        self._loginlog_table.verticalHeader().hide()
        self._loginlog_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._loginlog_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._loginlog_table.horizontalHeader().setStretchLastSection(True)
        self._loginlog_table.setStyleSheet(
            f"QTableWidget {{ font-size:9pt; border:1px solid {C['table_border']}; background:white; }}"
        )
        lay.addWidget(self._loginlog_table)
        return tab

    def _load_login_logs(self):
        self._loginlog_table.setRowCount(0)
        logs = self.session.query(LoginLog).order_by(LoginLog.id.desc()).limit(200).all()
        self._loginlog_table.setRowCount(len(logs))
        for i, lg in enumerate(logs):
            self._loginlog_table.setItem(
                i, 0, QTableWidgetItem(str(lg.created_at)[:19] if lg.created_at else "")
            )
            self._loginlog_table.setItem(i, 1, QTableWidgetItem(lg.username or ""))
            self._loginlog_table.setItem(
                i, 2, QTableWidgetItem("成功" if lg.status == "0" else "失败")
            )
            self._loginlog_table.setItem(i, 3, QTableWidgetItem(lg.ip or ""))
            self._loginlog_table.setItem(i, 4, QTableWidgetItem(lg.msg or ""))

    # ── 在线用户 ──
    def _build_online_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(4, 4, 4, 4)
        tb = QHBoxLayout()
        tb.addWidget(QLabel("在线用户"))
        tb.addStretch()
        b_ref = _btn("刷新", "#95A5A6")
        b_ref.clicked.connect(self._load_online)
        tb.addWidget(b_ref)
        lay.addLayout(tb)
        self._online_table = QTableWidget(0, 4)
        self._online_table.setHorizontalHeaderLabels(["账号", "姓名", "IP", "登录时间"])
        self._online_table.setFont(font(9))
        self._online_table.verticalHeader().hide()
        self._online_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._online_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._online_table.setStyleSheet(
            f"QTableWidget {{ font-size:9pt; border:1px solid {C['table_border']}; background:white; }}"
        )
        lay.addWidget(self._online_table)
        return tab

    def _load_online(self):
        self._online_table.setRowCount(0)
        users = self.session.query(OnlineUser).order_by(OnlineUser.login_at.desc()).all()
        self._online_table.setRowCount(len(users))
        for i, u in enumerate(users):
            self._online_table.setItem(i, 0, QTableWidgetItem(u.username or ""))
            self._online_table.setItem(i, 1, QTableWidgetItem(u.display_name or ""))
            self._online_table.setItem(i, 2, QTableWidgetItem(u.ip or ""))
            self._online_table.setItem(
                i, 3, QTableWidgetItem(str(u.login_at)[:19] if u.login_at else "")
            )
