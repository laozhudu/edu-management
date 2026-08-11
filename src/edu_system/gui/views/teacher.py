"""
GUI 视图 — 教师任课 (PyQt5 统一风格)
Tab 设计：教师列表 / 任课分配 / 任课查询
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from edu_system.gui.theme import TABLE_STYLE, C, font
from edu_system.models import Class as ClassModel
from edu_system.models import ClassSubject, Grade, Semester, Subject, Teacher


def _btn(txt, color, w=None):
    from edu_system.gui.components import btn

    return btn(txt, color, w)

class TeacherView(QWidget):
    def __init__(self, session: Session, view_id: str = "teacher_list"):
        super().__init__()
        self.session = session
        self.view_id = view_id
        self._tabs = None
        self._build_ui()
        # teacher_assign → 定位任课分配 Tab（index 1）
        if self._tabs is not None and view_id == "teacher_assign":
            self._tabs.setCurrentIndex(1)

    def refresh(self):
        self._refresh()

    def _build_ui(self):
        self._outer = QVBoxLayout()
        self._outer.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._outer)
        self._refresh()

    def _refresh(self):
        while self._outer.count():
            self._outer.takeAt(0).widget().deleteLater()
        w = QWidget()
        self._outer.addWidget(w)
        self._build_content(w)

    def _build_content(self, w):
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        # Toolbar
        tb = QHBoxLayout()
        tb.setSpacing(4)
        tb.addWidget(QLabel("教师任课"))
        tb.addStretch()

        b = _btn("刷新", "gray")
        b.clicked.connect(lambda: self._refresh())
        tb.addWidget(b)
        lay.addLayout(tb)

        self._tabs = QTabWidget()
        self._tabs.setFont(font(9))
        self._tabs.addTab(self._build_list_tab(), "教师列表")
        self._tabs.addTab(self._build_assign_tab(), "任课分配")
        self._tabs.addTab(self._build_query_tab(), "任课查询")
        lay.addWidget(self._tabs)

    def _build_list_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        teachers = self.session.query(Teacher).order_by(Teacher.name).all()
        _STATUS_CN = {"active": "在职", "resigned": "离职", "retired": "退休"}
        rows = [
            [
                t.name,
                t.gender,
                t.education,
                t.title,
                t.phone or "",
                _STATUS_CN.get(t.status or "active", "在职"),
            ]
            for t in teachers
        ]
        t = QTableWidget(len(rows), 6)
        t.setHorizontalHeaderLabels(["姓名", "性别", "学历", "职称", "电话", "状态"])
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                t.setItem(i, j, QTableWidgetItem(str(v)))
        t.verticalHeader().hide()
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setFont(font(9))
        t.setStyleSheet(TABLE_STYLE)
        # 列配置持久化（跨设备同步）
        from edu_system.gui.components import TablePrefsService

        self._teacher_prefs = TablePrefsService(self.session, "teacher_list")
        self._teacher_prefs.restore(t)
        t.horizontalHeader().sectionResized.connect(lambda *_: self._teacher_prefs.save(t))
        lay.addWidget(t)
        return w

    def _build_assign_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        cur = self.session.query(Semester).filter_by(is_active=True).first()
        if not cur:
            lay.addWidget(QLabel("请先设置当前学期"))
            return w

        grp = QGroupBox("任课分配")
        grp.setFont(font(10, True))
        gl = QVBoxLayout(grp)
        gl.setSpacing(6)

        # 行1: 年级/班级/科目/教师
        row = QHBoxLayout()
        row.setSpacing(6)

        row.addWidget(QLabel("年级:"))
        g_cb = QComboBox()
        g_cb.setFont(font(9))
        g_cb.setFixedWidth(100)
        for g in self.session.query(Grade).order_by(Grade.sort_order).all():
            g_cb.addItem(g.name, g.id)
        row.addWidget(g_cb)

        row.addWidget(QLabel("班级:"))
        c_cb = QComboBox()
        c_cb.setFont(font(9))
        c_cb.setFixedWidth(100)
        row.addWidget(c_cb)

        row.addWidget(QLabel("科目:"))
        s_cb = QComboBox()
        s_cb.setFont(font(9))
        s_cb.setFixedWidth(120)
        for sub in self.session.query(Subject).order_by(Subject.sort_order).all():
            s_cb.addItem(sub.name, sub.id)
        row.addWidget(s_cb)

        row.addWidget(QLabel("教师:"))
        t_cb = QComboBox()
        t_cb.setFont(font(9))
        t_cb.setFixedWidth(120)
        for t in self.session.query(Teacher).order_by(Teacher.name).all():
            t_cb.addItem(t.name, t.id)
        row.addWidget(t_cb)

        row.addStretch()
        gl.addLayout(row)

        def update_classes():
            c_cb.clear()
            gid = g_cb.currentData()
            if gid:
                for cls in (
                    self.session.query(ClassModel)
                    .filter_by(grade_id=gid)
                    .order_by(ClassModel.name)
                    .all()
                ):
                    c_cb.addItem(cls.name, cls.id)

        g_cb.currentIndexChanged.connect(update_classes)
        update_classes()
        gl.addSpacing(4)

        def save_assign():
            if not all(
                [g_cb.currentData(), c_cb.currentData(), s_cb.currentData(), t_cb.currentData()]
            ):
                QMessageBox.warning(self, "错误", "请完善所有选择")
                return
            existing = (
                self.session.query(ClassSubject)
                .filter_by(
                    semester_id=cur.id, class_id=c_cb.currentData(), subject_id=s_cb.currentData()
                )
                .first()
            )
            if existing:
                existing.teacher_id = t_cb.currentData()
            else:
                self.session.add(
                    ClassSubject(
                        semester_id=cur.id,
                        class_id=c_cb.currentData(),
                        subject_id=s_cb.currentData(),
                        teacher_id=t_cb.currentData(),
                    )
                )
            self.session.commit()
            QMessageBox.information(self, "完成", "任课分配已保存")
            self._refresh()

        b = _btn("保存分配", C["accent_green"])
        b.clicked.connect(save_assign)
        gl.addWidget(b, alignment=Qt.AlignLeft)

        lay.addWidget(grp)

        # 已分配列表
        grp2 = QGroupBox("已分配任课")
        grp2.setFont(font(10, True))
        g2l = QVBoxLayout(grp2)
        g2l.setSpacing(4)
        assignments = self.session.query(ClassSubject).filter_by(semester_id=cur.id).all()
        rows = []
        for a in assignments:
            cl = self.session.query(ClassModel).get(a.class_id)
            sj = self.session.query(Subject).get(a.subject_id)
            t = self.session.query(Teacher).get(a.teacher_id)
            rows.append([cl.name if cl else "?", sj.name if sj else "?", t.name if t else "—"])
        tbl = QTableWidget(len(rows) if rows else 1, 3)
        tbl.setHorizontalHeaderLabels(["班级", "科目", "教师"])
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                tbl.setItem(i, j, QTableWidgetItem(str(v)))
        tbl.verticalHeader().hide()
        tbl.setAlternatingRowColors(True)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setFont(font(9))
        tbl.setStyleSheet(TABLE_STYLE)
        g2l.addWidget(tbl)
        lay.addWidget(grp2)
        lay.addStretch()
        return w

    def _build_query_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        cur = self.session.query(Semester).filter_by(is_active=True).first()
        if not cur:
            lay.addWidget(QLabel("请先设置当前学期"))
            return w

        # 筛选栏
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(QLabel("年级:"))
        g_cb = QComboBox()
        g_cb.setFont(font(9))
        g_cb.addItem("全部", None)
        for g in self.session.query(Grade).order_by(Grade.sort_order).all():
            g_cb.addItem(g.name, g.id)
        row.addWidget(g_cb)

        row.addWidget(QLabel("教师:"))
        t_cb = QComboBox()
        t_cb.setFont(font(9))
        t_cb.addItem("全部", None)
        for t in self.session.query(Teacher).order_by(Teacher.name).all():
            t_cb.addItem(t.name, t.id)
        row.addWidget(t_cb)

        row.addWidget(QLabel("科目:"))
        s_cb = QComboBox()
        s_cb.setFont(font(9))
        s_cb.addItem("全部", None)
        for sub in self.session.query(Subject).order_by(Subject.sort_order).all():
            s_cb.addItem(sub.name, sub.id)
        row.addWidget(s_cb)

        b = _btn("查询", C["accent_blue"])
        row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)

        # 结果表
        tbl = QTableWidget(0, 5)
        tbl.setHorizontalHeaderLabels(["年级", "班级", "科目", "教师", "学期"])
        tbl.verticalHeader().hide()
        tbl.setAlternatingRowColors(True)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setFont(font(9))
        tbl.setStyleSheet(TABLE_STYLE)

        def do_query():
            q = self.session.query(ClassSubject).filter_by(semester_id=cur.id)
            if g_cb.currentData():
                cls_ids = [
                    c.id
                    for c in self.session.query(ClassModel)
                    .filter_by(grade_id=g_cb.currentData())
                    .all()
                ]
                q = q.filter(ClassSubject.class_id.in_(cls_ids))
            if t_cb.currentData():
                q = q.filter(ClassSubject.teacher_id == t_cb.currentData())
            if s_cb.currentData():
                q = q.filter(ClassSubject.subject_id == s_cb.currentData())
            assignments = q.all()
            rows = []
            for a in assignments:
                cl = self.session.query(ClassModel).get(a.class_id)
                sj = self.session.query(Subject).get(a.subject_id)
                t = self.session.query(Teacher).get(a.teacher_id)
                rows.append(
                    [
                        cl.grade.name if cl and cl.grade else "?",
                        cl.name if cl else "?",
                        sj.name if sj else "?",
                        t.name if t else "—",
                        cur.label,
                    ]
                )
            tbl.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, v in enumerate(row):
                    tbl.setItem(i, j, QTableWidgetItem(str(v)))

        b.clicked.connect(do_query)
        lay.addWidget(tbl)
        lay.addStretch()
        return w
