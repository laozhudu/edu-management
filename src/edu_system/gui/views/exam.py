"""
GUI 视图 — 考试管理（PyQt5 统一风格）
Tab 设计：考试列表 / 新建考试
"""

from datetime import datetime

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from edu_system.gui.theme import C, font
from edu_system.models import Exam, Grade, Semester


def _btn(txt, color, w=None):
    b = QPushButton(txt)
    b.setStyleSheet(
        f"""QPushButton {{ background: {color}; color: white; border: none;
        border-radius: 3px; padding: 4px 10px; font-size: 9pt; }}
        QPushButton:hover {{ background: #34495E; }}"""
    )
    b.setCursor(Qt.PointingHandCursor)
    b.setMinimumHeight(26)
    if w:
        b.setFixedWidth(w)
    return b


TABLE_STYLE = """
    QTableWidget {
        font-size: 9pt; border: 1px solid #DDD;
        gridline-color: #EEE; background: white;
        alternate-background-color: #EBF5FB;
    }
    QHeaderView::section {
        background: #D9E1F2; font-weight: bold; font-size: 9pt;
        padding: 4px; border: 1px solid #CCC; color: #2C3E50;
    }
    QTableWidget::item { padding: 2px 5px; }
    QTableWidget::item:selected { background: #3498DB; color: white; }
"""


class ExamView(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self._tabs = None
        self._build_ui()

    def refresh(self):
        self._refresh_list_tab()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Toolbar
        tb = QHBoxLayout()
        tb.setSpacing(4)
        tb.addWidget(QLabel("考试管理"))
        tb.addStretch()
        layout.addLayout(tb)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setFont(font(9))
        self._tabs.addTab(self._build_list_tab(), "考试列表")
        self._tabs.addTab(self._build_create_tab(), "新建考试")
        layout.addWidget(self._tabs)

    def _build_list_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(4, 4, 4, 4)

        exams = self.session.query(Exam).order_by(Exam.id.desc()).all()
        t = QTableWidget(len(exams), 5)
        t.setHorizontalHeaderLabels(["ID", "学期", "年级", "考试名称", "日期"])
        t.setFont(font(9))
        t.verticalHeader().hide()
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setStyleSheet(TABLE_STYLE)

        for i, e in enumerate(exams):
            t.setItem(i, 0, QTableWidgetItem(str(e.id)))
            t.setItem(i, 1, QTableWidgetItem(e.semester.label if e.semester else ""))
            t.setItem(i, 2, QTableWidgetItem(e.grade.name if e.grade else ""))
            t.setItem(i, 3, QTableWidgetItem(e.name))
            t.setItem(i, 4, QTableWidgetItem(str(e.exam_date) if e.exam_date else ""))
        l.addWidget(t)
        return w

    def _build_create_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(8, 8, 8, 8)
        l.setSpacing(8)

        cy = datetime.now().year
        grp = QGroupBox("新建考试")
        grp.setFont(font(10, True))
        gl = QVBoxLayout(grp)
        gl.setSpacing(6)

        # 学期选择
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.addWidget(QLabel("学期:"))
        sem_cb = QComboBox()
        sem_cb.setFont(font(9))
        sem_cb.setFixedWidth(200)
        semesters = self.session.query(Semester).order_by(Semester.year_start.desc()).all()
        for s in semesters:
            sem_cb.addItem(s.label, s.id)
        row1.addWidget(sem_cb)
        row1.addStretch()
        gl.addLayout(row1)

        # 年级
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.addWidget(QLabel("年级:"))
        grade_cb = QComboBox()
        grade_cb.setFont(font(9))
        grade_cb.setFixedWidth(120)
        for g in self.session.query(Grade).order_by(Grade.sort_order).all():
            grade_cb.addItem(g.name, g.id)
        row2.addWidget(grade_cb)
        row2.addStretch()
        gl.addLayout(row2)

        # 考试名称
        row3 = QHBoxLayout()
        row3.setSpacing(6)
        row3.addWidget(QLabel("名称:"))
        name_e = QLineEdit()
        name_e.setFont(font(9))
        name_e.setPlaceholderText("如: 期中考试、期末考试")
        name_e.setFixedWidth(200)
        row3.addWidget(name_e)
        row3.addStretch()
        gl.addLayout(row3)

        # 日期
        row4 = QHBoxLayout()
        row4.setSpacing(6)
        row4.addWidget(QLabel("日期:"))
        date_e = QDateEdit(QDate.currentDate())
        date_e.setCalendarPopup(True)
        date_e.setFont(font(9))
        date_e.setFixedWidth(150)
        row4.addWidget(date_e)
        row4.addStretch()
        gl.addLayout(row4)

        # 备注
        row5 = QHBoxLayout()
        row5.setSpacing(6)
        row5.addWidget(QLabel("备注:"))
        note_e = QLineEdit()
        note_e.setFont(font(9))
        note_e.setFixedWidth(300)
        row5.addWidget(note_e)
        row5.addStretch()
        gl.addLayout(row5)

        # 创建按钮
        b = QPushButton("创建考试")
        b.setStyleSheet(
            f"""QPushButton {{ background: {C["accent_green"]}; color: white; border: none;
            border-radius: 4px; padding: 8px 20px; font-size: 10pt; font-weight: bold; }}
            QPushButton:hover {{ background: #27AE60; }}"""
        )
        b.setCursor(Qt.PointingHandCursor)
        b.setMinimumHeight(36)
        b.clicked.connect(lambda: self._create_exam(sem_cb, grade_cb, name_e, date_e, note_e))
        gl.addWidget(b, alignment=Qt.AlignLeft)

        l.addWidget(grp)
        l.addStretch()
        return w

    def _create_exam(self, sem_cb, grade_cb, name_e, date_e, note_e):
        if not name_e.text().strip():
            QMessageBox.warning(self, "错误", "请输入考试名称")
            return
        if sem_cb.currentData() is None:
            QMessageBox.warning(self, "错误", "请选择学期")
            return
        e = Exam(
            semester_id=sem_cb.currentData(),
            grade_id=grade_cb.currentData(),
            name=name_e.text().strip(),
            exam_date=date_e.date().toPyDate(),
            note=note_e.text().strip(),
        )
        self.session.add(e)
        self.session.commit()
        QMessageBox.information(self, "完成", f"已创建考试: {e.name}")
        name_e.clear()
        note_e.clear()
        self._refresh_list_tab()

    def _refresh_list_tab(self):
        # Rebuild list tab by removing and re-adding
        self._tabs.removeTab(0)
        self._tabs.insertTab(0, self._build_list_tab(), "考试列表")
        self._tabs.setCurrentIndex(0)
