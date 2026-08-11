"""GUI 视图 — 学籍变动 / 新生注册 / 升年级 (统一风格)"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from edu_system.gui.theme import C, font
from edu_system.models import Class as ClassModel
from edu_system.models import Semester, Student, StudentMovement
from edu_system.services.enrollment import EnrollmentService


def _btn(txt, color, w=None):
    from edu_system.gui.components import btn

    return btn(txt, color, w)

class EnrollmentView(QWidget):
    """学籍变动：批量转班向导 + 单项操作 + 变动记录"""

    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self._selected_students = []  # 选中的学生
        self._build_ui()
        self._refresh_log()

    def refresh(self):
        self._refresh_log()

    def _build_ui(self):
        if self.layout():
            QWidget().setLayout(self.layout())
        self.setLayout(QVBoxLayout())
        lay = self.layout()
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(4)

        # 顶部工具栏
        tb = QHBoxLayout()
        tb.setSpacing(4)
        tb.addWidget(QLabel("学籍变动"))
        tb.addStretch()
        # 批量转班向导入口
        b_wizard = _btn("批量转班向导", C["accent_green"], 100)
        b_wizard.clicked.connect(self._open_batch_transfer_wizard)
        tb.addWidget(b_wizard)
        lay.addLayout(tb)

        # 搜索栏
        row = QHBoxLayout()
        row.setSpacing(3)
        row.addWidget(QLabel("搜索学生:"))
        self._search = QLineEdit()
        self._search.setFont(font(9))
        self._search.setPlaceholderText("输入姓名/学籍号/身份证/电话...")
        row.addWidget(self._search)
        b = _btn("查找", C["accent_blue"], 50)
        b.clicked.connect(self._search_student)
        row.addWidget(b)
        row.addSpacing(8)
        # 批量操作按钮
        b_sel_all = _btn("全选", C["accent_orange"], 60)
        b_sel_all.clicked.connect(self._select_all)
        row.addWidget(b_sel_all)
        b_clear = _btn("清空", C["accent_orange"], 60)
        b_clear.clicked.connect(self._clear_selection)
        row.addWidget(b_clear)
        row.addStretch()
        lay.addLayout(row)
        self._search.returnPressed.connect(self._search_student)

        # 学生列表（支持多选、复选框）
        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.MultiSelection)
        self._list.setAlternatingRowColors(True)
        self._list.setFont(font(9))
        self._list.setStyleSheet(
            """QListWidget { font-size:9pt; border:1px solid #DDD;
            background:white; alternate-background-color:#EBF5FB; }
            QListWidget::item { padding:4px 8px; }
            QListWidget::item:selected { background:#3498DB; color:white; }"""
        )
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        lay.addWidget(self._list, 1)

        # 底部状态栏
        status_row = QHBoxLayout()
        self._sel_label = QLabel("已选: 0 人")
        self._sel_label.setFont(font(9))
        status_row.addWidget(self._sel_label)
        status_row.addStretch()
        # 单项操作
        for txt, color, tip in [
            ("批量转班", C["accent_green"], "为选中学生批量转班"),
            ("批量休学", C["accent_orange"], "将选中学生设为休学"),
            ("批量复学", C["accent_green"], "将选中学生设为在校"),
            ("导出名单", C["accent_blue"], "导出选中学生名单"),
        ]:
            b = _btn(txt, color, 80)
            b.setToolTip(tip)
            b.clicked.connect(lambda _, t=txt: self._batch_action(t))
            status_row.addWidget(b)
        status_row.addStretch()
        lay.addLayout(status_row)

        # 最近变动记录
        lay.addWidget(QLabel("最近变动记录:"))
        self._log_table = QTableWidget(0, 5)
        self._log_table.setHorizontalHeaderLabels(["日期", "学生", "类型", "详情", "原因"])
        self._log_table.setFont(font(9))
        self._log_table.verticalHeader().hide()
        self._log_table.setAlternatingRowColors(True)
        self._log_table.horizontalHeader().setStretchLastSection(True)
        self._log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._log_table.setStyleSheet(
            """QTableWidget { font-size:9pt; border:1px solid #DDD;
            background:white; alternate-background-color:#EBF5FB; }
            QHeaderView::section { background: {C["table_header_bg"]}; font-weight:bold; padding:3px;
            border:1px solid {C["table_header_border"]}; }"""
        )
        lay.addWidget(self._log_table)
        self._refresh_log()

    def _search_student(self):
        kw = self._search.text().strip()
        if not kw:
            return
        students = (
            self.session.query(Student)
            .filter(
                Student.name.like(f"%{kw}%")
                | Student.student_code.like(f"%{kw}%")
                | Student.id_card.like(f"%{kw}%")
                | Student.phone.like(f"%{kw}%")
            )
            .limit(100)
            .all()
        )
        self._list.clear()
        for stu in students:
            cn = stu.class_.name if stu.class_ else "?"
            item = QListWidgetItem(f"{stu.name} | {cn} | {stu.student_code} | {stu.status}")
            item.setData(Qt.UserRole, stu.id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self._list.addItem(item)

    def _on_selection_changed(self):
        self._selected_students = [
            self._list.item(i).data(Qt.UserRole)
            for i in range(self._list.count())
            if self._list.item(i).isSelected()
        ]
        self._sel_label.setText(f"已选: {len(self._selected_students)} 人")

    def _select_all(self):
        for i in range(self._list.count()):
            self._list.item(i).setSelected(True)

    def _clear_selection(self):
        self._list.clearSelection()

    def _batch_action(self, action_name):
        if not self._selected_students:
            QMessageBox.information(self, "提示", "请先选择学生")
            return
        ids = self._selected_students
        if action_name == "批量转班":
            self._batch_transfer(ids)
        elif action_name == "批量休学":
            self._batch_change_status(ids, "休学")
        elif action_name == "批量复学":
            self._batch_change_status(ids, "在校")
        elif action_name == "导出名单":
            self._export_selected(ids)

    def _batch_transfer(self, student_ids):
        names = [c.name for c in self.session.query(ClassModel).order_by(ClassModel.name).all()]
        target, ok = QInputDialog.getItem(
            self, "批量转班", f"将 {len(student_ids)} 名学生转到:", names, 0, False
        )
        if not ok:
            return
        cls = self.session.query(ClassModel).filter_by(name=target).first()
        if not cls:
            return
        svc = EnrollmentService(self.session)
        progress = QProgressDialog("正在转班...", "取消", 0, len(student_ids), self)
        progress.setWindowModality(Qt.WindowModal)
        success = 0
        for i, sid in enumerate(student_ids):
            if progress.wasCanceled():
                break
            progress.setValue(i)
            try:
                svc.transfer(sid, cls.id, "批量转班")
                success += 1
            except Exception:
                pass
        progress.setValue(len(student_ids))
        self.session.commit()
        QMessageBox.information(self, "完成", f"成功转班 {success} 人")
        self._refresh_log()
        self._search_student()

    def _batch_change_status(self, student_ids, status):
        svc = EnrollmentService(self.session)
        success = 0
        for sid in student_ids:
            try:
                svc.change_status(sid, status, f"批量{status}")
                success += 1
            except Exception:
                pass
        self.session.commit()
        QMessageBox.information(self, "完成", f"成功修改 {success} 人状态为 {status}")
        self._refresh_log()
        self._search_student()

    def _export_selected(self, student_ids):
        from openpyxl import Workbook

        path, _ = QFileDialog.getSaveFileName(self, "保存", "选中学生名单.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        wb = Workbook(write_only=True)
        ws = wb.create_sheet("学生名单")
        ws.append(["姓名", "性别", "班级", "学籍号", "身份证", "电话", "状态"])
        for sid in student_ids:
            stu = self.session.get(Student, sid)
            if stu:
                ws.append(
                    [
                        stu.name,
                        stu.gender,
                        stu.class_name,
                        stu.student_code,
                        stu.id_card,
                        stu.phone,
                        stu.status,
                    ]
                )
        wb.save(path)
        QMessageBox.information(self, "完成", f"已导出 {len(student_ids)} 人")

    def _refresh_log(self):
        moves = (
            self.session.query(StudentMovement)
            .order_by(StudentMovement.created_at.desc())
            .limit(30)
            .all()
        )
        self._log_table.setRowCount(len(moves))
        for i, m in enumerate(moves):
            stu = self.session.get(Student, m.student_id)
            self._log_table.setItem(i, 0, QTableWidgetItem(str(m.move_date or "")[:10]))
            self._log_table.setItem(i, 1, QTableWidgetItem(stu.name if stu else "?"))
            self._log_table.setItem(i, 2, QTableWidgetItem(m.move_type))
            self._log_table.setItem(i, 3, QTableWidgetItem(f"{m.from_class_id}→{m.to_class_id}"))
            self._log_table.setItem(i, 4, QTableWidgetItem(m.reason or ""))

    def _open_batch_transfer_wizard(self):
        """打开转班向导对话框：选学生→目标班→预览→执行"""
        dlg = BatchTransferWizard(self, self.session)
        dlg.exec_()
        self._search_student()
        self._refresh_log()


class RegistrationView(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self._build_ui()

    def _build_ui(self):
        if self.layout():
            QWidget().setLayout(self.layout())
        self.setLayout(QVBoxLayout())
        lay = self.layout()
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        tb = QHBoxLayout()
        tb.addWidget(QLabel("新生注册"))
        tb.addStretch()
        lay.addLayout(tb)

        lay.addWidget(QLabel("从摇号结果Excel导入初一级学生并自动分班"))
        b = QPushButton("选择摇号文件并导入")
        b.setStyleSheet(
            f"background:{C['accent_red']}; color:white; border:none; border-radius:4px; padding:8px 16px; font-size:10pt;"
        )
        b.clicked.connect(self._import)
        lay.addWidget(b)
        lay.addStretch()

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择摇号结果", "", "Excel (*.xlsx *.xls)")
        if not path:
            return
        from edu_system.services.importer import ImportService

        result = ImportService(self.session).import_students_from_excel(path)
        self.session.commit()
        QMessageBox.information(self, "导入结果", result.summary)


class PromotionView(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self._build_ui()

    def refresh(self):
        self._build_ui()

    def _build_ui(self):
        if self.layout():
            QWidget().setLayout(self.layout())
        self.setLayout(QVBoxLayout())
        lay = self.layout()
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        # 工具栏
        tb = QHBoxLayout()
        tb.setSpacing(4)
        tb.addWidget(QLabel("升年级/毕业"))
        tb.addStretch()
        lay.addLayout(tb)

        cur = self.session.query(Semester).filter_by(is_active=True).first()
        old = None
        if cur:
            old = (
                self.session.query(Semester)
                .filter(Semester.id != cur.id, Semester.year_start < cur.year_start)
                .order_by(Semester.year_start.desc())
                .first()
            )

        # 当前学生分布
        grp = QGroupBox("当前学生分布")
        grp.setFont(font(10, True))
        gl = QVBoxLayout(grp)
        gl.setSpacing(2)
        from edu_system.models import Grade

        for g in self.session.query(Grade).order_by(Grade.sort_order).all():
            cnt = self.session.execute(
                text(
                    "SELECT COUNT(*) FROM students s JOIN classes c ON s.class_id=c.id "
                    "WHERE c.grade_id=:gid AND s.status='在校'"
                ),
                {"gid": g.id},
            ).fetchone()[0]
            gl.addWidget(QLabel(f"  {g.name}: {cnt} 人在校"))
        lay.addWidget(grp)

        # 操作
        ops = QFrame()
        ops.setFrameShape(QFrame.StyledPanel)
        ops.setStyleSheet(
            "background: white; border: 1px solid #DDD; border-radius: 4px; padding: 10px;"
        )
        ol = QVBoxLayout(ops)
        ol.setSpacing(6)
        ol.addWidget(
            QLabel(
                "升年级将执行:\n"
                "  初三 → 毕业(状态改毕业，班级保留)\n"
                "  初二 → 初三(class_id 2xx→3xx)\n"
                "  初一 → 初二(class_id 1xx→2xx)\n"
                "  创建新初一空班(101~110)"
            )
        )
        if cur and old:
            ol.addWidget(QLabel(f"从 {old.label} → {cur.label}"))

        b = QPushButton("执行升年级向导")
        b.setStyleSheet(
            f"background:{C['accent_red']}; color:white; border:none; "
            "border-radius: 4px; padding: 10px 20px; font-size: 10pt; font-weight: bold;"
        )
        b.clicked.connect(self._run_promotion_wizard)
        ol.addWidget(b)
        lay.addWidget(ops)
        lay.addStretch()

    def _run_promotion_wizard(self):
        """运行升年级向导：预览 → 备份 → 执行 → 报表"""
        from edu_system.services.enrollment import PromotionWizard

        wizard = PromotionWizard(self.session)
        success, result = wizard.run()

        if success:
            QMessageBox.information(
                self,
                "升年级完成",
                f"毕业: {result['graduated']}  升初三: {result['to_g3']}  "
                f"升初二: {result['to_g2']}  新班: {result['new_classes']}班\n"
                f"备份: {result.get('backup', '')}",
            )
            self._build_ui()
        else:
            QMessageBox.critical(self, "失败", result.get("error", "未知错误"))


class BatchTransferWizard(QDialog):
    """转班向导：选学生 → 目标班 → 预览 → 执行"""

    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("批量转班向导")
        self.setMinimumSize(700, 500)
        self._step = 1
        self._selected_ids = []
        self._target_class = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 步骤指示
        self._step_labels = []
        step_bar = QHBoxLayout()
        for i, step_text in enumerate(["1. 选学生", "2. 目标班", "3. 预览", "4. 执行"]):
            lbl = QLabel(step_text)
            lbl.setFont(font(9))
            lbl.setStyleSheet("color: #999;")
            step_bar.addWidget(lbl)
            self._step_labels.append(lbl)
        step_bar.addStretch()
        layout.addLayout(step_bar)

        # 内容区
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        # Step 1: 选学生
        self._page1 = QWidget()
        p1 = QVBoxLayout(self._page1)
        p1.addWidget(QLabel("选择要转班的学生（可多选）"))
        self._wizard_search = QLineEdit()
        self._wizard_search.setPlaceholderText("搜索姓名/学籍号/身份证/电话...")
        self._wizard_search.textChanged.connect(self._wizard_search_students)
        p1.addWidget(self._wizard_search)
        self._wizard_list = QListWidget()
        self._wizard_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self._wizard_list.setAlternatingRowColors(True)
        p1.addWidget(self._wizard_list, 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        b_next = _btn("下一步 →", C["accent_green"], 80)
        b_next.clicked.connect(lambda: self._goto_step(2))
        btn_row.addWidget(b_next)
        p1.addLayout(btn_row)
        self._stack.addWidget(self._page1)

        # Step 2: 目标班
        self._page2 = QWidget()
        p2 = QVBoxLayout(self._page2)
        p2.addWidget(QLabel("选择目标班级"))
        self._wizard_class_cb = QComboBox()
        self._wizard_class_cb.setFont(font(9))
        classes = self.session.query(ClassModel).order_by(ClassModel.name).all()
        for c in classes:
            self._wizard_class_cb.addItem(c.name, c.id)
        p2.addWidget(self._wizard_class_cb)
        p2.addStretch()
        btn_row = QHBoxLayout()
        b_back = _btn("← 上一步", C["accent_orange"], 80)
        b_back.clicked.connect(lambda: self._goto_step(1))
        btn_row.addStretch()
        b_next = _btn("下一步 →", C["accent_green"], 80)
        b_next.clicked.connect(lambda: self._goto_step(3))
        btn_row.addWidget(b_back)
        btn_row.addWidget(b_next)
        p2.addLayout(btn_row)
        self._stack.addWidget(self._page2)

        # Step 3: 预览
        self._page3 = QWidget()
        p3 = QVBoxLayout(self._page3)
        p3.addWidget(QLabel("预览转班结果"))
        self._preview_table = QTableWidget(0, 4)
        self._preview_table.setHorizontalHeaderLabels(["姓名", "当前班级", "目标班级", "状态"])
        self._preview_table.horizontalHeader().setStretchLastSection(True)
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        p3.addWidget(self._preview_table)
        btn_row = QHBoxLayout()
        b_back = _btn("← 上一步", C["accent_orange"], 80)
        b_back.clicked.connect(lambda: self._goto_step(2))
        btn_row.addStretch()
        b_exec = _btn("执行转班", C["accent_red"], 80)
        b_exec.clicked.connect(self._execute_transfer)
        btn_row.addWidget(b_back)
        btn_row.addWidget(b_exec)
        p3.addLayout(btn_row)
        self._stack.addWidget(self._page3)

        # Step 4: 结果（在 accept
        self._page4 = QWidget()
        p4 = QVBoxLayout(self._page4)
        self._result_label = QLabel("")
        self._result_label.setAlignment(Qt.AlignCenter)
        self._result_label.setFont(font(11, True))
        p4.addStretch()
        p4.addWidget(self._result_label)
        p4.addStretch()
        self._stack.addWidget(self._page4)

        self._stack.setCurrentIndex(0)
        self._update_step_indicator()

        # 底部按钮栏
        bottom = QHBoxLayout()
        bottom.addStretch()
        b_close = _btn("关闭", "gray", 80)
        b_close.clicked.connect(self.accept)
        bottom.addWidget(b_close)
        layout.addLayout(bottom)

        self._load_students()

    def _load_students(self):
        students = self.session.query(Student).filter(Student.status == "在校").all()
        for stu in students:
            cn = stu.class_.name if stu.class_ else "?"
            item = QListWidgetItem(f"{stu.name} | {cn} | {stu.student_code}")
            item.setData(Qt.UserRole, stu.id)
            self._wizard_list.addItem(item)

    def _wizard_search_students(self):
        kw = self._wizard_search.text().strip()
        self._wizard_list.clear()
        if not kw:
            self._load_students()
            return
        students = (
            self.session.query(Student)
            .filter(
                Student.name.like(f"%{kw}%")
                | Student.student_code.like(f"%{kw}%")
                | Student.id_card.like(f"%{kw}%")
                | Student.phone.like(f"%{kw}%")
            )
            .filter(Student.status == "在校")
            .all()
        )
        for stu in students:
            cn = stu.class_.name if stu.class_ else "?"
            item = QListWidgetItem(f"{stu.name} | {cn} | {stu.student_code}")
            item.setData(Qt.UserRole, stu.id)
            self._wizard_list.addItem(item)

    def _goto_step(self, step):
        if step == 3:
            self._build_preview()
        self._step = step
        self._stack.setCurrentIndex(step - 1)
        self._update_step_indicator()

    def _update_step_indicator(self):
        for i, lbl in enumerate(self._step_labels):
            if i + 1 == self._step:
                lbl.setStyleSheet("color: #3498DB; font-weight: bold;")
            elif i + 1 < self._step:
                lbl.setStyleSheet("color: #27AE60;")
            else:
                lbl.setStyleSheet("color: #999;")

    def _build_preview(self):
        self._selected_ids = [
            self._wizard_list.item(i).data(Qt.UserRole)
            for i in range(self._wizard_list.count())
            if self._wizard_list.item(i).isSelected()
        ]
        self._target_class = self._wizard_class_cb.currentData()
        self._preview_table.setRowCount(0)
        target_name = self._wizard_class_cb.currentText()
        for sid in self._selected_ids:
            stu = self.session.get(Student, sid)
            if stu:
                cn = stu.class_.name if stu.class_ else "?"
                row = self._preview_table.rowCount()
                self._preview_table.insertRow(row)
                self._preview_table.setItem(row, 0, QTableWidgetItem(stu.name))
                self._preview_table.setItem(row, 1, QTableWidgetItem(cn))
                self._preview_table.setItem(row, 2, QTableWidgetItem(target_name))
                self._preview_table.setItem(row, 3, QTableWidgetItem("待转入"))

    def _execute_transfer(self):
        if not self._selected_ids or not self._target_class:
            QMessageBox.warning(self, "提示", "请先完成前面步骤")
            return
        svc = EnrollmentService(self.session)
        progress = QProgressDialog("正在转班...", "取消", 0, len(self._selected_ids), self)
        progress.setWindowModality(Qt.WindowModal)
        success = 0
        for i, sid in enumerate(self._selected_ids):
            if progress.wasCanceled():
                break
            progress.setValue(i)
            try:
                svc.transfer(sid, self._target_class, "向导批量转班")
                success += 1
            except Exception:
                pass
        progress.setValue(len(self._selected_ids))
        self.session.commit()
        self._result_label.setText(f"完成！成功转班 {success} 人")
        self._goto_step(4)
