"""
动态表单渲染器（Sprint 3.7.9）
根据 FieldDefinition 注册表动态生成编辑表单（PyQt5 QFormLayout）

支持字段类型：string / int / float / date / enum / select / bool
- 必填校验（* 标记 + validate）
- 枚举/选择下拉、布尔开关、日期选择
- 自定义字段与系统字段混合渲染
"""

from datetime import date

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from edu_system.gui.theme import font


class DynamicFormWidget(QWidget):
    """根据字段定义动态构建表单

    用法:
        form = DynamicFormWidget(session, "student", field_defs)
        form.set_values(entity)          # 从实体 ext_json 回填
        values, errors = form.validate() # 校验并返回 (值字典, 错误列表)
        form.save_to(entity)             # 写回实体 ext_json
    """

    def __init__(self, session, entity_type: str, fields: list, parent=None):
        super().__init__(parent)
        self._session = session
        self._entity_type = entity_type
        self._fields = fields
        self._editors = {}  # field_key -> 输入控件
        self._build()

    # ── 构建 ──
    def _build(self):
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        for fd in self._fields:
            key = fd.field_key if hasattr(fd, "field_key") else fd.get("field_key")
            label = fd.label if hasattr(fd, "label") else fd.get("label", key)
            ftype = fd.field_type if hasattr(fd, "field_type") else fd.get("field_type", "string")
            required = bool(fd.required if hasattr(fd, "required") else fd.get("required", False))
            options = getattr(fd, "options", None)
            if options is None and isinstance(fd, dict):
                options = fd.get("options")

            label_text = f"{label}*" if required else label
            editor = self._make_editor(ftype, options)
            self._editors[key] = (editor, ftype, required)
            form.addRow(QLabel(label_text), editor)

    def _make_editor(self, ftype: str, options):
        """按字段类型创建输入控件"""
        if ftype in ("enum", "select"):
            cb = QComboBox()
            cb.setFont(font(10))
            cb.setMinimumHeight(34)
            opts = options or []
            if isinstance(opts, str):
                import json

                try:
                    opts = json.loads(opts)
                except (ValueError, TypeError):
                    opts = []
            cb.addItem("", None)  # 空选项
            for o in opts:
                cb.addItem(str(o), o)
            return cb
        if ftype == "bool":
            cb = QCheckBox()
            cb.setFont(font(10))
            return cb
        if ftype == "date":
            de = QDateEdit()
            de.setCalendarPopup(True)
            de.setDisplayFormat("yyyy-MM-dd")
            de.setMinimumHeight(34)
            de.setFont(font(10))
            de.setSpecialValueText("")  # 空值显示
            return de
        # string / int / float 用 QLineEdit（int/float 在 validate 时转换）
        edit = QLineEdit()
        edit.setFont(font(10))
        edit.setMinimumHeight(34)
        return edit

    # ── 回填 ──
    def set_values(self, values: dict):
        """从值字典回填（key -> value）"""
        for key, (editor, ftype, required) in self._editors.items():
            value = values.get(key)
            if value in (None, ""):
                continue
            if isinstance(editor, QComboBox):
                idx = editor.findData(value)
                if idx < 0:
                    idx = editor.findText(str(value))
                if idx >= 0:
                    editor.setCurrentIndex(idx)
            elif isinstance(editor, QCheckBox):
                editor.setChecked(bool(value))
            elif isinstance(editor, QDateEdit):
                d = value if isinstance(value, date) else None
                if d is None and isinstance(value, str):
                    try:
                        from datetime import datetime

                        d = datetime.strptime(value, "%Y-%m-%d").date()
                    except ValueError:
                        d = None
                if d is not None:
                    editor.setDate(QDate(d.year, d.month, d.day))
            else:
                editor.setText("" if value is None else str(value))

    # ── 校验与取值 ──
    def validate(self) -> tuple[dict, list]:
        """校验并返回 (值字典, 错误列表)。错误时值字典为已转换的合法值"""
        values = {}
        errors = []
        for key, (editor, ftype, required) in self._editors.items():
            raw = self._raw_value(editor)
            # 必填
            if required and raw in (None, "", []):
                errors.append(f"字段必填: {key}")
                continue
            if raw in (None, ""):
                values[key] = None
                continue
            # 类型转换
            try:
                values[key] = self._convert(ftype, raw)
            except ValueError as e:
                errors.append(f"{key}: {e}")
        return values, errors

    def _raw_value(self, editor):
        if isinstance(editor, QComboBox):
            return editor.currentData()
        if isinstance(editor, QCheckBox):
            return editor.isChecked()
        if isinstance(editor, QDateEdit):
            d = editor.date()
            return QDate(d.year(), d.month(), d.day()).toString("yyyy-MM-dd")
        return editor.text().strip()

    @staticmethod
    def _convert(ftype: str, raw):
        if ftype == "int":
            return int(raw)
        if ftype == "float":
            return float(raw)
        if ftype == "bool":
            return raw in (True, "1", "true", "是", "yes")
        if ftype == "date":
            if isinstance(raw, str) and raw:
                from datetime import datetime

                # 存 ext_json 用 ISO 字符串（date 对象不可 JSON 序列化）
                return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()
            return raw
        return str(raw)

    # ── 写回 ──
    def save_to(self, entity):
        """把校验后的值写回实体 ext_json（未校验的值跳过）"""
        from edu_system.services.meta import FieldService

        values, errors = self.validate()
        if errors:
            raise ValueError("; ".join(errors))
        for key, value in values.items():
            FieldService.set_value(entity, key, value)

    # ── 辅助 ──
    @property
    def field_keys(self) -> list:
        return list(self._editors.keys())
