"""
GUI 视图 — 数据维护 (PyQt5 完整版 v3)
统一风格 + 首次使用向导 + 学期初始化
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from edu_system.config import DB_PATH
from edu_system.gui.theme import C, font


def _btn(txt, color, w=None):
    b = QPushButton(txt)
    b.setStyleSheet(
        f"""QPushButton {{ background: {color}; color: white; border: none;
        border-radius: 3px; padding: 5px 12px; font-size: 9pt; }}
        QPushButton:hover {{ background: #34495E; }}"""
    )
    b.setCursor(Qt.PointingHandCursor)
    b.setMinimumHeight(28)
    if w:
        b.setFixedWidth(w)
    return b


class SettingsView(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self._build_ui()

    def refresh(self):
        self._rebuild()

    def _build_ui(self):
        self._outer = QVBoxLayout()
        self._outer.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._outer)

        # 设置最小尺寸，防止界面跳动
        self.setMinimumSize(800, 550)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._rebuild()

    def _rebuild(self):
        while self._outer.count():
            self._outer.takeAt(0).widget().deleteLater()
        w = QWidget()
        self._outer.addWidget(w)
        self._build_content(w)

    def _build_content(self, w):
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        # 工具栏（统一风格）
        tb = QHBoxLayout()
        tb.setSpacing(4)
        tb.addWidget(QLabel("数据维护"))
        tb.addStretch()
        b = QPushButton("刷新")
        b.setStyleSheet(
            "background:gray; color:white; border:none; border-radius:3px; "
            "padding:3px 12px; font-size:9pt;"
        )
        b.clicked.connect(lambda: self._rebuild())
        tb.addWidget(b)
        lay.addLayout(tb)

        # ── 首次使用？提示初始化学期 ──
        from edu_system.models import Semester

        has_semester = self.session.query(Semester).filter_by(is_active=True).first()
        if not has_semester:
            banner = QFrame()
            banner.setFrameShape(QFrame.StyledPanel)
            banner.setStyleSheet(
                "background: #FFF3CD; border: 2px solid #FFC107; border-radius: 6px; padding: 10px;"
            )
            bl = QVBoxLayout(banner)
            bl.addWidget(QLabel("系统首次使用 — 请先创建初始学期"))
            btn_row = QHBoxLayout()
            b_init = QPushButton("创建初始学期")
            b_init.setStyleSheet(
                f"background:{C['accent_green']}; color:white; border:none; "
                "border-radius:4px; padding:8px 16px; font-size:10pt; font-weight:bold;"
            )
            b_init.clicked.connect(self._first_time_setup)
            btn_row.addWidget(b_init)
            btn_row.addStretch()
            bl.addLayout(btn_row)
            lay.addWidget(banner)
            lay.addStretch()
            return

        # ── DB 信息 ──
        info = QGroupBox("数据库信息")
        info.setFont(font(10, True))
        il = QVBoxLayout(info)
        il.setSpacing(2)
        if os.path.exists(DB_PATH):
            sz = os.path.getsize(DB_PATH)
            il.addWidget(QLabel(f"路径: {DB_PATH}"))
            il.addWidget(QLabel(f"大小: {sz / 1024:.1f} KB  ({sz / 1024 / 1024:.2f} MB)"))
            mtime = Path(DB_PATH).stat().st_mtime
            il.addWidget(
                QLabel(f"修改: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')}")
            )
        else:
            il.addWidget(QLabel("数据库文件未找到"))
        lay.addWidget(info)

        # ── 全表统计 ──
        stat_grp = QGroupBox("数据统计")
        stat_grp.setFont(font(10, True))
        stat_l = QVBoxLayout(stat_grp)
        stat_l.setSpacing(2)
        inspector = inspect(self.session.bind)
        tables = sorted(inspector.get_table_names())
        t = QTableWidget(len(tables), 3)
        t.setHorizontalHeaderLabels(["表名", "记录数", "说明"])
        t.setFont(font(9))
        t.verticalHeader().hide()
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setMaximumHeight(28 + 22 * len(tables))
        t.setStyleSheet(
            """QTableWidget { font-size:9pt; border:1px solid #DDD;
            background:white; alternate-background-color:#EBF5FB; }
            QHeaderView::section { background:#D9E1F2; font-weight:bold;
            padding:3px; border:1px solid #CCC; }"""
        )
        hints = {
            "students": "学生",
            "teachers": "教师",
            "classes": "班级",
            "exams": "考试",
            "scores": "成绩",
            "class_subjects": "任课",
            "student_movements": "学籍变动",
            "semesters": "学期",
            "grades": "年级(系统)",
            "subjects": "科目(系统)",
            "settings": "设置",
        }
        for i, tbl in enumerate(tables):
            t.setItem(i, 0, QTableWidgetItem(tbl))
            cnt = self.session.execute(text(f"SELECT COUNT(*) FROM [{tbl}]")).fetchone()[0]
            item = QTableWidgetItem(str(cnt))
            item.setTextAlignment(Qt.AlignCenter)
            if cnt > 100:
                item.setForeground(QColor(C["accent_blue"]))
            t.setItem(i, 1, item)
            t.setItem(i, 2, QTableWidgetItem(hints.get(tbl, "")))
        stat_l.addWidget(t)
        lay.addWidget(stat_grp)

        # ── 快速操作 ──
        quick = QGroupBox("快速操作")
        quick.setFont(font(10, True))
        ql = QHBoxLayout(quick)
        ql.setSpacing(6)
        for txt, clr, cb in [
            ("创建新学期", C["accent_green"], self._first_time_setup),
            ("初始化默认", C["accent_purple"], self._init_defaults),
        ]:
            b = _btn(txt, clr)
            b.clicked.connect(cb)
            ql.addWidget(b)
        ql.addStretch()
        lay.addWidget(quick)

        # ── 高级操作 ──
        adv = QGroupBox("高级操作")
        adv.setFont(font(10, True))
        al = QVBoxLayout(adv)
        al.setSpacing(6)
        r1 = QHBoxLayout()
        r1.setSpacing(6)
        for txt, clr, cb in [
            ("备份数据库", C["accent_blue"], self._backup),
            ("恢复数据库", C["accent_teal"], self._restore),
            ("压缩数据库", "gray", self._vacuum),
        ]:
            b = _btn(txt, clr)
            b.clicked.connect(cb)
            r1.addWidget(b)
        r1.addStretch()
        al.addLayout(r1)
        r2 = QHBoxLayout()
        r2.setSpacing(6)
        for txt, clr, cb in [
            ("清空单表", C["accent_orange"], self._clear_table),
            ("重建业务数据", C["accent_red"], self._reset_all),
        ]:
            b = _btn(txt, clr)
            b.clicked.connect(cb)
            r2.addWidget(b)
        r2.addStretch()
        al.addLayout(r2)
        lay.addWidget(adv)
        lay.addStretch()

    # ═══════════════════════════════════
    # 首次使用向导
    # ═══════════════════════════════════

    def _first_time_setup(self):
        """创建初始学期（向导式）"""
        dlg = QDialog(self)
        dlg.setWindowTitle("创建学期")
        dlg.setMinimumWidth(380)
        fl = QFormLayout(dlg)
        fl.setSpacing(8)

        cy = datetime.now().year
        fl.addRow(QLabel("请设置当前学年度和学期:"))

        y = QSpinBox()
        y.setRange(1990, cy + 10)
        y.setValue(cy)
        y.setFont(font(10))
        y.setFixedWidth(80)
        fl.addRow("起始年:", y)
        end_label = QLabel(f"即 {cy}-{cy + 1} 学年")
        fl.addRow("", end_label)
        y.valueChanged.connect(lambda v: end_label.setText(f"即 {v}-{v + 1} 学年"))

        s_cb = QComboBox()
        s_cb.addItems(["第一学期", "第二学期"])
        s_cb.setFont(font(10))
        m = datetime.now().month
        s_cb.setCurrentIndex(0 if 1 <= m <= 8 else 1)
        fl.addRow("学期:", s_cb)

        fl.addRow(QLabel("日期可留空，后续在学期列表中编辑。"))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        fl.addRow(bb)

        if dlg.exec_():
            from edu_system.services.semester import SemesterService

            svc = SemesterService(self.session)
            sem = svc.create(y.value(), s_cb.currentText())
            self.session.commit()
            svc.set_current(sem.id)
            self.session.commit()
            m = self.window()
            if hasattr(m, "_update_semester_display"):
                m._update_semester_display()
            QMessageBox.information(
                self, "完成", f"学期已创建: {sem.display_label}\n现在可以导入学生数据了。"
            )
            self._rebuild()

    # ═══════════════════════════════════
    # 维护操作
    # ═══════════════════════════════════

    def _backup(self):
        if not os.path.exists(DB_PATH):
            QMessageBox.warning(self, "错误", "数据库不存在")
            return
        path, _ = QFileDialog.getSaveFileName(self, "备份", "school_backup.db", "*.db")
        if not path:
            return
        self.session.commit()
        shutil.copy2(DB_PATH, path)
        QMessageBox.information(self, "完成", f"已备份: {path}")

    def _restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择备份", "", "*.db")
        if not path:
            return
        if QMessageBox.question(self, "确认", "替换当前数据库？") != QMessageBox.Yes:
            return
        self.session.close()
        shutil.copy2(path, DB_PATH)
        QMessageBox.information(self, "完成", "数据库已恢复，请重启程序")
        QApplication.quit()

    def _vacuum(self):
        self.session.execute(text("VACUUM"))
        QMessageBox.information(self, "完成", "数据库已压缩")
        self._rebuild()

    def _clear_table(self):
        inspector = inspect(self.session.bind)
        safe = [t for t in inspector.get_table_names() if t not in ("grades", "subjects")]
        tbl, ok = QInputDialog.getItem(self, "清空表", "表名:", safe, 0, False)
        if not ok:
            return
        if QMessageBox.question(self, "确认", f"清空 '{tbl}'？") != QMessageBox.Yes:
            return
        self.session.execute(text(f"DELETE FROM [{tbl}]"))
        self.session.commit()
        self._rebuild()

    def _init_defaults(self):
        from edu_system.database import _ensure_defaults

        _ensure_defaults(self.session)
        self.session.commit()
        QMessageBox.information(self, "完成", "默认数据已初始化")
        self._rebuild()

    def _reset_all(self):
        if (
            QMessageBox.warning(
                self,
                "危险",
                "清空所有业务数据？\n(保留年级/科目/学期)",
                QMessageBox.Yes | QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        inspector = inspect(self.session.bind)
        for tbl in inspector.get_table_names():
            if tbl not in ("grades", "subjects", "semesters", "settings"):
                self.session.execute(text(f"DELETE FROM [{tbl}]"))
        self.session.commit()
        QMessageBox.information(self, "完成", "业务数据已清空")
        self._rebuild()
