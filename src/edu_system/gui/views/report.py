"""
GUI 视图 — 统计报表（PyQt5）

Tab 设计：
1. 报表生成：考试标准报表 / 学籍变动情况表 / 成绩单 / 证书奖状
2. 模板管理：报表模板注册、版本列表、回滚、变量扫描（M6 Sprint6）
3. 批量打印：批量生成成绩单 + ZIP 打包（M6 Sprint6）
"""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from edu_system.gui.theme import C, font
from edu_system.models import Exam


def _btn(txt, color, w=None):
    b = QPushButton(txt)
    b.setStyleSheet(
        f"""QPushButton {{ background: {color}; color: white; border: none;
        border-radius: 3px; padding: 6px 14px; font-size: 9pt; }}
        QPushButton:hover {{ background: #34495E; }}"""
    )
    b.setCursor(Qt.PointingHandCursor)
    if w:
        b.setFixedWidth(w)
    return b


class ReportView(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self._build_ui()

    def _build_ui(self):
        if self.layout():
            QWidget().setLayout(self.layout())
        l = QVBoxLayout(self)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(8)

        tb = QHBoxLayout()
        tb.addWidget(QLabel("统计报表"))
        tb.addStretch()
        l.addLayout(tb)

        tabs = QTabWidget()
        tabs.setFont(font(9))
        tabs.addTab(self._build_generate_tab(), "报表生成")
        tabs.addTab(self._build_template_tab(), "模板管理")
        tabs.addTab(self._build_batch_tab(), "批量打印")
        l.addWidget(tabs)

    # ═══════════════════════════════════
    #  Tab 1: 报表生成
    # ═══════════════════════════════════

    def _build_generate_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(8, 8, 8, 8)
        l.setSpacing(8)

        row = QHBoxLayout()
        row.addWidget(self._lbl("选择考试:"))
        self._exam_cb = QComboBox()
        self._exam_cb.setFont(font(9))
        self._exam_cb.setMinimumWidth(320)
        self._reload_exams()
        row.addWidget(self._exam_cb)
        row.addStretch()
        l.addLayout(row)

        btns = QHBoxLayout()
        btns.setSpacing(6)
        for txt, clr, rtype in [
            ("生成成绩报表", C["accent_blue"], "exam"),
            ("生成变动情况表", C["accent_orange"], "movement"),
            ("生成成绩单 Word", C["accent_green"], "card_word"),
            ("生成成绩单 Excel", C["accent_teal"], "card_excel"),
            ("生成奖状", C["accent_purple"], "award"),
            ("生成证书", C["accent_red"], "certificate"),
        ]:
            b = _btn(txt, clr)
            b.clicked.connect(lambda _, t=rtype: self._generate(t))
            btns.addWidget(b)
        btns.addStretch()
        l.addLayout(btns)

        tip = QLabel(
            "成绩单/证书支持批量生成（每人一份或合并单文件）——批量能力见「批量打印」Tab。"
        )
        tip.setFont(font(8))
        tip.setStyleSheet("color:#666;")
        l.addWidget(tip)
        l.addStretch()
        return w

    def _reload_exams(self):
        self._exam_cb.clear()
        exams = self.session.query(Exam).order_by(Exam.id.desc()).all()
        for e in exams:
            grade = e.grade.name if e.grade else ""
            sem = e.semester.label if e.semester else ""
            self._exam_cb.addItem(f"ID{e.id}  {sem}  {grade}  {e.name}", e.id)

    def _generate(self, report_type):
        idx = self._exam_cb.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "提示", "请先创建考试")
            return
        exam_id = self._exam_cb.itemData(idx)

        from edu_system.services.report import ReportService

        svc = ReportService(self.session)

        try:
            if report_type == "exam":
                path, _ = QFileDialog.getSaveFileName(self, "保存报表", "", "Excel (*.xlsx)")
                if not path:
                    return
                svc.generate_exam_report(exam_id, path)
                QMessageBox.information(self, "完成", f"报表已保存到:\n{path}")
            elif report_type == "movement":
                exam = self.session.get(Exam, exam_id)
                path, _ = QFileDialog.getSaveFileName(self, "保存报表", "", "Excel (*.xlsx)")
                if not path:
                    return
                svc.generate_change_report(exam.semester_id if exam else None, path)
                QMessageBox.information(self, "完成", f"变动情况表已保存到:\n{path}")
            elif report_type in ("card_word", "card_excel"):
                out_dir = QFileDialog.getExistingDirectory(self, "选择输出目录")
                if not out_dir:
                    return
                if report_type == "card_word":
                    files = svc.generate_report_cards_word(exam_id, out_dir, single_file=True)
                else:
                    files = svc.generate_report_cards_excel(exam_id, out_dir, single_file=True)
                QMessageBox.information(
                    self, "完成", f"已生成 {len(files)} 个文件:\n{chr(10).join(files)}"
                )
            elif report_type in ("award", "certificate"):
                out_dir = QFileDialog.getExistingDirectory(self, "选择输出目录")
                if not out_dir:
                    return
                files = svc.generate_certificate(
                    exam_id, out_dir, certificate_type=report_type, single_file=True
                )
                QMessageBox.information(
                    self, "完成", f"已生成 {len(files)} 个文件:\n{chr(10).join(files)}"
                )
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    # ═══════════════════════════════════
    #  Tab 2: 模板管理（M6 Sprint6）
    # ═══════════════════════════════════

    def _build_template_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(8, 8, 8, 8)
        l.setSpacing(8)

        # 注册区
        reg_row = QHBoxLayout()
        reg_row.setSpacing(6)
        reg_row.addWidget(self._lbl("模板名:"))
        self._tpl_name = QLineEdit()
        self._tpl_name.setFont(font(9))
        self._tpl_name.setPlaceholderText("如：成绩单模板")
        self._tpl_name.setMinimumWidth(140)
        reg_row.addWidget(self._tpl_name)
        reg_row.addWidget(self._lbl("类型:"))
        self._tpl_type = QComboBox()
        self._tpl_type.setFont(font(9))
        for t in ["excel", "word", "certificate"]:
            self._tpl_type.addItem(t)
        reg_row.addWidget(self._tpl_type)
        reg_btn = _btn("选择文件并注册", C["accent_blue"])
        reg_btn.clicked.connect(self._register_template)
        reg_row.addWidget(reg_btn)
        reg_row.addStretch()
        l.addLayout(reg_row)

        # 模板列表
        self._tpl_table = QTableWidget(0, 5)
        self._tpl_table.setHorizontalHeaderLabels(["模板名", "类型", "版本", "状态", "操作"])
        self._tpl_table.setFont(font(9))
        self._tpl_table.verticalHeader().hide()
        self._tpl_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tpl_table.horizontalHeader().setStretchLastSection(True)
        self._tpl_table.setStyleSheet(
            """QTableWidget { font-size:9pt; border:1px solid #DDD; background:white; }
            QHeaderView::section { background:#D9E1F2; font-weight:bold;
            padding:4px; border:1px solid #CCC; }"""
        )
        self._tpl_table.setMinimumHeight(160)
        l.addWidget(self._tpl_table)

        # 版本/变量区
        ver_row = QHBoxLayout()
        ver_row.setSpacing(6)
        refresh_btn = _btn("刷新列表", C["accent_teal"])
        refresh_btn.clicked.connect(self._load_templates)
        ver_row.addWidget(refresh_btn)
        ver_row.addWidget(self._lbl("变量:"))
        self._var_label = QLabel("（扫描模板文件获取变量）")
        self._var_label.setFont(font(8))
        self._var_label.setStyleSheet("color:#666;")
        ver_row.addWidget(self._var_label)
        ver_row.addStretch()
        l.addLayout(ver_row)

        self._load_templates()
        return w

    def _register_template(self):
        name = self._tpl_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入模板名称")
            return
        ttype = self._tpl_type.currentText()
        path, _ = QFileDialog.getOpenFileName(
            self, "选择模板文件", "", "模板文件 (*.xlsx *.xlsm *.docx)"
        )
        if not path:
            return

        from edu_system.services.report_template import ReportTemplateService

        svc = ReportTemplateService(self.session)
        try:
            # 变量扫描
            vars_found = svc.scan_variables(path)
            tpl = svc.register(
                name=name,
                template_type=ttype,
                file_path=path,
                description=f"从 {Path(path).name} 注册",
                created_by="admin",
                variables=[v["key"] for v in vars_found],
            )
            self._var_label.setText(f"发现 {len(vars_found)} 个变量: {[v['key'] for v in vars_found]}")
            QMessageBox.information(
                self, "注册成功", f"模板 v{tpl.version} 已注册，扫描到 {len(vars_found)} 个变量"
            )
            self._load_templates()
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def _load_templates(self):
        from edu_system.services.report_template import ReportTemplateService

        svc = ReportTemplateService(self.session)
        templates = svc.list_all()
        self._tpl_table.setRowCount(len(templates))
        for i, t in enumerate(templates):
            self._tpl_table.setItem(i, 0, QTableWidgetItem(t["name"]))
            self._tpl_table.setItem(i, 1, QTableWidgetItem(t["template_type"]))
            self._tpl_table.setItem(i, 2, QTableWidgetItem(f"v{t['version']}"))
            self._tpl_table.setItem(
                i, 3, QTableWidgetItem("启用" if t["is_active"] else "停用")
            )
            # 操作：版本历史 + 回滚
            op = QWidget()
            op_ly = QHBoxLayout(op)
            op_ly.setContentsMargins(0, 0, 0, 0)
            hist_btn = QPushButton("版本")
            hist_btn.setStyleSheet(
                "background:#3498DB; color:white; font-size:8pt; "
                "border:none; border-radius:2px; padding:2px 8px;"
            )
            hist_btn.clicked.connect(lambda _, n=t["name"]: self._show_versions(n))
            op_ly.addWidget(hist_btn)
            op_ly.addStretch()
            self._tpl_table.setCellWidget(i, 4, op)

    def _show_versions(self, name):
        from edu_system.services.report_template import ReportTemplateService

        svc = ReportTemplateService(self.session)
        versions = svc.get_versions(name)
        lines = []
        for v in versions:
            lines.append(
                f"v{v['version']}  {'★当前' if v['is_active'] else '历史'}  "
                f"{v['description'] or ''}  {v['created_at'] or ''}"
            )

        # 提供回滚按钮
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout as _V

        dlg = QDialog(self)
        dlg.setWindowTitle(f"版本历史 - {name}")
        dl = _V(dlg)
        info = QLabel("\n".join(lines))
        info.setFont(font(9))
        info.setWordWrap(True)
        dl.addWidget(info)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("回滚到最新")
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        dl.addWidget(bb)
        dlg.resize(420, 260)

        if dlg.exec_() == QDialog.Accepted and versions:
            latest = versions[0]
            try:
                svc.rollback_to(name, latest["version"])
                QMessageBox.information(self, "完成", f"已回滚到 v{latest['version']}")
                self._load_templates()
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    # ═══════════════════════════════════
    #  Tab 3: 批量打印（M6 Sprint6）
    # ═══════════════════════════════════

    def _build_batch_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(8, 8, 8, 8)
        l.setSpacing(8)

        row = QHBoxLayout()
        row.addWidget(self._lbl("选择考试:"))
        self._batch_exam_cb = QComboBox()
        self._batch_exam_cb.setFont(font(9))
        self._batch_exam_cb.setMinimumWidth(320)
        exams = self.session.query(Exam).order_by(Exam.id.desc()).all()
        for e in exams:
            grade = e.grade.name if e.grade else ""
            sem = e.semester.label if e.semester else ""
            self._batch_exam_cb.addItem(f"ID{e.id}  {sem}  {grade}  {e.name}", e.id)
        row.addWidget(self._batch_exam_cb)
        row.addStretch()
        l.addLayout(row)

        btns = QHBoxLayout()
        btns.setSpacing(6)
        gen_btn = _btn("批量生成成绩单（ZIP）", C["accent_green"])
        gen_btn.clicked.connect(self._batch_generate)
        btns.addWidget(gen_btn)
        print_btn = _btn("打印文档", C["accent_blue"])
        print_btn.clicked.connect(self._print_document)
        btns.addWidget(print_btn)
        btns.addStretch()
        l.addLayout(btns)

        self._batch_progress = QProgressBar()
        self._batch_progress.setFont(font(8))
        self._batch_progress.setRange(0, 100)
        self._batch_progress.setValue(0)
        l.addWidget(self._batch_progress)

        self._batch_log = QTextEdit()
        self._batch_log.setFont(font(8))
        self._batch_log.setReadOnly(True)
        self._batch_log.setStyleSheet("border:1px solid #DDD; background:#FAFAFA;")
        self._batch_log.setMaximumHeight(120)
        l.addWidget(self._batch_log)
        return w

    def _batch_generate(self):
        idx = self._batch_exam_cb.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "提示", "请先创建考试")
            return
        exam_id = self._batch_exam_cb.itemData(idx)
        out_dir = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if not out_dir:
            return

        from edu_system.services.report import ReportService
        from edu_system.services.report_worker import ReportBatchWorker

        svc = ReportService(self.session)
        # 每人一份（single_file=False）→ 批量 Worker
        students, subjects, configs = svc.score_svc.get_exam_scores(exam_id)
        ranked = svc.score_svc.calc_grade_ranks(exam_id)
        if not ranked:
            QMessageBox.warning(self, "提示", "该考试暂无学生成绩")
            return

        self._batch_progress.setValue(0)
        self._batch_log.append(f"开始批量生成 {len(ranked)} 份成绩单...")

        # 批量生成：单文件模式生成全部 → Worker 打包 ZIP
        def render_all(_):
            svc.generate_report_cards_word(exam_id, out_dir, single_file=True)

        worker = ReportBatchWorker()
        worker.start(
            items=[1],
            render_fn=render_all,
            out_dir=out_dir,
            progress_cb=lambda p, m: (
                self._batch_progress.setValue(p),
                self._batch_log.append(m),
            ),
            finished_cb=self._batch_finished,
            error_cb=lambda item, err: self._batch_log.append(f"失败: {err}"),
            zip_name="report_cards.zip",
        )

    def _batch_finished(self, result):
        if result.get("cancelled"):
            self._batch_log.append("已取消")
            return
        self._batch_log.append(
            f"完成: 生成 {result.get('generated', 0)} 份，失败 {result.get('failed', 0)} 份"
        )
        if result.get("zip_path"):
            self._batch_log.append(f"ZIP: {result['zip_path']}")
        self._batch_progress.setValue(100)

    def _print_document(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择要打印的文档", "", "文档 (*.docx *.xlsx *.pdf)"
        )
        if not path:
            return
        from edu_system.services.report import PrintService

        svc = PrintService(self.session)
        ok = svc.print_document(path)
        if ok:
            QMessageBox.information(self, "完成", "已提交打印")
        else:
            QMessageBox.warning(self, "提示", "打印失败或系统无打印机")

    def _lbl(self, t):
        l = QLabel(t)
        l.setFont(font(9))
        return l
