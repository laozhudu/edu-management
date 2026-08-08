"""
导入向导 UI（M5-D2）

五步流程：
1. 选择文件（拖拽文件到区域 / 浏览选择）
2. 字段映射（源列 → 标准字段，自动猜测）
3. 规则预览（清洗后数据表格预览）
4. 验证报告（质量报告 + 错误行明细）
5. 确认入库（事务写入 + 结果报告）

底层调用 ImportExportService（parse_file → apply_mapping → preview → import_rows）。
验收：3000 人 < 2 分钟（服务层性能由 import_rows 决定；UI 无额外开销）。
"""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from edu_system.gui.theme import C, font

# 学生导入标准字段（与数据质量校验对齐）
STUDENT_FIELDS = [
    ("学号", "student_code"),
    ("姓名", "name"),
    ("性别", "gender"),
    ("班级", "class_name"),
    ("联系电话", "phone"),
    ("民族", "ethnicity"),
]


class ImportWizard(QWidget):
    """导入向导：文件 → 映射 → 预览 → 验证 → 入库"""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._df = None
        self._stage = None
        self._file_path = ""
        self._build_ui()

    # ═══════════ UI ═══════════

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        title = QLabel("导入向导")
        title.setFont(font(13, True))
        lay.addWidget(title)

        # ── 第 1 步：选择文件 ──
        self._file_row = QHBoxLayout()
        self._file_label = QLabel("未选择文件")
        self._file_label.setStyleSheet(
            f"border: 2px dashed {C['line']}; border-radius: 6px;"
            f"padding: 24px; color: {C['text_light']}; font-size: 10pt;"
        )
        self._file_label.setAlignment(Qt.AlignCenter)
        self._file_label.setMinimumHeight(80)
        self._file_label.setAcceptDrops(True)
        self._file_label.mousePressEvent = lambda e: self._browse_file()
        self._file_row.addWidget(self._file_label, 1)
        lay.addLayout(self._file_row)

        btn_row = QHBoxLayout()
        browse_btn = QPushButton("浏览选择文件")
        browse_btn.clicked.connect(self._browse_file)
        btn_row.addWidget(browse_btn)
        self.load_btn = QPushButton("解析文件")
        self.load_btn.clicked.connect(self._parse_file)
        self.load_btn.setEnabled(False)
        btn_row.addWidget(self.load_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # ── 第 2 步：字段映射 ──
        self._map_title = QLabel("字段映射（源列 → 标准字段）")
        self._map_title.setFont(font(10, True))
        self._map_title.hide()
        lay.addWidget(self._map_title)

        self._map_form = QFormLayout()
        self._map_widgets: dict[str, QComboBox] = {}
        for label, key in STUDENT_FIELDS:
            cb = QComboBox()
            cb.addItem("（忽略）", None)
            self._map_widgets[key] = cb
            self._map_form.addRow(f"{label}:", cb)
        lay.addLayout(self._map_form)
        self._map_form.setEnabled(False)

        # ── 第 3 步：预览 ──
        self._preview_title = QLabel("数据预览（清洗后前 50 行）")
        self._preview_title.setFont(font(10, True))
        self._preview_title.hide()
        lay.addWidget(self._preview_title)

        self._preview_table = QTableWidget()
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.setMaximumHeight(220)
        self._preview_table.hide()
        lay.addWidget(self._preview_table)

        # ── 第 4 步：验证报告 ──
        self._report_label = QLabel("")
        self._report_label.setFont(font(9))
        self._report_label.setWordWrap(True)
        self._report_label.hide()
        lay.addWidget(self._report_label)

        # ── 操作 ──
        op_row = QHBoxLayout()
        self.preview_btn = QPushButton("规则预览")
        self.preview_btn.clicked.connect(self._preview)
        self.preview_btn.setEnabled(False)
        op_row.addWidget(self.preview_btn)
        self.import_btn = QPushButton("确认入库")
        self.import_btn.clicked.connect(self._import)
        self.import_btn.setEnabled(False)
        op_row.addWidget(self.import_btn)
        op_row.addStretch()
        lay.addLayout(op_row)

        lay.addStretch()

    # ═══════════ 拖拽 ═══════════

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self._set_file(urls[0].toLocalFile())

    # ═══════════ 步骤实现 ═══════════

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择导入文件", "", "表格文件 (*.xlsx *.xls *.csv);;所有文件 (*)"
        )
        if path:
            self._set_file(path)

    def _set_file(self, path: str):
        self._file_path = path
        self._file_label.setText(f"已选择: {Path(path).name}\n(拖入新文件可替换)")
        self.load_btn.setEnabled(True)

    def _parse_file(self):
        """第 1 步完成：解析文件 → 自动猜测映射"""
        if not self._file_path:
            return
        from edu_system.services.import_export import ImportExportService, ImportFormatError

        try:
            df = ImportExportService.parse_file(self._file_path)
        except ImportFormatError as e:
            QMessageBox.critical(self, "解析失败", str(e))
            return

        self._df = df
        # 填充映射下拉（源列名）
        for key, cb in self._map_widgets.items():
            cb.clear()
            cb.addItem("（忽略）", None)
            for col in df.columns:
                cb.addItem(str(col), str(col))
        # 自动猜测：同名列直接匹配
        for label, key in STUDENT_FIELDS:
            cb = self._map_widgets[key]
            for i in range(cb.count()):
                if cb.itemData(i) == label:
                    cb.setCurrentIndex(i)
                    break

        self._map_form.setEnabled(True)
        self._map_title.show()
        self.preview_btn.setEnabled(True)
        self._preview_title.show()
        self._show_preview(df.head(50))
        QMessageBox.information(
            self, "解析完成", f"共 {len(df)} 行, {len(df.columns)} 列，请确认字段映射"
        )

    def _build_mapping(self) -> dict:
        """收集映射: {标准列名: 源列名}"""
        mapping = {}
        for label, key in STUDENT_FIELDS:
            cb = self._map_widgets[key]
            src = cb.currentData()
            if src:
                mapping[label] = src
        return mapping

    def _preview(self):
        """第 3 步：规则预览（清洗+验证，不落库）"""
        if self._df is None:
            return
        from edu_system.services.import_export import (
            ImportExportService,
            ImportOptions,
        )

        options = ImportOptions(
            entity="student",
            field_mapping=self._build_mapping(),
            dedup_keys=["学号"],
            normalize_gender=True,
        )
        stage = ImportExportService().preview(options, self._df)
        self._stage = stage

        qr = stage.quality_report
        total = qr.get("total", 0)
        error_count = qr.get("error_count", 0)
        warn_count = qr.get("warning_count", 0)
        self._report_label.setText(
            f"验证报告: 共 {total} 行 | 错误 {error_count} 行 | 警告 {warn_count} 行\n"
            f"待入库: {len(stage.rows_to_insert)} 行\n"
            + (f"错误示例: {stage.row_errors[0]['message']}" if stage.row_errors else "")
        )
        self._report_label.show()

        self.import_btn.setEnabled(error_count == 0 and len(stage.rows_to_insert) > 0)
        if error_count > 0:
            QMessageBox.warning(
                self, "存在错误行", f"{error_count} 行有错误，已隔离；修复后重新预览"
            )

    def _import(self):
        """第 5 步：确认入库（事务写入）"""
        if self._stage is None:
            return
        from edu_system.services.import_export import ImportExportService, ImportOptions
        from edu_system.services.importer import ImportService

        options = ImportOptions(entity="student", field_mapping=self._build_mapping())

        def insert_fn(rows):
            svc = ImportService(self.session)
            return svc.import_students_from_excel(self._file_path, mapping=options.field_mapping)

        try:
            result = ImportExportService().import_rows(options, self._stage, insert_fn)
        except Exception as e:  # noqa: BLE001 - 入库异常统一提示
            QMessageBox.critical(self, "入库失败", str(e))
            return

        self._report_label.setText(f"入库完成: 成功 {result.inserted} 行\n{result.summary()}")
        self.import_btn.setEnabled(False)
        QMessageBox.information(self, "导入完成", result.summary())

    # ═══════════ 预览表 ═══════════

    def _show_preview(self, df):
        self._preview_table.setRowCount(len(df))
        self._preview_table.setColumnCount(len(df.columns))
        self._preview_table.setHorizontalHeaderLabels([str(c) for c in df.columns])
        for r, (_, row) in enumerate(df.iterrows()):
            for c, col in enumerate(df.columns):
                self._preview_table.setItem(r, c, QTableWidgetItem(str(row[col])))
        self._preview_table.show()
