"""
GUI 视图 — 学期设置 (PyQt5 科学版)
Tab 设计：当前概览 / 学期列表 / 新建
"""

from datetime import datetime

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from edu_system.gui.theme import C, font
from edu_system.models import Semester, SemesterStatus, Student


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


class SemesterView(QWidget):
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
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        # 工具栏
        tb = QHBoxLayout()
        tb.setSpacing(4)
        tb.addWidget(QLabel("学期设置"))
        tb.addStretch()
        lay.addLayout(tb)

        cur = self.session.query(Semester).filter_by(is_active=True).first()

        # ── 当前学期卡片 ──
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            f"background: white; border: 2px solid {C['accent_green']}; "
            "border-radius: 6px; padding: 10px;"
        )
        cl = QVBoxLayout(card)
        cl.setSpacing(3)
        if cur:
            cl.addWidget(QLabel(f"当前学期: {cur.display_label}"))
            # 直接统计在校生总数（不按semester_id，因为导入数据可能不匹配）
            total = self.session.query(Student).filter(Student.status == "在校").count()
            cl.addWidget(QLabel(f"在校学生: {total}人"))
        else:
            cl.addWidget(QLabel("未设置当前学期"))
        lay.addWidget(card)

        # ── Tab ──
        tabs = QTabWidget()
        tabs.setFont(font(9))
        tabs.addTab(self._build_list_tab(cur), "学期列表")
        tabs.addTab(self._build_create_tab(cur), "新建学期")
        tabs.addTab(self._build_inherit_tab(), "继承配置")
        tabs.addTab(self._build_version_tab(), "版本历史")
        lay.addWidget(tabs)

    # ═══════════════════════════════════
    #  Tab 1: 学期列表
    # ═══════════════════════════════════

    def _build_list_tab(self, cur):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        semesters = (
            self.session.query(Semester).order_by(Semester.year_start.desc(), Semester.id).all()
        )
        t = QTableWidget(len(semesters), 4)
        t.setHorizontalHeaderLabels(["学年度", "学期", "状态", "操作"])
        t.setFont(font(9))
        t.verticalHeader().hide()
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setStyleSheet(
            """QTableWidget { font-size:9pt; border:1px solid #DDD;
            background:white; alternate-background-color:#EBF5FB; }
            QHeaderView::section { background:#D9E1F2; font-weight:bold;
            padding:4px; border:1px solid #CCC; }"""
        )

        for i, sem in enumerate(semesters):
            t.setItem(i, 0, QTableWidgetItem(f"{sem.year_start}-{sem.year_start + 1}"))
            t.setItem(i, 1, QTableWidgetItem(sem.semester))

            # 状态列
            if sem.is_active:
                it = QTableWidgetItem("★ 当前")
                it.setForeground(QColor(C["accent_green"]))
            elif sem.status == SemesterStatus.archived:
                it = QTableWidgetItem("已归档")
                it.setForeground(QColor("#999"))
            else:
                it = QTableWidgetItem(
                    sem.status.value if hasattr(sem.status, "value") else sem.status
                )
            t.setItem(i, 2, it)

            # 操作列
            op = QWidget()
            op_ly = QHBoxLayout(op)
            op_ly.setContentsMargins(0, 0, 0, 0)
            if not sem.is_active:
                b = QPushButton("切换至此")
                b.setStyleSheet(
                    f"background:{C['accent_green']}; color:white; font-size:8pt; "
                    "border:none; border-radius:2px; padding:2px 4px;"
                )
                b.clicked.connect(lambda _, sid=sem.id: self._set_current(sid))
                op_ly.addWidget(b)
                b2 = QPushButton("编辑")
                b2.setStyleSheet(
                    "background:#3498DB; color:white; font-size:8pt; "
                    "border:none; border-radius:2px; padding:2px 4px;"
                )
                b2.clicked.connect(lambda _, s=sem: self._edit_semester(s))
                op_ly.addWidget(b2)
                if sem.status != SemesterStatus.archived:
                    b3 = QPushButton("归档")
                    b3.setStyleSheet(
                        "background:#95A5A6; color:white; font-size:8pt; "
                        "border:none; border-radius:2px; padding:2px 4px;"
                    )
                    b3.clicked.connect(lambda _, s=sem: self._archive_semester(s))
                    op_ly.addWidget(b3)
            op_ly.addStretch()
            t.setCellWidget(i, 3, op)
            t.setRowHeight(i, 30)
        lay.addWidget(t)
        return w

    def _edit_semester(self, sem):
        """编辑学期日期（不改变学年/学期名）"""
        dlg = QDialog(self)
        dlg.setWindowTitle(f"编辑 - {sem.display_label}")
        fl = QFormLayout(dlg)
        ds = QDateEdit(QDate(sem.start_date) if sem.start_date else QDate.currentDate())
        ds.setCalendarPopup(True)
        fl.addRow("开始日期:", ds)
        de = QDateEdit(QDate(sem.end_date) if sem.end_date else QDate.currentDate())
        de.setCalendarPopup(True)
        fl.addRow("结束日期:", de)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        fl.addRow(bb)
        if dlg.exec_():
            sem.start_date = ds.date().toPyDate()
            sem.end_date = de.date().toPyDate()
            self.session.commit()
            self._rebuild()

    def _archive_semester(self, sem):
        """归档学期（不删除，仅标记）"""
        ans = QMessageBox.question(
            self,
            "确认归档",
            f"归档 '{sem.display_label}'？\n归档后该学期不再出现在活跃列表中，但所有数据保留。",
        )
        if ans == QMessageBox.Yes:
            sem.status = SemesterStatus.archived
            sem.is_active = False
            self.session.commit()
            self._rebuild()

    # ═══════════════════════════════════
    #  Tab 2: 新建学期
    # ═══════════════════════════════════

    def _build_create_tab(self, cur):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        cy = datetime.now().year
        grp = QGroupBox("新建学期")
        grp.setFont(font(10, True))
        gl = QVBoxLayout(grp)
        gl.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.addWidget(QLabel("起始年:"))
        start_y = QSpinBox()
        start_y.setRange(1990, cy + 10)
        start_y.setValue(cy)
        start_y.setFont(font(9))
        start_y.setFixedWidth(80)
        row1.addWidget(start_y)
        end_label = QLabel(f"— {cy + 1}学年")
        row1.addWidget(end_label)
        start_y.valueChanged.connect(lambda v: end_label.setText(f"— {v + 1}学年"))
        row1.addWidget(QLabel("学期:"))
        sc = QComboBox()
        sc.addItems(["第一学期", "第二学期"])
        sc.setFont(font(9))
        row1.addWidget(sc)
        row1.addStretch()
        gl.addLayout(row1)

        row3 = QHBoxLayout()
        row3.setSpacing(6)
        info_label = QLabel("")
        info_label.setFont(font(8))
        info_label.setStyleSheet("color:#666;")
        row3.addWidget(info_label)
        row3.addStretch()

        b = QPushButton("创建学期并设为当前")
        b.setStyleSheet(
            f"""
            QPushButton {{ background: {C["accent_green"]}; color: white; border: none;
                border-radius: 4px; padding: 8px 20px; font-size: 10pt; font-weight: bold; }}
            QPushButton:hover {{ background: #27AE60; }}
        """
        )
        b.setCursor(Qt.PointingHandCursor)
        b.setMinimumHeight(36)
        b.clicked.connect(lambda: self._create(start_y.value(), sc.currentText(), info_label))
        row3.addWidget(b)
        gl.addLayout(row3)
        lay.addWidget(grp)

        # 关联信息
        if cur:
            grp2 = QGroupBox("关联操作")
            grp2.setFont(font(10, True))
            g2l = QVBoxLayout(grp2)
            g2l.setSpacing(4)
            g2l.addWidget(
                QLabel(
                    f"当前: {cur.display_label}  ({cur.semester})\n"
                    f"新建第二学期 → 同学年，不升年级\n"
                    f"新建第一学期 → 跨学年，自动提示升年级"
                )
            )
            lay.addWidget(grp2)
        lay.addStretch()
        return w

    # ═══════════════════════════════════
    #  Tab 3: 继承配置向导（M5-C1）
    # ═══════════════════════════════════

    def _build_inherit_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        grp = QGroupBox("从历史学期继承配置")
        grp.setFont(font(10, True))
        gl = QVBoxLayout(grp)
        gl.setSpacing(6)

        # 选择源学期 + 目标学期
        sems = self.session.query(Semester).order_by(Semester.year_start.desc(), Semester.id).all()
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(QLabel("源学期:"))
        src_cb = QComboBox()
        for s in sems:
            src_cb.addItem(f"{s.display_label}", s.id)
        src_cb.setFont(font(9))
        src_cb.setMinimumWidth(160)
        row.addWidget(src_cb)
        row.addWidget(QLabel("→ 目标学期:"))
        tgt_cb = QComboBox()
        for s in sems:
            tgt_cb.addItem(f"{s.display_label}", s.id)
        tgt_cb.setFont(font(9))
        tgt_cb.setMinimumWidth(160)
        row.addWidget(tgt_cb)
        row.addStretch()
        gl.addLayout(row)

        # 预览按钮
        b = QPushButton("预览差异（四色）")
        b.setStyleSheet(
            f"""
            QPushButton {{ background: {C["accent_blue"]}; color: white; border: none;
                border-radius: 4px; padding: 6px 16px; font-size: 9pt; }}
            QPushButton:hover {{ background: #2E86C1; }}
        """
        )
        b.setCursor(Qt.PointingHandCursor)
        gl.addWidget(b)

        # 差异表（四色）
        t = QTableWidget(0, 5)
        t.setHorizontalHeaderLabels(["配置项", "类型", "源值", "目标值", "新值"])
        t.setFont(font(9))
        t.verticalHeader().hide()
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.horizontalHeader().setStretchLastSection(True)
        t.setStyleSheet(
            """QTableWidget { font-size:9pt; border:1px solid #DDD; background:white; }
            QHeaderView::section { background:#D9E1F2; font-weight:bold;
            padding:4px; border:1px solid #CCC; }"""
        )
        t.setMinimumHeight(140)
        gl.addWidget(t)

        # 执行按钮
        exec_row = QHBoxLayout()
        exec_row.setSpacing(6)
        info_label = QLabel("")
        info_label.setFont(font(8))
        info_label.setStyleSheet("color:#666;")
        exec_row.addWidget(info_label)
        exec_row.addStretch()
        run_b = QPushButton("确认继承")
        run_b.setStyleSheet(
            f"""
            QPushButton {{ background: {C["accent_green"]}; color: white; border: none;
                border-radius: 4px; padding: 8px 20px; font-size: 10pt; font-weight: bold; }}
            QPushButton:hover {{ background: #27AE60; }}
        """
        )
        run_b.setCursor(Qt.PointingHandCursor)
        run_b.setMinimumHeight(34)
        run_b.setEnabled(False)
        exec_row.addWidget(run_b)
        gl.addLayout(exec_row)

        lay.addWidget(grp)

        # 四色图例
        legend = QLabel(
            '<span style="color:#22c55e">■ 新增</span> '
            '<span style="color:#3b82f6">■ 修改</span> '
            '<span style="color:#9ca3af">■ 保留</span> '
            '<span style="color:#ef4444">■ 冲突</span>'
        )
        legend.setFont(font(8))
        lay.addWidget(legend)
        lay.addStretch()

        def _preview():
            src_id = src_cb.currentData()
            tgt_id = tgt_cb.currentData()
            if not src_id or not tgt_id or src_id == tgt_id:
                info_label.setText("请选择不同的源/目标学期")
                return
            from edu_system.services.semester_config import SemesterConfigService

            svc = SemesterConfigService(self.session)
            result = svc.preview_inherit(src_id, tgt_id)
            diffs = result["diffs"]
            t.setRowCount(len(diffs))
            for i, d in enumerate(diffs):
                t.setItem(i, 0, QTableWidgetItem(d["key"]))
                type_it = QTableWidgetItem(d["type"])
                type_it.setForeground(QColor(d["color"]))
                t.setItem(i, 1, type_it)
                t.setItem(i, 2, QTableWidgetItem(str(d.get("source_value") or "")))
                t.setItem(i, 3, QTableWidgetItem(str(d.get("target_value") or "")))
                t.setItem(i, 4, QTableWidgetItem(str(d.get("new_value") or "")))
            stats = result["stats"]
            info_label.setText(
                f"新增 {stats['added']} · 修改 {stats['modified']} · "
                f"保留 {stats['retained']} · 冲突 {stats['conflict']}"
            )
            # 有可继承项（非全保留）才可执行
            run_b.setEnabled(stats["total"] > 0)

        def _run():
            src_id = src_cb.currentData()
            tgt_id = tgt_cb.currentData()
            from edu_system.services.semester_config import SemesterConfigService

            svc = SemesterConfigService(self.session)
            r = svc.execute_inherit(src_id, tgt_id, operator="admin")
            if r["success"]:
                QMessageBox.information(
                    self,
                    "继承完成",
                    f"{r['message']}\\n\\n继承配置后目标学期值已更新，历史版本可回滚。",
                )
                info_label.setText(r["message"])
                run_b.setEnabled(False)
            else:
                QMessageBox.warning(self, "继承失败", r.get("error", "未知错误"))

        b.clicked.connect(lambda: _preview())
        run_b.clicked.connect(lambda: _run())
        return w

    def _create(self, start_yr, term, info_lbl):
        from edu_system.services.semester import SemesterService

        if not start_yr:
            QMessageBox.warning(self, "错误", "请选择学年度")
            return
        svc = SemesterService(self.session)
        try:
            old = self.session.query(Semester).filter_by(is_active=True).first()
            sem = svc.create(start_yr, term)
            self.session.commit()
            svc.set_current(sem.id)
            self.session.commit()

            if old:
                self._personnel_change_wizard(old, sem, term)
            else:
                QMessageBox.information(
                    self,
                    "初始学期",
                    f"第一个学期: {sem.display_label}\n请依次操作: 导入学生 → 分配教师任课 → 配置教室",
                )

            m = self.window()
            if hasattr(m, "_update_semester_display"):
                m._update_semester_display()
            self._rebuild()
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def _personnel_change_wizard(self, old, sem, term):
        """人员变动引导——跨学年全量/同学年增补"""
        from edu_system.models import Classroom, ClassSubject, Grade
        from edu_system.services.enrollment import EnrollmentService

        is_cross = (
            old.semester == "第二学期" and term == "第一学期" and sem.year_start > old.year_start
        )

        # ── 统计数据 ──
        grade_counts = []
        for g in self.session.query(Grade).order_by(Grade.sort_order).all():
            cnt = self.session.execute(
                text(
                    "SELECT COUNT(*) FROM students s JOIN classes c ON s.class_id=c.id "
                    "WHERE c.grade_id=:gid AND s.status='在校'"
                ),
                {"gid": g.id},
            ).fetchone()[0]
            grade_counts.append(f"{g.name}:{cnt}人")
        teacher_cs = self.session.query(ClassSubject).filter_by(semester_id=old.id).count()
        classroom_cs = self.session.query(Classroom).filter_by(semester_id=old.id).count()

        if is_cross:
            # ══════════════════════════════
            # 跨学年：全量变更引导
            # ══════════════════════════════
            pv = EnrollmentService(self.session).promote_summary(old)

            msg = (
                f"══ 跨学年人员变动总览 ══\n"
                f"{old.display_label} → {sem.display_label}\n\n"
                f"当前学生: {' / '.join(grade_counts)}\n"
                f"已分配教师任课: {teacher_cs}条\n"
                f"已配置教室: {classroom_cs}间\n\n"
                f"【将自动执行】\n"
                f"  1. 学生: 初三毕业({pv['graduated']}人)  初二→初三({pv['to_g3']}人)  初一→初二({pv['to_g2']}人)\n"
                f"  2. 创建新初一空班 101~110\n\n"
                f"【需手动操作】\n"
                f"  3. 教师任课: 全部清空，需重新分配\n"
                f"  4. 教室位置: 全部清空，需重新配置\n"
                f"  5. 导入新生: 将摇号结果导入初一各班\n"
                f"  6. 重排座号: 各班按拼音重新生成\n\n"
                f"确认执行第1-2步(自动)？"
            )

            ans = QMessageBox.question(
                self, "人员变动 — 跨学年", msg, QMessageBox.Yes | QMessageBox.No
            )
            if ans == QMessageBox.Yes:
                # 1. 升年级
                r = EnrollmentService(self.session).promote_grade(sem, old)
                self.session.commit()

                # 2. 清空任课(新学期重新分配)
                self.session.execute(
                    text("DELETE FROM class_subjects WHERE semester_id=:sid"), {"sid": sem.id}
                )
                # 3. 清空教室(新学期重新配置)
                self.session.execute(
                    text("DELETE FROM classrooms WHERE semester_id=:sid"), {"sid": sem.id}
                )
                self.session.commit()

                QMessageBox.information(
                    self,
                    "自动操作完成",
                    f"毕业: {r['graduated']}人\n"
                    f"升初三: {r['to_g3']}人\n"
                    f"升初二: {r['to_g2']}人\n"
                    f"新班: {r['new_classes']}间\n"
                    f"备份: {r['backup']}\n\n"
                    "接下来请依次:\n"
                    "  ① 新生注册(导入摇号学生)\n"
                    "  ② 教师任课(重新分配)\n"
                    "  ③ 教室位置(重新配置)\n"
                    "  ④ 重排座号",
                )

        else:
            # ══════════════════════════════
            # 同学年：增补式变更
            # ══════════════════════════════
            mvs = self.session.execute(
                text("SELECT COUNT(*) FROM student_movements WHERE semester_id=:sid"),
                {"sid": old.id},
            ).fetchone()[0]

            msg = (
                f"══ 同学年人员变动 ══\n"
                f"{old.display_label} → {sem.display_label}\n\n"
                f"当前学生: {' / '.join(grade_counts)}\n"
                f"本学期学籍变动: {mvs}条\n"
                f"教师任课: {teacher_cs}条(保留)\n"
                f"教室位置: {classroom_cs}间(保留)\n\n"
                f"【通常仅需处理】\n"
                f"  个别转学/休复学 → 学籍变动\n"
                f"  个别教师调整 → 教师任课\n\n"
                f"学生结构不变，任课和教室自动保留。"
            )
            QMessageBox.information(self, "人员变动 — 同学年", msg)

    def _set_current(self, sid):
        from edu_system.services.semester import SemesterService

        SemesterService(self.session).set_current(sid)
        self.session.commit()
        m = self.window()
        if hasattr(m, "_update_semester_display"):
            m._update_semester_display()
        self._rebuild()

    # ═══════════════════════════════════
    #  Tab 4: 版本历史 (M5-C2)
    # ═══════════════════════════════════

    def _build_version_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        # 学期选择
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(QLabel("选择学期:"))
        sem_cb = QComboBox()
        semesters = (
            self.session.query(Semester).order_by(Semester.year_start.desc(), Semester.id).all()
        )
        for s in semesters:
            sem_cb.addItem(f"{s.display_label}", s.id)
        sem_cb.setFont(font(9))
        sem_cb.setMinimumWidth(200)
        row.addWidget(sem_cb)
        row.addStretch()
        lay.addLayout(row)

        # 版本列表
        t = QTableWidget(0, 5)
        t.setHorizontalHeaderLabels(["版本", "时间", "操作者", "配置项数", "操作"])
        t.setFont(font(9))
        t.verticalHeader().hide()
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.horizontalHeader().setStretchLastSection(True)
        t.setStyleSheet(
            """QTableWidget { font-size:9pt; border:1px solid #DDD; background:white; alternate-background-color:#EBF5FB; }
            QHeaderView::section { background:#D9E1F2; font-weight:bold; padding:4px; border:1px solid #CCC; }"""
        )
        t.setMinimumHeight(200)
        lay.addWidget(t)

        # 刷新按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        refresh_btn = QPushButton("刷新版本列表")
        refresh_btn.setStyleSheet(
            f"""
            QPushButton {{ background: {C["accent_blue"]}; color: white; border: none;
                border-radius: 4px; padding: 6px 16px; font-size: 9pt; }}
            QPushButton:hover {{ background: #2E86C1; }}
            """
        )
        refresh_btn.setCursor(Qt.PointingHandCursor)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # 详情区
        detail_label = QLabel("选择版本查看配置详情")
        detail_label.setFont(font(8))
        detail_label.setStyleSheet("color:#666;")
        lay.addWidget(detail_label)

        detail_text = QTextEdit()
        detail_text.setFont(font(8))
        detail_text.setReadOnly(True)
        detail_text.setMaximumHeight(150)
        detail_text.setStyleSheet("border:1px solid #DDD; background:#FAFAFA;")
        lay.addWidget(detail_text)

        def load_versions():
            sem_id = sem_cb.currentData()
            if not sem_id:
                return
            from edu_system.services.semester_config import SemesterConfigService

            svc = SemesterConfigService(self.session)
            try:
                versions = svc.get_versions(sem_id)
                t.setRowCount(len(versions))
                for i, v in enumerate(versions):
                    t.setItem(i, 0, QTableWidgetItem(str(v["version"])))
                    t.setItem(i, 1, QTableWidgetItem(v["created_at"] or ""))
                    t.setItem(i, 2, QTableWidgetItem(v["created_by"] or ""))
                    t.setItem(i, 3, QTableWidgetItem(str(v["config_count"])))

                    # 回滚按钮
                    rollback_btn = QPushButton("回滚")
                    rollback_btn.setStyleSheet(
                        "background:#E74C3C; color:white; font-size:8pt; "
                        "border:none; border-radius:2px; padding:2px 8px;"
                    )
                    rollback_btn.setCursor(Qt.PointingHandCursor)
                    rollback_btn.clicked.connect(
                        lambda _, ver=v["version"]: do_rollback(sem_id, ver)
                    )
                    t.setCellWidget(i, 4, rollback_btn)
                t.setColumnWidth(0, 60)
                t.setColumnWidth(1, 140)
                t.setColumnWidth(2, 100)
                t.setColumnWidth(3, 80)
                detail_label.setText(f"共 {len(versions)} 个版本")
                detail_text.clear()
            except Exception as e:
                QMessageBox.warning(self, "加载失败", str(e))

        def do_rollback(sem_id, version):
            from PyQt5.QtWidgets import QMessageBox

            ans = QMessageBox.question(
                self,
                "确认回滚",
                f"确定要回滚到版本 {version} 吗？\n这将创建一个新版本并覆盖当前配置。",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return

            from edu_system.services.semester_config import SemesterConfigService

            svc = SemesterConfigService(self.session)
            try:
                result = svc.rollback_to_version(sem_id, version, operator="admin")
                if result.get("success"):
                    QMessageBox.information(
                        self,
                        "回滚完成",
                        f"{result['message']}\n\n新版本: v{result['new_version']}\n配置项: {result['config_count']}",
                    )
                    load_versions()
                else:
                    QMessageBox.warning(self, "回滚失败", result.get("error", "未知错误"))
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

        refresh_btn.clicked.connect(lambda: load_versions())
        sem_cb.currentIndexChanged.connect(lambda: load_versions())

        # 初始加载
        load_versions()

        return w

    # ═══════════════════════════════════
    #  升年级已移至 PromotionView（学生管理工作台）
    # ═══════════════════════════════════
