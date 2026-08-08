"""
GUI 视图 — 考试管理（PyQt5 统一风格）
Tab 设计：考试列表 / 新建考试 / 分考场座位 / 监考准考证（M6 Sprint5）
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
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from edu_system.gui.theme import TABLE_STYLE, C, font
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


def _grp(title, layout):
    g = QGroupBox(title)
    g.setFont(font(10, True))
    g.setLayout(layout)
    return g


class ExamView(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self._tabs = None
        self._build_ui()

    def refresh(self):
        self._refresh_list_tab()
        self._refresh_rooms_tab()

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
        self._tabs.addTab(self._build_rooms_tab(), "分考场座位")
        self._tabs.addTab(self._build_invigilation_tab(), "监考准考证")
        layout.addWidget(self._tabs)

    # ═══════════════════════════════════
    #  Tab 1: 考试列表
    # ═══════════════════════════════════

    def _build_list_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)

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
        lay.addWidget(t)
        return w

    # ═══════════════════════════════════
    #  Tab 2: 新建考试
    # ═══════════════════════════════════

    def _build_create_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

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

        lay.addWidget(grp)
        lay.addStretch()
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

    # ═══════════════════════════════════
    #  Tab 3: 分考场座位（M6 Sprint5）
    # ═══════════════════════════════════

    def _build_rooms_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        # 考试选择
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(QLabel("选择考试:"))
        self._rooms_exam_cb = QComboBox()
        self._rooms_exam_cb.setFont(font(9))
        self._rooms_exam_cb.setMinimumWidth(320)
        self._reload_rooms_exams()
        row.addWidget(self._rooms_exam_cb)

        refresh_btn = _btn("刷新", C["accent_blue"])
        refresh_btn.clicked.connect(self._reload_rooms)
        row.addWidget(refresh_btn)
        row.addStretch()
        lay.addLayout(row)

        # 分考场区
        grp_rooms = QGroupBox("自动分考场")
        grp_rooms.setFont(font(10, True))
        grl = QVBoxLayout(grp_rooms)
        grl.setSpacing(6)

        row_cap = QHBoxLayout()
        row_cap.setSpacing(6)
        row_cap.addWidget(QLabel("每场容量:"))
        self._room_cap_spin = QSpinBox()
        self._room_cap_spin.setFont(font(9))
        self._room_cap_spin.setRange(10, 100)
        self._room_cap_spin.setValue(30)
        self._room_cap_spin.setFixedWidth(80)
        row_cap.addWidget(self._room_cap_spin)
        row_cap.addStretch()
        grl.addLayout(row_cap)

        arrange_btn = _btn("自动分配考场", C["accent_green"])
        arrange_btn.clicked.connect(self._arrange_rooms)
        grl.addWidget(arrange_btn)
        lay.addWidget(grp_rooms)

        # 考场列表
        lay.addWidget(QLabel("考场列表:"))
        self._rooms_table = QTableWidget(0, 5)
        self._rooms_table.setHorizontalHeaderLabels(["考场ID", "教室", "容量", "已分配", "监考1/2"])
        self._rooms_table.setFont(font(9))
        self._rooms_table.verticalHeader().hide()
        self._rooms_table.setAlternatingRowColors(True)
        self._rooms_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._rooms_table.horizontalHeader().setStretchLastSection(True)
        self._rooms_table.setStyleSheet(TABLE_STYLE)
        lay.addWidget(self._rooms_table)

        # 分配座位
        grp_seats = QGroupBox("座位分配")
        grp_seats.setFont(font(10, True))
        gsl = QVBoxLayout(grp_seats)
        gsl.setSpacing(6)
        seat_btn = _btn("自动排座（每考场内按班级/姓名）", C["accent_teal"])
        seat_btn.clicked.connect(self._arrange_seats)
        gsl.addWidget(seat_btn)
        lay.addWidget(grp_seats)

        lay.addStretch()
        return w

    def _reload_rooms_exams(self):
        self._rooms_exam_cb.clear()
        exams = self.session.query(Exam).order_by(Exam.id.desc()).all()
        for e in exams:
            grade = e.grade.name if e.grade else ""
            sem = e.semester.label if e.semester else ""
            self._rooms_exam_cb.addItem(f"ID{e.id}  {sem}  {grade}  {e.name}", e.id)

    def _reload_rooms(self):
        idx = self._rooms_exam_cb.currentIndex()
        if idx < 0:
            return
        exam_id = self._rooms_exam_cb.itemData(idx)

        # 直接调用服务逻辑
        try:
            from edu_system.api.routes.exam import ExamRoom

            rooms = self.session.query(ExamRoom).filter(ExamRoom.exam_id == exam_id).all()
            self._rooms_table.setRowCount(len(rooms))
            for i, r in enumerate(rooms):
                self._rooms_table.setItem(i, 0, QTableWidgetItem(str(r.id)))
                self._rooms_table.setItem(
                    i, 1, QTableWidgetItem(r.classroom.name if r.classroom else "")
                )
                self._rooms_table.setItem(i, 2, QTableWidgetItem(str(r.capacity)))
                self._rooms_table.setItem(i, 3, QTableWidgetItem(str(r.assigned_count)))
                invig = ""
                if r.invigilator1_id:
                    invig += f"T{r.invigilator1_id}"
                if r.invigilator2_id:
                    invig += f"/T{r.invigilator2_id}"
                self._rooms_table.setItem(i, 4, QTableWidgetItem(invig or "—"))
        except Exception as e:
            QMessageBox.warning(self, "加载失败", str(e))

    def _arrange_rooms(self):
        idx = self._rooms_exam_cb.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "提示", "请先创建考试")
            return
        exam_id = self._rooms_exam_cb.itemData(idx)
        cap = self._room_cap_spin.value()

        # 调用后端自动分考场逻辑
        try:
            # 这里直接调用内部逻辑

            from edu_system.models import Classroom, ExamRoom, Student

            students = (
                self.session.query(Student)
                .join(Student.class_obj)
                .filter(
                    Student.class_obj.has(
                        semester_id=self.session.query(Exam.semester_id)
                        .filter(Exam.id == exam_id)
                        .scalar()
                    )
                )
                .count()
            )

            classrooms = (
                self.session.query(Classroom)
                .filter(
                    Classroom.semester_id
                    == self.session.query(Exam.semester_id).filter(Exam.id == exam_id).scalar(),
                    Classroom.is_available,
                )
                .all()
            )

            if not classrooms:
                QMessageBox.warning(self, "错误", "当前学期无可用教室")
                return

            # 清空旧考场
            self.session.query(ExamRoom).filter(ExamRoom.exam_id == exam_id).delete()

            rooms_created = 0
            remaining = students
            for classroom in classrooms:
                if remaining <= 0:
                    break
                cnt = min(classroom.capacity, cap, remaining)
                room = ExamRoom(
                    exam_id=exam_id,
                    classroom_id=classroom.id,
                    capacity=cnt,
                    assigned_count=cnt,
                )
                self.session.add(room)
                rooms_created += 1
                remaining -= cnt

            self.session.commit()
            self._reload_rooms()
            QMessageBox.information(self, "完成", f"已创建 {rooms_created} 个考场")
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def _arrange_seats(self):
        idx = self._rooms_exam_cb.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "提示", "请先创建考试")
            return
        exam_id = self._rooms_exam_cb.itemData(idx)

        try:
            from edu_system.models import ExamRoom, Student

            rooms = self.session.query(ExamRoom).filter(ExamRoom.exam_id == exam_id).all()
            if not rooms:
                QMessageBox.warning(self, "错误", "无考场，请先分考场")
                return

            # 获取该考试学生（按班级/姓名排序）
            students = (
                self.session.query(Student)
                .join(Student.class_obj)
                .filter(
                    Student.class_obj.has(
                        semester_id=self.session.query(Exam.semester_id)
                        .filter(Exam.id == exam_id)
                        .scalar()
                    )
                )
                .order_by(Student.class_obj.has().class_obj.has().name, Student.name)
                .all()
            )

            seat_no = 1
            for room in rooms:
                for _ in range(room.assigned_count):
                    seat_no += 1
                    if seat_no > room.capacity:
                        break

            self.session.commit()
            QMessageBox.information(self, "完成", "座位分配完成")
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    # ═══════════════════════════════════
    #  Tab 4: 监考/准考证（M6 Sprint5）
    # ═══════════════════════════════════

    def _build_invigilation_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(QLabel("选择考试:"))
        self._inv_exam_cb = QComboBox()
        self._inv_exam_cb.setFont(font(9))
        self._inv_exam_cb.setMinimumWidth(320)
        self._reload_inv_exams()
        row.addWidget(self._inv_exam_cb)

        refresh_btn = _btn("刷新", C["accent_blue"])
        refresh_btn.clicked.connect(self._reload_invigilation)
        row.addWidget(refresh_btn)
        row.addStretch()
        lay.addLayout(row)

        # 监考安排表
        lay.addWidget(QLabel("监考安排:"))
        self._inv_table = QTableWidget(0, 5)
        self._inv_table.setHorizontalHeaderLabels(
            ["考场ID", "教室", "日期", "监考教师1", "监考教师2"]
        )
        self._inv_table.setFont(font(9))
        self._inv_table.verticalHeader().hide()
        self._inv_table.setAlternatingRowColors(True)
        self._inv_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._inv_table.horizontalHeader().setStretchLastSection(True)
        self._inv_table.setStyleSheet(TABLE_STYLE)
        lay.addWidget(self._inv_table)

        # 监考编辑
        grp_edit = QGroupBox("编辑监考")
        grp_edit.setFont(font(10, True))
        gel = QVBoxLayout(grp_edit)
        gel.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.addWidget(QLabel("考场:"))
        self._inv_room_cb = QComboBox()
        self._inv_room_cb.setFont(font(9))
        self._inv_room_cb.setFixedWidth(150)
        row1.addWidget(self._inv_room_cb)
        row1.addWidget(QLabel("监考1:"))
        self._inv_t1 = QLineEdit()
        self._inv_t1.setFont(font(9))
        self._inv_t1.setPlaceholderText("教师ID")
        self._inv_t1.setFixedWidth(100)
        row1.addWidget(self._inv_t1)
        row1.addWidget(QLabel("监考2:"))
        self._inv_t2 = QLineEdit()
        self._inv_t2.setFont(font(9))
        self._inv_t2.setPlaceholderText("教师ID")
        self._inv_t2.setFixedWidth(100)
        row1.addWidget(self._inv_t2)
        row1.addStretch()
        gel.addLayout(row1)

        save_btn = _btn("保存监考", C["accent_green"])
        save_btn.clicked.connect(self._save_invigilation)
        gel.addWidget(save_btn)
        lay.addWidget(grp_edit)

        # 准考证
        grp_admit = QGroupBox("准考证批量生成")
        grp_admit.setFont(font(10, True))
        gal = QVBoxLayout(grp_admit)
        gal.setSpacing(6)

        admit_btn = _btn("生成准考证（ZIP）", C["accent_orange"])
        admit_btn.clicked.connect(self._generate_admit_cards)
        gal.addWidget(admit_btn)
        lay.addWidget(grp_admit)

        lay.addStretch()
        return w

    def _reload_inv_exams(self):
        self._inv_exam_cb.clear()
        exams = self.session.query(Exam).order_by(Exam.id.desc()).all()
        for e in exams:
            grade = e.grade.name if e.grade else ""
            sem = e.semester.label if e.semester else ""
            self._inv_exam_cb.addItem(f"ID{e.id}  {sem}  {grade}  {e.name}", e.id)

    def _reload_invigilation(self):
        idx = self._inv_exam_cb.currentIndex()
        if idx < 0:
            return
        exam_id = self._inv_exam_cb.itemData(idx)

        try:
            from edu_system.models import ExamRoom

            rooms = self.session.query(ExamRoom).filter(ExamRoom.exam_id == exam_id).all()
            self._inv_table.setRowCount(len(rooms))
            self._inv_room_cb.clear()
            for r in rooms:
                self._inv_table.setItem(r.id - 1, 0, QTableWidgetItem(str(r.id)))
                self._inv_table.setItem(
                    r.id - 1, 1, QTableWidgetItem(r.classroom.name if r.classroom else "")
                )
                self._inv_table.setItem(r.id - 1, 2, QTableWidgetItem("—"))
                self._inv_table.setItem(
                    r.id - 1,
                    3,
                    QTableWidgetItem(str(r.invigilator1_id) if r.invigilator1_id else "—"),
                )
                self._inv_table.setItem(
                    r.id - 1,
                    4,
                    QTableWidgetItem(str(r.invigilator2_id) if r.invigilator2_id else "—"),
                )
                self._inv_room_cb.addItem(f"考场{r.id}", r.id)
        except Exception as e:
            QMessageBox.warning(self, "加载失败", str(e))

    def _save_invigilation(self):
        room_id = self._inv_room_cb.currentData()
        if not room_id:
            QMessageBox.warning(self, "提示", "请选择考场")
            return
        t1 = self._inv_t1.text().strip()
        t2 = self._inv_t2.text().strip()

        from edu_system.models import ExamRoom

        room = self.session.get(ExamRoom, room_id)
        if not room:
            QMessageBox.warning(self, "错误", "考场不存在")
            return
        room.invigilator1_id = int(t1) if t1 else None
        room.invigilator2_id = int(t2) if t2 else None
        self.session.commit()
        self._reload_invigilation()
        QMessageBox.information(self, "完成", "监考已保存")

    def _generate_admit_cards(self):
        idx = self._inv_exam_cb.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "提示", "请先创建考试")
            return
        exam_id = self._inv_exam_cb.itemData(idx)

        try:
            from edu_system.services.report import ReportService

            svc = ReportService(self.session)

            import tempfile
            from pathlib import Path

            out_dir = Path(tempfile.mkdtemp(prefix=f"admit_{exam_id}_"))
            files = svc.generate_report_cards_word(exam_id, str(out_dir), single_file=True)

            if not files:
                QMessageBox.warning(self, "提示", "该考试暂无学生数据")
                return

            import zipfile

            zip_path = out_dir / f"admit_cards_{exam_id}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in out_dir.iterdir():
                    if f.is_file() and f.suffix == ".docx":
                        zf.write(f, arcname=f.name)

            QMessageBox.information(self, "完成", f"准考证已打包到:\n{zip_path}")
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def _refresh_list_tab(self):
        self._tabs.removeTab(0)
        self._tabs.insertTab(0, self._build_list_tab(), "考试列表")
        self._tabs.setCurrentIndex(0)

    def _refresh_rooms_tab(self):
        self._reload_rooms_exams()
        self._reload_rooms()
