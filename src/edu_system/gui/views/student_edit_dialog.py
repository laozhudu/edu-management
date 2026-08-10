"""
StudentEditDialog — 学生新增/编辑对话框（G2 拆分：从 student.py 独立）
"""

from __future__ import annotations

from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from edu_system.gui.theme import font
from edu_system.models import Class as ClassModel
from edu_system.models import Student
from edu_system.schemas import ID_CARD_REGEX, PHONE_REGEX


class StudentEditDialog(QDialog):
    """学生新增/编辑对话框 - 29字段分组布局 + 照片支持"""

    def __init__(
        self, parent, student: Student = None, title: str = "编辑", session: Session = None
    ):
        super().__init__(parent)
        self.student = student
        self.session = session
        self.setWindowTitle(f"{title}学生" if student else "新增学生")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._photo_data = None
        self._photo_mime = ""

        self._build_ui()

        if student:
            self._load_student(student)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 顶部：照片区域
        photo_layout = QHBoxLayout()

        # 照片预览
        self.photo_label = QLabel("无照片")
        self.photo_label.setFixedSize(120, 150)
        self.photo_label.setAlignment(Qt.AlignCenter)
        self.photo_label.setStyleSheet(
            "border: 1px solid #DDD; border-radius: 4px; background: #F5F5F5;"
        )
        self.photo_label.setAcceptDrops(True)
        self.photo_label.dragEnterEvent = self._drag_enter
        self.photo_label.dropEvent = self._drop_photo
        self.photo_label.mousePressEvent = self._click_photo
        photo_layout.addWidget(self.photo_label)

        # 照片操作按钮
        photo_btns = QVBoxLayout()
        for txt, cb in [
            ("选择照片", self._select_photo),
            ("粘贴照片", self._paste_photo),
            ("清除照片", self._clear_photo),
        ]:
            btn = QPushButton(txt)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(cb)
            btn.setMinimumHeight(28)
            photo_btns.addWidget(btn)
        photo_btns.addStretch()
        photo_layout.addLayout(photo_btns)
        photo_layout.addStretch()
        layout.addLayout(photo_layout)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #DDD;")
        layout.addWidget(line)

        # 主体：分组标签页
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        # 组1：基本信息
        basic_widget = self._create_basic_tab()
        tabs.addTab(basic_widget, "基本信息")

        # 组2：学籍信息
        academic_widget = self._create_academic_tab()
        tabs.addTab(academic_widget, "学籍信息")

        # 组3：监护人信息
        guardian_widget = self._create_guardian_tab()
        tabs.addTab(guardian_widget, "监护人信息")

        # 组4：其他/备注
        other_widget = self._create_other_tab()
        tabs.addTab(other_widget, "其他/备注")

        layout.addWidget(tabs, 1)

        # 底部按钮
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._on_accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _create_basic_tab(self):
        w = QWidget()
        # Store as instance variable to prevent garbage collection
        self._basic_tab_widget = w
        form = QFormLayout(w)
        form.setSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        # Keep reference to form as well
        self._basic_form = form

        self.basic_widgets = {}
        fields = [
            ("name", "姓名*", QLineEdit),
            ("gender", "性别*", QComboBox),
            ("birth_date", "出生日期", QLineEdit),
            ("ethnicity", "民族", QLineEdit),
            ("native_place", "籍贯", QLineEdit),
            ("political_status", "政治面貌", QLineEdit),
            ("phone", "电话", QLineEdit),
            ("address", "居住地址", QLineEdit),
            ("hukou_addr", "户籍地址", QLineEdit),
            ("boarding", "走住读", QComboBox),
        ]

        for key, label, widget_cls in fields:
            if widget_cls == QComboBox:
                w = QComboBox()
                if key == "gender":
                    w.addItems(["男", "女"])
                elif key == "boarding":
                    w.addItems(["走读", "住宿", "半寄宿"])
                w.setFont(font(9))
            else:
                w = QLineEdit()
                w.setFont(font(9))
                if key == "birth_date":
                    w.setPlaceholderText("YYYY-MM-DD")
                elif key == "phone":
                    w.setPlaceholderText("11位手机号")
                    w.textChanged.connect(
                        lambda text, k=key: self._validate_field_realtime(k, text)
                    )
            form.addRow(label, w)
            self.basic_widgets[key] = w

        return w

    def _create_academic_tab(self):
        w = QWidget()
        self._academic_tab_widget = w
        form = QFormLayout(w)
        form.setSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self._academic_form = form

        self.academic_widgets = {}
        fields = [
            ("class_name", "班级*", QComboBox),
            ("student_no", "座号", QLineEdit),
            ("student_code", "学籍号*", QLineEdit),
            ("id_card", "身份证*", QLineEdit),
            ("exam_no", "考号", QLineEdit),
            ("enroll_year", "入学年份*", QLineEdit),
            ("status", "状态*", QComboBox),
        ]

        for key, label, widget_cls in fields:
            if widget_cls == QComboBox:
                w = QComboBox()
                if key == "status":
                    w.addItems(["在校", "休学", "复学", "退学", "转学", "毕业"])
                elif key == "class_name":
                    w.setEditable(False)
                    if self.session:
                        classes = self.session.query(ClassModel).order_by(ClassModel.name).all()
                        w.addItems([c.name for c in classes])
                w.setFont(font(9))
            else:
                w = QLineEdit()
                w.setFont(font(9))
                if key == "id_card":
                    w.setPlaceholderText("18位身份证号")
                    w.textChanged.connect(
                        lambda text, k=key: self._validate_field_realtime(k, text)
                    )
                elif key == "enroll_year":
                    w.setPlaceholderText("如 2024")
                elif key == "student_code":
                    w.setPlaceholderText("学籍号")
                    w.textChanged.connect(
                        lambda text, k=key: self._validate_field_realtime(k, text)
                    )
            form.addRow(label, w)
            self.academic_widgets[key] = w
        return w

    def _create_guardian_tab(self):
        w = QWidget()
        self._guardian_tab_widget = w
        form = QFormLayout(w)
        form.setSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self._guardian_form = form

        self.guardian_widgets = {}

        for prefix, title in [("guardian1", "监护人1"), ("guardian2", "监护人2")]:
            # 分隔标题
            sep = QLabel(f"<b>{title}</b>")
            sep.setStyleSheet("margin-top: 8px; margin-bottom: 4px;")
            form.addRow(sep)

            for key, label in [
                (f"{prefix}_name", "姓名"),
                (f"{prefix}_relation", "关系"),
                (f"{prefix}_phone", "电话"),
                (f"{prefix}_work", "工作单位"),
                (f"{prefix}_edu", "学历"),
                (f"{prefix}_id_card", "身份证"),
            ]:
                e = QLineEdit()
                e.setFont(font(9))
                if "phone" in key:
                    e.setPlaceholderText("11位手机号")
                    e.textChanged.connect(
                        lambda text, k=key: self._validate_field_realtime(k, text)
                    )
                elif "id_card" in key:
                    e.setPlaceholderText("18位身份证号")
                    e.textChanged.connect(
                        lambda text, k=key: self._validate_field_realtime(k, text)
                    )
                form.addRow(label, e)
                self.guardian_widgets[key] = e

        return w

    def _create_other_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        self.note_edit = QTextEdit()
        self.note_edit.setFont(font(9))
        self.note_edit.setPlaceholderText("备注信息...")
        self.note_edit.setMaximumHeight(100)
        layout.addWidget(QLabel("备注"))
        layout.addWidget(self.note_edit)
        layout.addStretch()
        return w

    def _validate_field_realtime(self, field_name: str, text: str):
        """实时字段验证"""
        error_msg = None

        if field_name in ("phone", "guardian1_phone", "guardian2_phone"):
            if text and not PHONE_REGEX.match(text):
                error_msg = "手机号格式不正确（需11位，以13-19开头）"
        elif field_name in ("id_card", "guardian1_id_card", "guardian2_id_card"):
            if text and not ID_CARD_REGEX.match(text):
                error_msg = "身份证号格式不正确（需18位，最后一位可为X）"
        elif field_name == "student_code":
            # 学籍号不能为空，长度检查
            if text and len(text) > 20:
                error_msg = "学籍号过长（最多20位）"

        # 设置样式提示错误
        widget = None
        for d in [self.basic_widgets, self.academic_widgets, self.guardian_widgets]:
            if field_name in d:
                widget = d[field_name]
                break

        if widget:
            if error_msg:
                widget.setToolTip(error_msg)
                widget.setStyleSheet("border: 1px solid red;")
            else:
                widget.setToolTip("")
                widget.setStyleSheet("")

    def _load_student(self, s: Student):
        # 基本信息
        self.basic_widgets["name"].setText(s.name or "")
        self.basic_widgets["gender"].setCurrentText(s.gender or "男")
        self.basic_widgets["birth_date"].setText(str(s.birth_date)[:10] if s.birth_date else "")
        self.basic_widgets["ethnicity"].setText(s.ethnicity or "")
        self.basic_widgets["native_place"].setText(s.native_place or "")
        self.basic_widgets["political_status"].setText(s.political_status or "")
        self.basic_widgets["phone"].setText(s.phone or "")
        self.basic_widgets["address"].setText(s.address or "")
        self.basic_widgets["hukou_addr"].setText(s.hukou_addr or "")
        self.basic_widgets["boarding"].setCurrentText(s.boarding or "走读")

        # 学籍信息
        self.academic_widgets["class_name"].setCurrentText(s.class_name or "")
        self.academic_widgets["student_no"].setText(s.student_no or "")
        self.academic_widgets["student_code"].setText(s.student_code or "")
        self.academic_widgets["id_card"].setText(s.id_card or "")
        self.academic_widgets["exam_no"].setText(s.exam_no or "")
        self.academic_widgets["enroll_year"].setText(str(s.enroll_year) if s.enroll_year else "")
        self.academic_widgets["status"].setCurrentText(s.status or "在校")

        # 监护人
        for key in self.guardian_widgets:
            val = getattr(s, key, "") or ""
            self.guardian_widgets[key].setText(val)

        # 备注
        self.note_edit.setText(s.note or "")

        # 照片
        if s.photo:
            pixmap = QPixmap()
            pixmap.loadFromData(QByteArray(s.photo))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(120, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.photo_label.setPixmap(pixmap)
                self.photo_label.setText("")
            else:
                self.photo_label.setText("无法加载")
                self.photo_label.setPixmap(QPixmap())
        else:
            self.photo_label.setText("无照片")
            self.photo_label.setPixmap(QPixmap())

    def _select_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择照片", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self._load_photo_file(path)

    def _paste_photo(self):
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        if mime.hasImage():
            img = clipboard.image()
            if not img.isNull():
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    img.save(f.name, "PNG")
                    self._load_photo_file(f.name)

    def _click_photo(self, event):
        if event.button() == Qt.LeftButton:
            self._select_photo()

    def _drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_photo(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                self._load_photo_file(path)

    def _load_photo_file(self, path: str):
        try:
            from PIL import Image

            img = Image.open(path)

            # 裁剪为 1:1 正方形（居中）
            w, h = img.size
            if w != h:
                size = min(w, h)
                left = (w - size) // 2
                top = (h - size) // 2
                img = img.crop((left, top, left + size, top + size))

            # 压缩到 < 200KB
            import io

            buffer = io.BytesIO()
            quality = 85
            while quality > 10:
                buffer.seek(0)
                buffer.truncate()
                img.save(buffer, format="JPEG", quality=quality)
                if buffer.tell() < 200 * 1024:
                    break
                quality -= 10

            self._photo_data = buffer.getvalue()
            self._photo_mime = "image/jpeg"

            # 预览
            pixmap = QPixmap()
            pixmap.loadFromData(QByteArray(self._photo_data))
            pixmap = pixmap.scaled(120, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.photo_label.setPixmap(pixmap)
            self.photo_label.setText("")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载照片失败: {e}")

    def _clear_photo(self):
        self._photo_data = None
        self._photo_mime = ""
        self.photo_label.setText("无照片")
        self.photo_label.setPixmap(QPixmap())

    def _on_accept(self):
        # 验证必填字段
        name = self.basic_widgets["name"].text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "姓名不能为空")
            return

        student_code = self.academic_widgets["student_code"].text().strip()
        if not student_code:
            QMessageBox.warning(self, "提示", "学籍号不能为空")
            return

        id_card = self.academic_widgets["id_card"].text().strip()
        if not id_card:
            QMessageBox.warning(self, "提示", "身份证不能为空")
            return

        class_name = self.academic_widgets["class_name"].currentText().strip()
        if not class_name:
            QMessageBox.warning(self, "提示", "请选择班级")
            return

        # 身份证格式校验
        if not ID_CARD_REGEX.match(id_card):
            QMessageBox.warning(self, "提示", "身份证号格式不正确（需18位，最后一位可为X）")
            return

        # 手机号校验（如果填写了）
        phone = self.basic_widgets["phone"].text().strip()
        if phone and not PHONE_REGEX.match(phone):
            QMessageBox.warning(self, "提示", "手机号格式不正确（需11位，以13-19开头）")
            return

        # 监护人手机号校验
        for prefix in ["guardian1", "guardian2"]:
            g_phone = self.guardian_widgets.get(f"{prefix}_phone", "").text().strip()
            if g_phone and not PHONE_REGEX.match(g_phone):
                QMessageBox.warning(
                    self, "提示", f"{prefix} 手机号格式不正确（需11位，以13-19开头）"
                )
                return

        self.accept()

    def get_data(self) -> dict:
        """获取表单数据"""
        data = {}

        # 基本信息
        for key, w in self.basic_widgets.items():
            if isinstance(w, QComboBox):
                data[key] = w.currentText()
            else:
                data[key] = w.text().strip()

        # 学籍信息
        for key, w in self.academic_widgets.items():
            if isinstance(w, QComboBox):
                data[key] = w.currentText()
            else:
                data[key] = w.text().strip()

        # 监护人
        for key, w in self.guardian_widgets.items():
            data[key] = w.text().strip()

        # 备注
        data["note"] = self.note_edit.toPlainText().strip()

        # 照片
        data["photo"] = self._photo_data
        data["photo_mime"] = self._photo_mime

        return data
