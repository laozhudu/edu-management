"""
DynamicFormWidget 单元测试（Sprint 3.7.9）
覆盖：七种字段类型渲染、值回填、校验（必填/类型/枚举）、写回实体
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PyQt5.QtWidgets import QApplication, QCheckBox, QComboBox, QDateEdit, QLineEdit

from edu_system.gui.widgets.dynamic_form import DynamicFormWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _fd(key, ftype="string", label=None, required=False, options=None):
    """构造字段定义（dict 形式）"""
    from types import SimpleNamespace

    return SimpleNamespace(
        field_key=key,
        label=label or key,
        field_type=ftype,
        required=required,
        options=options,
    )


FIELDS = [
    _fd("name", "string", "姓名", required=True),
    _fd("age", "int", "年龄"),
    _fd("height", "float", "身高"),
    _fd("birth", "date", "出生日期"),
    _fd("level", "enum", "级别", options=["初级", "中级", "高级"]),
    _fd("city", "select", "城市", options=["北京", "上海"]),
    _fd("active", "bool", "是否在籍"),
]


class TestRender:
    def test_all_types_rendered(self, qapp):
        """七种字段类型全部生成对应控件"""
        form = DynamicFormWidget(None, "student", FIELDS)
        editors = form._editors
        assert isinstance(editors["name"][0], QLineEdit)
        assert isinstance(editors["age"][0], QLineEdit)  # int 也用 QLineEdit
        assert isinstance(editors["birth"][0], QDateEdit)
        assert isinstance(editors["level"][0], QComboBox)
        assert isinstance(editors["city"][0], QComboBox)
        assert isinstance(editors["active"][0], QCheckBox)

    def test_enum_options_loaded(self, qapp):
        """enum 字段选项加载到下拉框"""
        form = DynamicFormWidget(None, "student", FIELDS)
        cb = form._editors["level"][0]
        items = [cb.itemData(i) for i in range(cb.count())]
        assert "初级" in items and "高级" in items

    def test_required_marked(self, qapp):
        """必填字段标记（validate 校验）"""
        form = DynamicFormWidget(None, "student", FIELDS)
        values, errors = form.validate()
        assert any("必填" in e for e in errors)
        assert "name" not in values  # 未填必填不进入值


class TestValues:
    def test_set_values_string(self, qapp):
        """字符串值回填"""
        form = DynamicFormWidget(None, "student", FIELDS)
        form.set_values({"name": "张三"})
        assert form._editors["name"][0].text() == "张三"

    def test_set_values_enum(self, qapp):
        """枚举值回填（按 data 匹配）"""
        form = DynamicFormWidget(None, "student", FIELDS)
        form.set_values({"level": "中级"})
        cb = form._editors["level"][0]
        assert cb.currentData() == "中级"

    def test_set_values_bool(self, qapp):
        """布尔值回填"""
        form = DynamicFormWidget(None, "student", FIELDS)
        form.set_values({"active": True})
        assert form._editors["active"][0].isChecked() is True

    def test_validate_converts_types(self, qapp):
        """int/float 类型转换校验"""
        form = DynamicFormWidget(None, "student", FIELDS)
        form.set_values({"name": "张三", "age": "18", "height": "1.75"})
        values, errors = form.validate()
        assert errors == []
        assert values["age"] == 18
        assert values["height"] == 1.75

    def test_validate_int_error(self, qapp):
        """int 字段非法值报错"""
        form = DynamicFormWidget(None, "student", FIELDS)
        form.set_values({"name": "张三", "age": "abc"})
        values, errors = form.validate()
        assert any("age" in e for e in errors)

    def test_validate_enum_invalid(self, qapp):
        """enum 字段未选或非法——下拉框天然约束，空值可选但必填才报"""
        form = DynamicFormWidget(None, "student", FIELDS)
        form.set_values({"name": "张三"})
        values, errors = form.validate()
        # level 非必填，空值允许 → 无错误
        assert errors == []


class TestSave:
    def test_save_to_entity(self, qapp):
        """校验通过后写回实体 ext_json（含 date 序列化为 ISO 字符串）"""
        from types import SimpleNamespace

        from edu_system.services.meta import FieldService

        entity = SimpleNamespace(ext_json=None)
        form = DynamicFormWidget(None, "student", FIELDS)
        form.set_values({"name": "李四", "age": "20", "birth": "2020-01-01"})
        form.save_to(entity)
        assert FieldService.get_value(entity, "name") == "李四"
        assert FieldService.get_value(entity, "age") == 20
        assert FieldService.get_value(entity, "birth") == "2020-01-01"

    def test_save_required_error(self, qapp):
        """必填缺失时 save 抛错"""
        from types import SimpleNamespace

        entity = SimpleNamespace(ext_json=None)
        form = DynamicFormWidget(None, "student", FIELDS)
        with pytest.raises(ValueError):
            form.save_to(entity)
