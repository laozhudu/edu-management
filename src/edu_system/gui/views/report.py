"""
GUI 视图 — 统计报表（PyQt5）
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from edu_system.gui.theme import C, font
from edu_system.models import Exam


class ReportView(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self._build_ui()

    def _build_ui(self):
        if self.layout():
            QWidget().setLayout(self.layout())
        self.setLayout(QVBoxLayout())
        l = self.layout()
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(8)

        # 工具栏
        tb = QHBoxLayout()
        tb.setSpacing(4)
        tb.addWidget(QLabel("生成考试报表"))
        tb.addStretch()
        l.addLayout(tb)

        # 选择考试
        row = QHBoxLayout()
        row.addWidget(self._lbl("选择考试:"))
        exams = self.session.query(Exam).order_by(Exam.id.desc()).all()
        self._exam_cb = QComboBox()
        self._exam_cb.setFont(font(9))
        self._exam_cb.setMinimumWidth(300)
        for e in exams:
            grade = e.grade.name if e.grade else ""
            sem = e.semester.label if e.semester else ""
            self._exam_cb.addItem(f"ID{e.id}  {sem}  {grade}  {e.name}", e.id)
        row.addWidget(self._exam_cb)
        row.addStretch()
        l.addLayout(row)

        # 生成按钮
        btns = QHBoxLayout()
        btns.setSpacing(6)
        for txt, clr, report_type in [
            ("生成成绩报表", C["accent_blue"], "exam"),
            ("生成变动情况表", C["accent_orange"], "movement"),
        ]:
            b = QPushButton(txt)
            b.setStyleSheet(
                f"""
                QPushButton {{ background: {clr}; color: white; border: none;
                    border-radius: 4px; padding: 8px 16px; font-size: 10pt; }}
                QPushButton:hover {{ background: #34495E; }}
            """
            )
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, t=report_type: self._generate(t))
            btns.addWidget(b)
        btns.addStretch()
        l.addLayout(btns)
        l.addStretch()

    def _lbl(self, t):
        l = QLabel(t)
        l.setFont(font(9))
        return l

    def _generate(self, report_type):
        idx = self._exam_cb.currentIndex()
        if idx < 0:
            return
        exam_id = self._exam_cb.itemData(idx)

        path, _ = QFileDialog.getSaveFileName(self, "保存报表", "", "Excel (*.xlsx)")
        if not path:
            return

        try:
            if report_type == "exam":
                from edu_system.services.report import ReportService

                svc = ReportService(self.session)
                svc.generate_exam_report(exam_id, path)
            else:
                exam = self.session.query(Exam).get(exam_id)
                from edu_system.services.report import ReportService

                svc = ReportService(self.session)
                svc.generate_change_report(exam.semester_id if exam else None, path)

            QMessageBox.information(self, "完成", f"报表已保存到:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))
