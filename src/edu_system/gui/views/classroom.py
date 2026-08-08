"""
GUI 视图 — 教室位置管理 (PyQt5)
按学年学期管理每班教室位置，为考场编排做准备
"""

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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
from sqlalchemy.orm import Session

from edu_system.gui.theme import C, font
from edu_system.models import Class as ClassModel
from edu_system.models import Grade, Semester


class ClassroomView(QWidget):
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
        tb.addWidget(QLabel("教室位置"))
        tb.addStretch()
        b = QPushButton("批量设置楼层")
        b.setStyleSheet(
            f"background:{C['accent_blue']}; color:white; border:none; border-radius:3px; padding:5px 12px; font-size:9pt;"
        )
        b.clicked.connect(self._batch_set)
        tb.addWidget(b)
        lay.addLayout(tb)

        cur = self.session.query(Semester).filter_by(is_active=True).first()
        lay.addWidget(QLabel(f"当前学期: {cur.label if cur else '未设置'}"))

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
                continue
            t = QTableWidget(len(classes), 4)
            t.setHorizontalHeaderLabels(["班级", "教室楼层", "教室编号", "座位数"])
            t.setFont(font(9))
            t.verticalHeader().hide()
            t.setAlternatingRowColors(True)
            t.setEditTriggers(QTableWidget.NoEditTriggers)
            t.setSelectionBehavior(QTableWidget.SelectRows)
            t.setStyleSheet(
                """QTableWidget { font-size:9pt; border:1px solid #DDD;
                background:white; alternate-background-color:#EBF5FB; }
                QHeaderView::section { background:#D9E1F2; font-weight:bold; padding:4px;
                border:1px solid #CCC; }"""
            )
            for i, c in enumerate(classes):
                t.setItem(i, 0, QTableWidgetItem(c.name))
                t.setItem(i, 1, QTableWidgetItem(c.room or ""))
                t.setItem(i, 2, QTableWidgetItem(c.class_type or ""))
                t.setItem(i, 3, QTableWidgetItem(""))
            t.setMaximumHeight(30 + 22 * len(classes))
            t.horizontalHeader().setStretchLastSection(True)
            t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            t.cellDoubleClicked.connect(lambda r, c, tbl=t: self._edit_room(tbl, r))
            lay.addWidget(t)

        lay.addStretch()

    def _edit_room(self, table, row):
        cls_name = table.item(row, 0).text()
        cls = self.session.query(ClassModel).filter_by(name=cls_name).first()
        if not cls:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"设置教室 - {cls_name}")
        f = QFormLayout(dlg)
        floor = QLineEdit(cls.room or "")
        f.addRow("楼层:", floor)
        room = QLineEdit(cls.class_type or "")
        f.addRow("教室号:", room)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec_():
            cls.room = floor.text().strip()
            cls.class_type = room.text().strip()
            self.session.commit()
            self._rebuild()

    def _batch_set(self):
        cur = self.session.query(Semester).filter_by(is_active=True).first()
        floor, ok = QLineEdit.getText(self, "批量设置楼层", "楼层(如: 2楼):")
        if not ok:
            return
        for cls in self.session.query(ClassModel).all():
            cls.room = floor.strip()
        self.session.commit()
        self._rebuild()
        QMessageBox.information(self, "完成", f"已设置所有班级楼层为: {floor.strip()}")
