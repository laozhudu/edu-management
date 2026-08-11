"""
GUI 视图 — 班级管理 (PyQt5)
查看/编辑/新增班级，分配班主任，班级统计
"""

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from edu_system.gui.theme import C, font
from edu_system.models import Class as ClassModel
from edu_system.models import Grade, Student, Teacher


def _btn(txt, color, w=None):
    from edu_system.gui.components import btn

    return btn(txt, color, w)

class ClassView(QWidget):
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
        lay.setSpacing(6)

        # 工具栏
        tb = QHBoxLayout()
        tb.setSpacing(4)
        tb.addWidget(QLabel("班级管理"))
        tb.addStretch()
        for txt, clr, cb in [
            ("新增班级", C["accent_green"], self._add_class),
            ("编辑班主任", C["accent_blue"], self._edit_head_teacher),
        ]:
            b = _btn(txt, clr)
            b.clicked.connect(cb)
            tb.addWidget(b)
        lay.addLayout(tb)

        # 按年级分组的卡片
        grades = self.session.query(Grade).order_by(Grade.sort_order).all()
        for g in grades:
            lay.addWidget(QLabel(f"  {g.name}"))
            classes = (
                self.session.query(ClassModel)
                .filter_by(grade_id=g.id)
                .order_by(ClassModel.name)
                .all()
            )
            if not classes:
                lay.addWidget(QLabel("    (无班级)"))
                continue
            t = QTableWidget(len(classes), 5)
            t.setHorizontalHeaderLabels(["班级", "班主任", "在校生", "男生", "女生"])
            t.setFont(font(9))
            t.verticalHeader().hide()
            t.setAlternatingRowColors(True)
            t.setEditTriggers(QTableWidget.NoEditTriggers)
            t.setSelectionBehavior(QTableWidget.SelectRows)
            t.setStyleSheet(
                """QTableWidget { font-size:9pt; border:1px solid #DDD;
                background:white; alternate-background-color:#EBF5FB; }
                QHeaderView::section { background: {C["table_header_bg"]}; font-weight:bold;
                padding:4px; border:1px solid {C["table_header_border"]}; }"""
            )
            for i, c in enumerate(classes):
                t.setItem(i, 0, QTableWidgetItem(c.name))
                t.setItem(i, 1, QTableWidgetItem(c.head_teacher or ""))
                male = (
                    self.session.query(Student)
                    .filter_by(class_id=c.id, status="在校", gender="男")
                    .count()
                )
                female = (
                    self.session.query(Student)
                    .filter_by(class_id=c.id, status="在校", gender="女")
                    .count()
                )
                t.setItem(i, 2, QTableWidgetItem(str(male + female)))
                mi = QTableWidgetItem(str(male))
                mi.setForeground(QColor(C["accent_blue"]))
                t.setItem(i, 3, mi)
                fi = QTableWidgetItem(str(female))
                fi.setForeground(QColor(C["accent_purple"]))
                t.setItem(i, 4, fi)
            t.setMaximumHeight(30 + 24 * len(classes))
            t.horizontalHeader().setStretchLastSection(True)
            t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            lay.addWidget(t)
        lay.addStretch()

    def _add_class(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("新增班级")
        dlg.setMinimumWidth(300)
        f = QFormLayout(dlg)
        grades = self.session.query(Grade).order_by(Grade.sort_order).all()
        g_cb = QComboBox()
        g_cb.setFont(font(9))
        for g in grades:
            g_cb.addItem(g.name, g.id)
        f.addRow("年级:", g_cb)
        name_e = QLineEdit()
        name_e.setFont(font(9))
        f.addRow("班级名:", name_e)
        ht_e = QLineEdit()
        ht_e.setFont(font(9))
        f.addRow("班主任:", ht_e)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec_():
            name = name_e.text().strip()
            if not name:
                return
            cls = ClassModel(
                grade_id=g_cb.currentData(), name=name, head_teacher=ht_e.text().strip()
            )
            self.session.add(cls)
            self.session.commit()
            self._rebuild()

    def _edit_head_teacher(self):
        classes = self.session.query(ClassModel).order_by(ClassModel.name).all()
        if not classes:
            return
        names = [c.name for c in classes]
        cname, ok = QInputDialog.getItem(self, "选择班级", "班级:", names, 0, False)
        if not ok:
            return
        cls = self.session.query(ClassModel).filter_by(name=cname).first()
        if not cls:
            return
        # 可从教师列表选
        teachers = self.session.query(Teacher).order_by(Teacher.name).all()
        tnames = [t.name for t in teachers]
        tname, ok = QInputDialog.getItem(
            self, "选择班主任", f"为 {cname} 选班主任:", tnames, 0, False
        )
        if ok:
            cls.head_teacher = tname
            self.session.commit()
            self._rebuild()
