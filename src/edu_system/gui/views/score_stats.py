"""
ScoreStatsView — 成绩统计视图（R1：成绩域独立统计页）

从 ScoreView 分离：专注学期/考试维度的统计汇总
- 学期/考试选择
- KPI：参考人数 / 平均分 / 及格率 / 优秀率
- 分段分布表（<60 / 60-69 / 70-79 / 80-89 / 90+）
- 班级对比柱状图（QtCharts）
"""

from __future__ import annotations

from PyQt5.QtChart import QBarSeries, QBarSet, QChart, QChartView
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import func

from edu_system.gui.theme import C, font
from edu_system.models import Exam, Score, Semester, Student


class ScoreStatsView(QWidget):
    """成绩统计（学期/考试维度汇总）"""

    def __init__(self, session):
        super().__init__()
        self.session = session
        self._build_ui()
        self._load_semesters()
        self._load_exams()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # 顶部工具行：学期 + 考试选择
        tb = QHBoxLayout()
        tb.setSpacing(6)
        tb.addWidget(self._lbl("学期:"))
        self._semester_cb = QComboBox()
        self._semester_cb.setFont(font(9))
        self._semester_cb.currentIndexChanged.connect(self._on_semester_changed)
        tb.addWidget(self._semester_cb)
        tb.addWidget(self._lbl("考试:"))
        self._exam_cb = QComboBox()
        self._exam_cb.setFont(font(9))
        self._exam_cb.currentIndexChanged.connect(self.refresh)
        tb.addWidget(self._exam_cb)
        tb.addStretch()
        layout.addLayout(tb)

        # KPI 卡片行
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(8)
        self._kpi_labels = {}
        for key, title in [
            ("count", "参考人数"),
            ("avg", "平均分"),
            ("pass", "及格率"),
            ("good", "优秀率"),
        ]:
            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background: {C['white']}; border: 1px solid {C['line']}; border-radius: 6px; padding: 8px; }}"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(8, 6, 8, 6)
            t = QLabel(title)
            t.setFont(font(9))
            t.setStyleSheet(f"color: {C['text_light']};")
            cl.addWidget(t)
            v = QLabel("—")
            v.setFont(font(16, True))
            v.setStyleSheet(f"color: {C['accent_blue']};")
            cl.addWidget(v)
            self._kpi_labels[key] = v
            kpi_layout.addWidget(card)
        layout.addLayout(kpi_layout)

        # 下部：分布表 + 班级对比图
        mid = QHBoxLayout()
        mid.setSpacing(8)

        # 分段分布表
        dist_frame = QFrame()
        dist_frame.setStyleSheet(
            f"QFrame {{ background: {C['white']}; border: 1px solid {C['line']}; border-radius: 6px; }}"
        )
        dl = QVBoxLayout(dist_frame)
        dl.setContentsMargins(8, 8, 8, 8)
        dl.addWidget(self._lbl("分段分布"))
        self._dist_table = QTableWidget(0, 2)
        self._dist_table.setHorizontalHeaderLabels(["分数段", "人数"])
        self._dist_table.setFont(font(9))
        self._dist_table.verticalHeader().hide()
        self._dist_table.horizontalHeader().setStretchLastSection(True)
        self._dist_table.setStyleSheet(
            f"QTableWidget {{ font-size:9pt; border:1px solid {C['table_border']}; }}"
        )
        dl.addWidget(self._dist_table)
        mid.addWidget(dist_frame, 1)

        # 班级对比柱状图
        bar_frame = QFrame()
        bar_frame.setStyleSheet(
            f"QFrame {{ background: {C['white']}; border: 1px solid {C['line']}; border-radius: 6px; }}"
        )
        bl = QVBoxLayout(bar_frame)
        bl.setContentsMargins(8, 8, 8, 8)
        bl.addWidget(self._lbl("班级平均分对比"))
        self._bar_chart = QChartView()
        self._bar_chart.setMinimumHeight(220)
        bl.addWidget(self._bar_chart)
        mid.addWidget(bar_frame, 1)

        layout.addLayout(mid, 1)

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(font(9))
        lbl.setStyleSheet(f"color: {C['text']};")
        return lbl

    def _load_semesters(self):
        self._semester_cb.blockSignals(True)
        self._semester_cb.clear()
        sems = self.session.query(Semester).order_by(Semester.id.desc()).all()
        for s in sems:
            self._semester_cb.addItem(s.display_label, s.id)
        self._semester_cb.blockSignals(False)
        if sems:
            self._semester_cb.setCurrentIndex(0)

    def _on_semester_changed(self):
        self._load_exams()
        self.refresh()

    def _load_exams(self):
        self._exam_cb.blockSignals(True)
        self._exam_cb.clear()
        sem_id = self._semester_cb.currentData()
        if sem_id is None:
            self._exam_cb.blockSignals(False)
            return
        exams = (
            self.session.query(Exam)
            .filter(Exam.semester_id == sem_id)
            .order_by(Exam.id.desc())
            .all()
        )
        self._exam_cb.addItem("全部考试", None)
        for e in exams:
            self._exam_cb.addItem(e.name, e.id)
        self._exam_cb.blockSignals(False)

    def refresh(self):
        if not hasattr(self, "_semester_cb"):
            return
        sem_id = self._semester_cb.currentData()
        exam_id = self._exam_cb.currentData() if hasattr(self, "_exam_cb") else None
        if sem_id is None:
            return

        q = (
            self.session.query(Score)
            .join(Exam)
            .filter(Exam.semester_id == sem_id, Score.score.isnot(None))
        )
        if exam_id:
            q = q.filter(Score.exam_id == exam_id)
        scores = q.all()
        values = [s.score for s in scores]

        if values:
            n = len(values)
            avg = sum(values) / n
            pass_c = sum(1 for v in values if v >= 60)
            good_c = sum(1 for v in values if v >= 90)
            self._kpi_labels["count"].setText(str(n))
            self._kpi_labels["avg"].setText(f"{avg:.1f}")
            self._kpi_labels["pass"].setText(f"{pass_c / n * 100:.1f}%")
            self._kpi_labels["good"].setText(f"{good_c / n * 100:.1f}%")
        else:
            for k in self._kpi_labels:
                self._kpi_labels[k].setText("—")

        # 分段分布
        dist = {"<60": 0, "60-69": 0, "70-79": 0, "80-89": 0, "90+": 0}
        for v in values:
            if v < 60:
                dist["<60"] += 1
            elif v < 70:
                dist["60-69"] += 1
            elif v < 80:
                dist["70-79"] += 1
            elif v < 90:
                dist["80-89"] += 1
            else:
                dist["90+"] += 1
        self._dist_table.setRowCount(len(dist))
        for i, (k, v) in enumerate(dist.items()):
            self._dist_table.setItem(i, 0, QTableWidgetItem(k))
            self._dist_table.setItem(i, 1, QTableWidgetItem(str(v)))

        # 班级平均分对比（柱状图）
        self._render_class_bar(sem_id, exam_id)

    def _render_class_bar(self, sem_id: int, exam_id: int | None):
        from edu_system.models import Class

        chart = QChart()
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setTitle("班级平均分")
        chart.legend().setAlignment(Qt.AlignBottom)
        series = QBarSeries()
        classes = (
            self.session.query(Class).filter(Class.semester_id == sem_id).order_by(Class.name).all()
        )
        for cls in classes:
            q = (
                self.session.query(func.avg(Score.score))
                .join(Exam)
                .filter(
                    Exam.semester_id == sem_id,
                    Score.student_id.in_(
                        self.session.query(Student.id).filter(Student.class_id == cls.id)
                    ),
                )
            )
            if exam_id:
                q = q.filter(Score.exam_id == exam_id)
            avg = q.scalar()
            bset = QBarSet(cls.name)
            bset.append(round(avg, 1) if avg is not None else 0)
            series.append(bset)
        chart.addSeries(series)
        self._bar_chart.setChart(chart)

    def _init_done(self):
        """首帧初始化：加载学期与考试"""
        self._load_semesters()
        self._load_exams()
        self.refresh()
