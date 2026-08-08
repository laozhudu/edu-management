"""
GUI 视图 — 成绩管理（PyQt5 统一风格）
Tab 设计：成绩编辑 / 统计概览 / 可视化分析（Qt Charts 原生图表）
"""

from PyQt5.QtChart import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QBoxPlotSeries,
    QBoxSet,
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from edu_system.gui.theme import TABLE_STYLE, C, font
from edu_system.models import Exam, Score, Student, Subject
from edu_system.services.importer import ImportService
from edu_system.services.score import ScoreService


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


class ScoreView(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self._exam_id = None
        self._subjects = []
        self._data = []
        self._build_ui()
        self._refresh_exam_list()

    def refresh(self):
        self._refresh_exam_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Toolbar
        tb = QHBoxLayout()
        tb.setSpacing(4)
        tb.addWidget(self._lbl("考试:"))
        self._exam_cb = QComboBox()
        self._exam_cb.setFont(font(9))
        self._exam_cb.setMinimumWidth(300)
        self._exam_cb.currentIndexChanged.connect(self._on_exam_changed)
        tb.addWidget(self._exam_cb)

        tb.addSpacing(6)
        for txt, clr, cb in [
            ("刷新", "gray", self._refresh_exam_list),
            ("导入成绩", C["accent_blue"], self._import_scores),
            ("保存修改", C["accent_green"], self._save),
            ("重算统计", C["accent_purple"], self._recalc_stats),
        ]:
            b = _btn(txt, clr)
            b.clicked.connect(cb)
            tb.addWidget(b)
        tb.addStretch()
        layout.addLayout(tb)

        # Tabs: 成绩编辑 / 统计概览 / 可视化分析
        self._tabs = QTabWidget()
        self._tabs.setFont(font(9))

        # Tab 1: 成绩表格
        self._table_tab = QWidget()
        tl = QVBoxLayout(self._table_tab)
        tl.setContentsMargins(2, 4, 2, 2)
        self._table = QTableWidget()
        self._table.setStyleSheet(TABLE_STYLE)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().hide()
        tl.addWidget(self._table)

        # Tab 2: 统计概览（文本）
        self._stats_tab = QWidget()
        sl = QVBoxLayout(self._stats_tab)
        self._stats_text = QTextEdit()
        self._stats_text.setReadOnly(True)
        self._stats_text.setFont(font(9))
        sl.addWidget(self._stats_text)

        # Tab 3: 可视化分析（Qt Charts 原生）
        self._viz_tab = QWidget()
        vl = QVBoxLayout(self._viz_tab)
        vl.setContentsMargins(0, 0, 0, 0)

        # 控制栏
        ctrl = QHBoxLayout()
        ctrl.setSpacing(6)
        ctrl.addWidget(self._lbl("图表类型:"))
        self._chart_type = QComboBox()
        self._chart_type.addItems(
            [
                "各科分布(箱线)",
                "班级对比(柱状)",
                "分数段分布(直方)",
                "趋势对比(折线)",
                "优秀/及格率(堆叠)",
            ]
        )
        self._chart_type.setFont(font(9))
        self._chart_type.setFixedWidth(180)
        self._chart_type.currentIndexChanged.connect(self._render_chart)
        ctrl.addWidget(self._chart_type)

        ctrl.addWidget(self._lbl("科目:"))
        self._chart_subject = QComboBox()
        self._chart_subject.setFont(font(9))
        self._chart_subject.setFixedWidth(120)
        self._chart_subject.currentIndexChanged.connect(self._render_chart)
        ctrl.addWidget(self._chart_subject)

        ctrl.addWidget(self._lbl("班级:"))
        self._chart_class = QComboBox()
        self._chart_class.addItem("全部")
        self._chart_class.setFont(font(9))
        self._chart_class.setFixedWidth(100)
        self._chart_class.currentIndexChanged.connect(self._render_chart)
        ctrl.addWidget(self._chart_class)

        ctrl.addStretch()
        vl.addLayout(ctrl)

        # Qt Charts 容器
        self._chart_view = QChartView()
        self._chart_view.setMinimumHeight(400)
        self._chart_view.setRenderHint(QPainter.Antialiasing)
        vl.addWidget(self._chart_view)

        self._tabs.addTab(self._table_tab, "成绩编辑")
        self._tabs.addTab(self._stats_tab, "统计概览")
        self._tabs.addTab(self._viz_tab, "可视化分析")
        layout.addWidget(self._tabs)

        # Status bar
        self._status = QLabel("请选择考试")
        self._status.setFont(font(8))
        self._status.setStyleSheet("color: #666; padding: 2px;")
        layout.addWidget(self._status)

    def _lbl(self, text, sz=8):
        lay = QLabel(text)
        lay.setFont(font(sz))
        return lay

    def _refresh_exam_list(self):
        exams = self.session.query(Exam).order_by(Exam.id.desc()).all()
        self._exam_cb.blockSignals(True)
        self._exam_cb.clear()
        for e in exams:
            grade = e.grade.name if e.grade else ""
            lbl = f"ID{e.id}  {e.semester.label if e.semester else ''}  {grade}  {e.name}"
            self._exam_cb.addItem(lbl, e.id)
        self._exam_cb.blockSignals(False)
        if exams:
            self._exam_cb.setCurrentIndex(0)
            self._on_exam_changed()

    def _on_exam_changed(self):
        idx = self._exam_cb.currentIndex()
        if idx < 0:
            return
        self._exam_id = self._exam_cb.itemData(idx)
        self._load_scores()
        self._show_stats()
        self._prepare_chart_controls()
        self._render_chart()

    def _load_scores(self):
        if not self._exam_id:
            return
        svc = ScoreService(self.session)
        students, subjects, _ = svc.get_exam_scores(self._exam_id)
        self._subjects = subjects
        self._data = students

        headers = ["班级", "姓名"] + subjects + ["总分"]
        self._table.setColumnCount(len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.setRowCount(len(students))

        for i, s in enumerate(students):
            self._table.setItem(i, 0, QTableWidgetItem(s["class_name"]))
            name_item = QTableWidgetItem(s["name"])
            name_item.setData(Qt.UserRole, s.get("student_id"))
            self._table.setItem(i, 1, name_item)
            total = 0
            for j, subj in enumerate(subjects):
                v = s["scores"].get(subj)
                item = QTableWidgetItem(str(v) if v is not None else "")
                item.setTextAlignment(Qt.AlignCenter)
                if v is not None:
                    total += v
                    if v < 30:
                        item.setForeground(QColor("#E74C3C"))
                    elif v >= 90:
                        item.setForeground(QColor("#27AE60"))
                self._table.setItem(i, 2 + j, item)
            total_item = QTableWidgetItem(str(round(total, 1)) if total else "")
            total_item.setTextAlignment(Qt.AlignCenter)
            total_item.setForeground(QColor("#2C3E50"))
            self._table.setItem(i, 2 + len(subjects), total_item)

        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._status.setText(f"已加载 {len(students)} 名学生 × {len(subjects)} 科")

    def _show_stats(self):
        if not self._exam_id:
            return
        svc = ScoreService(self.session)
        students, subjects, configs = svc.get_exam_scores(self._exam_id)

        lines = ["=== 各科统计 ===\n"]
        for subj in subjects:
            scores = [s["scores"].get(subj) for s in students if s["scores"].get(subj) is not None]
            if not scores:
                continue
            cfg = configs.get(subj, {"pass_line": 60})
            pl = cfg.get("pass_line", 60)
            gl = cfg.get("good_line", pl * 1.2)
            el = cfg.get("excellent_line", pl * 1.5)
            ll = cfg.get("low_line", pl * 0.5)
            avg = round(sum(scores) / len(scores), 1)
            pass_rate = round(sum(1 for x in scores if x >= pl) / len(scores) * 100, 1)
            good_rate = round(sum(1 for x in scores if x >= gl) / len(scores) * 100, 1)
            excellent = round(sum(1 for x in scores if x >= el) / len(scores) * 100, 1)
            low = round(sum(1 for x in scores if x < ll) / len(scores) * 100, 1)
            lines.append(
                f"{subj}: 人数={len(scores)}  均分={avg}  "
                f"及格={pass_rate}%  良好={good_rate}%  优秀={excellent}%  低分={low}%"
            )

        lines.append("\n=== 各班均分对比 ===\n")
        from collections import defaultdict

        by_class = defaultdict(lambda: defaultdict(list))
        for s in students:
            for subj in subjects:
                v = s["scores"].get(subj)
                if v is not None:
                    by_class[s["class_name"]][subj].append(v)

        classes = sorted(by_class.keys())
        header = "班级".ljust(8)
        for subj in subjects:
            header += subj.ljust(10)
        lines.append(header)
        for cls_name in classes:
            line = cls_name.ljust(8)
            for subj in subjects:
                vals = by_class[cls_name].get(subj, [])
                avg = round(sum(vals) / len(vals), 1) if vals else "-"
                line += str(avg).ljust(10)
            lines.append(line)

        self._stats_text.setText("\n".join(lines))

    def _recalc_stats(self):
        if not self._exam_id:
            return
        self._show_stats()
        self._status.setText("统计已重算")

    def _prepare_chart_controls(self):
        """根据当前考试更新图表控件的下拉选项"""
        exam = self.session.get(Exam, self._exam_id) if self._exam_id else None
        if not exam:
            return

        # 更新科目下拉
        self._chart_subject.blockSignals(True)
        self._chart_subject.clear()
        self._chart_subject.addItem("全部")
        for subj in self._subjects:
            self._chart_subject.addItem(subj)
        self._chart_subject.blockSignals(False)

        # 更新班级下拉
        self._chart_class.blockSignals(True)
        self._chart_class.clear()
        self._chart_class.addItem("全部")
        classes = sorted(set(s["class_name"] for s in self._data))
        for cls in classes:
            self._chart_class.addItem(cls)
        self._chart_class.blockSignals(False)

    def _render_chart(self):
        """生成 Qt Charts 图表"""
        if not self._exam_id or not self._data:
            return

        chart_type = self._chart_type.currentIndex()
        subject_filter = self._chart_subject.currentText()
        class_filter = self._chart_class.currentText()

        # 清除旧图表
        chart = QChart()
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setAlignment(Qt.AlignBottom)

        if chart_type == 0:  # 各科分布(箱线)
            self._build_boxplot_chart(chart, subject_filter)
        elif chart_type == 1:  # 班级对比(柱状)
            self._build_bar_chart(chart, class_filter)
        elif chart_type == 2:  # 分数段分布(直方)
            self._build_histogram_chart(chart, subject_filter)
        elif chart_type == 3:  # 趋势对比(折线)
            self._build_line_chart(chart)
        else:  # 优秀/及格率(堆叠)
            self._build_stacked_bar_chart(chart)

        self._chart_view.setChart(chart)

    def _build_boxplot_chart(self, chart, subject_filter):
        """各科分数分布（箱线图）"""
        subjects = [subject_filter] if subject_filter != "全部" else self._subjects
        series = QBoxPlotSeries()
        series.setName("分数分布")

        for subj in subjects:
            scores = [
                s["scores"].get(subj) for s in self._data if s["scores"].get(subj) is not None
            ]
            if not scores:
                continue
            scores.sort()
            n = len(scores)
            q1 = scores[n // 4]
            q2 = scores[n // 2]
            q3 = scores[3 * n // 4]
            min_v = scores[0]
            max_v = scores[-1]

            box = QBoxSet()
            box.setValue(0, min_v)
            box.setValue(1, q1)
            box.setValue(2, q2)
            box.setValue(3, q3)
            box.setValue(4, max_v)
            box.setLabel(subj)
            series.append(box)

        chart.addSeries(series)
        chart.setTitle("各科分数分布（箱线图）")
        chart.createDefaultAxes()
        chart.axisY().setTitleText("分数")

    def _build_bar_chart(self, chart, class_filter):
        """班级均分对比（柱状图）"""
        from collections import defaultdict

        by_class = defaultdict(lambda: defaultdict(list))
        for s in self._data:
            for subj in self._subjects:
                v = s["scores"].get(subj)
                if v is not None:
                    by_class[s["class_name"]][subj].append(v)

        classes = sorted(by_class.keys())
        if class_filter != "全部":
            classes = [c for c in classes if c == class_filter]

        chart.setTitle("各班均分对比")
        for subj in self._subjects:
            bar_set = QBarSet(subj)
            for cls in classes:
                vals = by_class[cls].get(subj, [])
                avg = round(sum(vals) / len(vals), 1) if vals else 0
                bar_set.append(avg)
            series = QBarSeries()
            series.append(bar_set)
            chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(classes)
        axis_x.setTitleText("班级")
        chart.addAxis(axis_x, Qt.AlignBottom)
        for series in chart.series():
            series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("均分")
        axis_y.setRange(0, 120)
        chart.addAxis(axis_y, Qt.AlignLeft)
        for series in chart.series():
            series.attachAxis(axis_y)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

    def _build_histogram_chart(self, chart, subject_filter):
        """分数段分布（直方图）"""
        subjects = [subject_filter] if subject_filter != "全部" else self._subjects

        for subj in subjects:
            scores = [
                s["scores"].get(subj) for s in self._data if s["scores"].get(subj) is not None
            ]
            if not scores:
                continue
            bins = [0] * 10
            for v in scores:
                idx = min(int(v // 10), 9)
                bins[idx] += 1

            bar_set = QBarSet(subj)
            for count in bins:
                bar_set.append(count)
            series = QBarSeries()
            series.append(bar_set)
            chart.addSeries(series)

        chart.setTitle("分数段分布（直方图）")
        axis_x = QBarCategoryAxis()
        axis_x.append([f"{i * 10}-{i * 10 + 9}" for i in range(10)])
        axis_x.setTitleText("分数段")
        chart.addAxis(axis_x, Qt.AlignBottom)
        for series in chart.series():
            series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("人数")
        chart.addAxis(axis_y, Qt.AlignLeft)
        for series in chart.series():
            series.attachAxis(axis_y)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

    def _build_line_chart(self, chart):
        """趋势对比：当前考试 vs 上次考试（同年级同科目）"""
        exam = self.session.get(self._exam_id)
        if not exam or not exam.grade_id:
            chart.setTitle("无法对比")
            return

        # 找同年级的上一次考试
        prev_exam = (
            self.session.query(Exam)
            .filter(
                Exam.grade_id == exam.grade_id, Exam.id != exam.id, Exam.exam_date < exam.exam_date
            )
            .order_by(Exam.exam_date.desc())
            .first()
        )

        if not prev_exam:
            chart.setTitle("无历史考试可对比")
            return

        from edu_system.services.score import ScoreService

        svc = ScoreService(self.session)
        students_cur, subjects, _ = svc.get_exam_scores(exam.id)
        students_prev, _, _ = svc.get_exam_scores(prev_exam.id)

        classes = sorted(set(s["class_name"] for s in self._data))

        for subj in self._subjects:
            cur_series = QLineSeries()
            cur_series.setName(f"{subj}(本次)")
            prev_series = QLineSeries()
            prev_series.setName(f"{subj}(上次)")
            prev_series.setPen(QColor("#999999"))

            for cls in classes:
                cur_scores = [
                    s["scores"].get(subj)
                    for s in self._data
                    if s["class_name"] == cls and s["scores"].get(subj) is not None
                ]
                prev_scores = [
                    s["scores"].get(subj)
                    for s in self._get_prev_data(prev_exam.id)
                    if s["class_name"] == cls and s["scores"].get(subj) is not None
                ]
                cur_avg = round(sum(cur_scores) / len(cur_scores), 1) if cur_scores else 0
                prev_avg = round(sum(prev_scores) / len(prev_scores), 1) if prev_scores else 0

                # 找到班级索引
                cls_idx = self._get_class_index(cls)
                cur_series.append(cls_idx, cur_avg)
                prev_series.append(cls_idx, prev_avg)

            chart.addSeries(cur_series)
            chart.addSeries(prev_series)

        chart.setTitle(f"趋势对比：{exam.name} vs {prev_exam.name}")
        axis_x = QBarCategoryAxis()
        axis_x.append([str(i) for i in range(len(self._get_class_list()))])
        axis_x.setTitleText("班级")
        chart.addAxis(axis_x, Qt.AlignBottom)

        axis_y = QValueAxis()
        axis_y.setTitleText("均分")
        axis_y.setRange(0, 120)
        chart.addAxis(axis_y, Qt.AlignLeft)

        for series in chart.series():
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

    def _build_stacked_bar_chart(self, chart):
        """优秀/及格/低分率堆叠柱状图"""
        exam = self.session.get(self._exam_id)
        cfg = self.session.query(Subject).all()
        cfg_dict = {
            s.name: {"pass_line": s.pass_line or 60, "excellent_line": s.excellent_line or 90}
            for s in cfg
        }

        classes = sorted(set(s["class_name"] for s in self._data))
        pass_rates = []
        good_rates = []
        excellent_rates = []
        low_rates = []

        for cls in classes:
            cls_students = [s for s in self._data if s["class_name"] == cls]
            total = len(cls_students)
            if total == 0:
                pass_rates.append(0)
                good_rates.append(0)
                excellent_rates.append(0)
                low_rates.append(0)
                continue

            pass_cnt = 0
            good_cnt = 0
            excellent_cnt = 0
            low_cnt = 0
            for s in cls_students:
                for subj in self._subjects:
                    v = s["scores"].get(subj)
                    if v is None:
                        continue
                    pl = cfg_dict.get(subj, {}).get("pass_line", 60)
                    el = cfg_dict.get(subj, {}).get("excellent_line", 90)
                    if v >= el:
                        excellent_cnt += 1
                    elif v >= pl:
                        good_cnt += 1
                    else:
                        low_cnt += 1

            pass_rates.append(round((pass_cnt + good_cnt) / total * 100, 1))
            good_rates.append(round(good_cnt / total * 100, 1))
            excellent_rates.append(round(excellent_cnt / total * 100, 1))
            low_rates.append(round(low_cnt / total * 100, 1))

        chart.setTitle("优秀/良好/及格/低分率对比")
        for name, data, color in [
            ("优秀率", excellent_rates, QColor("#27AE60")),
            ("良好率", good_rates, QColor("#3498DB")),
            ("及格率", pass_rates, QColor("#F39C12")),
            ("低分率", low_rates, QColor("#E74C3C")),
        ]:
            bar_set = QBarSet(name)
            for v in data:
                bar_set.append(v)
            series = QBarSeries()
            series.append(bar_set)
            chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append([str(i) for i in range(len(self._get_class_list()))])
        axis_x.setTitleText("班级")
        chart.addAxis(axis_x, Qt.AlignBottom)
        for series in chart.series():
            series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("比例 (%)")
        axis_y.setRange(0, 100)
        chart.addAxis(axis_y, Qt.AlignLeft)
        for series in chart.series():
            series.attachAxis(axis_y)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

    def _get_prev_data(self, exam_id):
        """获取历史考试数据（用于趋势对比）"""
        from edu_system.services.score import ScoreService

        svc = ScoreService(self.session)
        students, _, _ = svc.get_exam_scores(exam_id)
        return students

    def _get_class_list(self):
        """获取班级列表"""
        return sorted(set(s["class_name"] for s in self._data))

    def _get_class_index(self, class_name):
        classes = self._get_class_list()
        return classes.index(class_name) if class_name in classes else 0

    def _prepare_chart_controls(self):
        """根据当前考试更新图表控件的下拉选项"""
        exam = self.session.get(Exam, self._exam_id) if self._exam_id else None
        if not exam:
            return

        # 更新科目下拉
        self._chart_subject.blockSignals(True)
        self._chart_subject.clear()
        self._chart_subject.addItem("全部")
        for subj in self._subjects:
            self._chart_subject.addItem(subj)
        self._chart_subject.blockSignals(False)

        # 更新班级下拉
        self._chart_class.blockSignals(True)
        self._chart_class.clear()
        self._chart_class.addItem("全部")
        classes = sorted(set(s["class_name"] for s in self._data))
        for cls in classes:
            self._chart_class.addItem(cls)
        self._chart_class.blockSignals(False)

    def _save(self):
        if not self._exam_id:
            return
        from edu_system.models import Subject

        updated = 0
        for row in range(self._table.rowCount()):
            cls_name = self._table.item(row, 0).text() if self._table.item(row, 0) else ""
            stu_name = self._table.item(row, 1).text() if self._table.item(row, 1) else ""
            if not stu_name:
                continue

            student_id = None
            item = self._table.item(row, 1)
            if item:
                student_id = item.data(Qt.UserRole)

            if not student_id:
                student = (
                    self.session.query(Student)
                    .join(Student.class_)
                    .filter(Student.name == stu_name)
                    .first()
                )
                if student:
                    student_id = student.id
            else:
                student = self.session.get(Student, student_id)

            if not student:
                continue

            for j, subj_name in enumerate(self._subjects):
                item = self._table.item(row, 2 + j)
                if not item:
                    continue
                text = item.text().strip()
                if not text:
                    continue
                try:
                    v = float(text)
                except ValueError:
                    continue

                subj = self.session.query(Subject).filter_by(name=subj_name).first()
                if not subj:
                    continue

                existing = (
                    self.session.query(Score)
                    .filter_by(exam_id=self._exam_id, student_id=student.id, subject_id=subj.id)
                    .first()
                )
                if existing:
                    existing.score = v
                else:
                    self.session.add(
                        Score(
                            exam_id=self._exam_id,
                            student_id=student.id,
                            subject_id=subj.id,
                            score=v,
                        )
                    )
                updated += 1

        self.session.commit()
        self._status.setText(f"已保存 {updated} 条成绩")

    def _import_scores(self):
        if not self._exam_id:
            QMessageBox.warning(self, "提示", "请先选择考试")
            return

        path, _ = QFileDialog.getOpenFileName(self, "选择成绩文件", "", "Excel (*.xlsx *.xls)")
        if not path:
            return

        result = ImportService(self.session).import_scores_from_excel(path, self._exam_id)
        self.session.commit()
        QMessageBox.information(self, "导入结果", result.summary)
        self._load_scores()
        self._show_stats()
        self._prepare_chart_controls()
        self._render_chart()
