"""
DashboardView — 首页仪表盘：学期概览 / 快捷操作 / 待办·数据状态
"""

from __future__ import annotations

from collections import OrderedDict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import func

from edu_system.config.ui_config import get_config
from edu_system.gui.theme import C, font
from edu_system.models import Class, Exam, Semester, Student


class RecentVisitsManager:
    """最近访问管理器 - 跟踪用户最近访问的页面"""

    def __init__(self, max_items: int = 5):
        self.max_items = max_items
        # OrderedDict 保持插入顺序，最新的在最前
        self._visits = OrderedDict()

    def add_visit(self, view_id: str, title: str):
        """记录一次访问"""
        # 如果已存在，先删除（移到最前）
        if view_id in self._visits:
            del self._visits[view_id]
        # 插入到最前
        self._visits[view_id] = {"view_id": view_id, "title": title}
        # 限制数量
        if len(self._visits) > self.max_items:
            self._visits.popitem(last=False)  # 删除最旧的

    def get_recent(self, limit: int | None = None) -> list[dict]:
        """获取最近访问列表，最新的在前"""
        items = list(self._visits.values())
        if limit:
            return items[:limit]
        return items

    def clear(self):
        self._visits.clear()


class DashboardView(QWidget):
    """学期概览 - 首页仪表盘"""

    def __init__(self, session=None):
        super().__init__()
        self.session = session
        self._ui_config = get_config()
        self._kpi_labels = {}  # 存储 KPI 数值标签引用
        self._recent_visits = RecentVisitsManager(max_items=5)
        self._build_ui()

    def _build_ui(self):
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(16, 16, 16, 16)
        self._main_layout.setSpacing(16)

        # 标题行
        header = QHBoxLayout()
        title = QLabel("学期概览")
        title.setFont(font(18, True))
        title.setStyleSheet(f"color: {C['text']};")
        header.addWidget(title)
        header.addStretch()
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {C["accent_blue"]}; color: white; border: none;
                           border-radius: 4px; padding: 6px 16px; font-size: 9pt; }}
            QPushButton:hover {{ background: #2f89c9; }}
        """)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        self._main_layout.addLayout(header)

        # KPI 卡片行
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)
        self._kpi_labels = {}
        for key, title, color in [
            ("students", "在校学生", C["accent_blue"]),
            ("classes", "班级数", C["accent_green"]),
            ("subjects", "科目数", C["accent_orange"]),
            ("exams", "本学期考试", C["accent_purple"]),
        ]:
            card, val_label = self._create_kpi_card(key, title, "0", color)
            kpi_layout.addWidget(card)
            self._kpi_labels[key] = val_label
        self._main_layout.addLayout(kpi_layout)

        # 学期进度 + 快捷操作
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(16)

        # 学期进度卡片
        progress_card = QFrame()
        progress_card.setStyleSheet(f"""
            QFrame {{ background: {C["white"]}; border: 1px solid {C["line"]}; border-radius: 8px; padding: 16px; }}
        """)
        pc_layout = QVBoxLayout(progress_card)
        pc_layout.setSpacing(10)

        prog_title = QLabel("学期进度")
        prog_title.setFont(font(14, True))
        prog_title.setStyleSheet(f"color: {C['text']};")
        pc_layout.addWidget(prog_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(62)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {C["line"]};
                border-radius: 4px;
                background: {C["bg_light"]};
                text-align: center;
                font-size: 9pt;
            }}
            QProgressBar::chunk {{
                background: {C["accent_green"]};
                border-radius: 3px;
            }}
        """)
        self.progress_bar.setFixedHeight(20)
        pc_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("第 14 / 22 周（期中考试已完成）")
        self.progress_label.setFont(font(10))
        self.progress_label.setStyleSheet(f"color: {C['text_light']};")
        pc_layout.addWidget(self.progress_label)

        mid_layout.addWidget(progress_card, 1)

        # 快捷操作卡片
        quick_card = QFrame()
        quick_card.setStyleSheet(f"""
            QFrame {{ background: {C["white"]}; border: 1px solid {C["line"]}; border-radius: 8px; padding: 16px; }}
        """)
        qc_layout = QVBoxLayout(quick_card)
        qc_layout.setSpacing(8)

        qc_title = QLabel("快捷操作")
        qc_title.setFont(font(14, True))
        qc_title.setStyleSheet(f"color: {C['text']};")
        quick_card_layout = qc_layout

        # 快捷操作按钮网格
        btn_grid = QGridLayout()
        btn_grid.setSpacing(8)
        actions = [
            ("＋ 录入成绩", "score_entry", C["accent_blue"]),
            ("＋ 新生注册", "student_register", C["accent_green"]),
            ("＋ 新建考试", "exam_manage", C["accent_orange"]),
            ("⇧ 班级名单", "student_list", C["accent_blue"]),
            ("⇩ 导出成绩单", "score_stats", C["accent_purple"]),
            ("＋ 增开班级", "class_list", C["accent_green"]),
        ]
        for i, (text, view_id, color) in enumerate(actions):
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {color}; color: white; border: none;
                               border-radius: 6px; padding: 10px; font-size: 9pt; }}
                QPushButton:hover {{ opacity: 0.9; }}
            """)
            btn.clicked.connect(lambda checked, vid=view_id: self._navigate(vid))
            row, col = divmod(i, 3)
            btn_grid.addWidget(btn, row, col, 1, 1, Qt.Alignment(Qt.AlignHCenter | Qt.AlignVCenter))

        mid_layout.addWidget(quick_card, 1)

        self._main_layout.addLayout(mid_layout)

        # 最近访问
        recent_card = QFrame()
        recent_card.setStyleSheet(f"""
            QFrame {{ background: {C["white"]}; border: 1px solid {C["line"]}; border-radius: 8px; padding: 16px; }}
        """)
        rc_layout = QVBoxLayout(recent_card)
        rc_layout.setSpacing(10)

        rc_title = QLabel("最近访问")
        rc_title.setFont(font(14, True))
        rc_title.setStyleSheet(f"color: {C['text']};")
        rc_layout.addWidget(rc_title)

        self.recent_list = QVBoxLayout()
        rc_layout.addLayout(self.recent_list)

        self._main_layout.addWidget(recent_card)

        # 待办 / 数据状态
        todo_card = QFrame()
        todo_card.setStyleSheet(f"""
            QFrame {{ background: {C["white"]}; border: 1px solid {C["line"]}; border-radius: 8px; padding: 16px; }}
        """)
        tc_layout = QVBoxLayout(todo_card)
        tc_layout.setSpacing(10)

        todo_title = QLabel("待办 / 数据状态")
        todo_title.setFont(font(14, True))
        todo_title.setStyleSheet(f"color: {C['text']};")
        self._main_layout.addWidget(todo_title)

        self.todo_table = self._create_todo_table()
        tc_layout.addWidget(self.todo_table)

        self._main_layout.addWidget(todo_card)

        self.load_data()

    def _create_kpi_card(self, key: str, title: str, value: str, color: str):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background: {color}; border-radius: 8px; padding: 16px; color: white; }}
        """)
        layout = QVBoxLayout()
        layout.setSpacing(4)

        val = QLabel(value)
        val.setFont(font(28, True))
        val.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        val.setStyleSheet("color: white;")
        val.setObjectName(f"kpi_{key}")
        layout.addWidget(val)

        lbl = QLabel(title)
        lbl.setFont(font(11))
        lbl.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        lbl.setStyleSheet("color: rgba(255,255,255,0.9);")
        layout.addWidget(lbl)

        layout.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        card.setLayout(layout)
        card.setFixedSize(200, 100)

        # 返回卡片和数值标签引用
        val_label = card.findChild(QLabel, f"kpi_{key}")
        return card, val

    def _create_todo_table(self):
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["事项", "状态", "截止"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {C["line"]};
                border-radius: 6px;
                gridline-color: {C["line"]};
                alternate-background-color: {C["bg_light"]};
            }}
            QHeaderView::section {{
                background: {C["line"]}; font-weight: bold; padding: 8px; border: none;
            }}
        """)
        return table

    def load_data(self):
        if not self.session:
            return

        # 统计数据
        try:
            student_count = self.session.query(func.count(Student.id)).scalar() or 0
            class_count = self.session.query(func.count(Class.id)).scalar() or 0
            subject_count = 10  # 暂时硬编码
            exam_count = (
                self.session.query(func.count(Exam.id))
                .filter(Exam.semester_id == self._get_current_semester_id())
                .scalar()
                or 0
            )

            if "students" in self._kpi_labels:
                self._kpi_labels["students"].setText(str(student_count))
            if "classes" in self._kpi_labels:
                self._kpi_labels["classes"].setText(str(class_count))
            if "subjects" in self._kpi_labels:
                self._kpi_labels["subjects"].setText(str(subject_count))
            if "exams" in self._kpi_labels:
                self._kpi_labels["exams"].setText(str(exam_count))
        except Exception:
            pass

        # 进度条
        self.progress_bar.setValue(62)
        self.progress_label.setText("第 14 / 22 周（期中考试已完成）")

        # 待办表格
        self.todo_table.setRowCount(4)
        todos = [
            ("期末成绩未录入 (1班)", "待录入", "今天"),
            ("学籍变动待审批", "等待", "2 天后"),
            ("考试成绩单待打印", "待处理", "3 天后"),
            ("本学期数据已锁定", "已锁定", "—"),
        ]
        for row, (item, status, deadline) in enumerate(todos):
            self.todo_table.setItem(row, 0, QTableWidgetItem(item))
            self.todo_table.setItem(row, 1, QTableWidgetItem(status))
            self.todo_table.setItem(row, 2, QTableWidgetItem(deadline))

    def _get_current_semester_id(self):
        if self.session:
            sem = self.session.query(Semester).filter_by(is_current=True).first()
            if sem:
                return sem.id
        return 1

    def refresh(self):
        self.load_data()

    def _navigate(self, view_id: str):
        from edu_system.gui.views.registry import build_view

        if self.session:
            view = build_view(view_id, self.session)
            # TODO: 实际导航逻辑
            print(f"Navigate to: {view_id}")

        # 记录访问
        for domain in self._ui_config.domains_parsed:
            for tab in domain["tabs"]:
                tab_view = tab.view if hasattr(tab, "view") else tab["view"]
                tab_title = tab.title if hasattr(tab, "title") else tab["title"]
                if tab_view == view_id:
                    self._recent_visits.add_visit(view_id, tab_title)
                    break
        self._update_recent_list()

    def _update_recent_list(self):
        """更新最近访问列表显示"""
        # 清空现有列表
        while self.recent_list.count():
            item = self.recent_list.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        recent = self._recent_visits.get_recent(5)
        if not recent:
            empty_lbl = QLabel("暂无最近访问记录")
            empty_lbl.setFont(font(10))
            empty_lbl.setStyleSheet(f"color: {C['text_light']};")
            empty_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            self.recent_list.addWidget(empty_lbl)
            return

        for item in recent:
            btn = QPushButton(item["title"])
            btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {C["text"]}; border: none;
                               border-radius: 4px; padding: 8px 12px; font-size: 10pt; text-align: left; }}
                QPushButton:hover {{ background: {C["bg_light"]}; color: {C["accent_blue"]}; }}
            """)
            btn.clicked.connect(lambda checked, vid=item["view_id"]: self._navigate(vid))
            self.recent_list.addWidget(btn)


class QuickActionsView(QWidget):
    """快捷操作视图"""

    def __init__(self, session=None):
        super().__init__()
        self.session = session
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        title = QLabel("快捷操作")
        title.setFont(font(18, True))
        title.setStyleSheet(f"color: {C['text']};")
        self.layout().addWidget(title)

        empty = QLabel("快捷操作面板 - 待实现")
        empty.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        empty.setFont(font(14))
        empty.setStyleSheet(f"color: {C['text_light']};")
        self.layout().addWidget(empty)


class DataStatusView(QWidget):
    """待办/数据状态视图"""

    def __init__(self, session=None):
        super().__init__()
        self.session = session
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        title = QLabel("待办 / 数据状态")
        title.setFont(font(18, True))
        title.setStyleSheet(f"color: {C['text']};")
        self.layout().addWidget(title)

        empty = QLabel("数据状态面板 - 待实现")
        empty.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        empty.setFont(font(14))
        empty.setStyleSheet(f"color: {C['text_light']};")
        self.layout().addWidget(empty)
