"""
TableColumnManager 单元测试（Sprint 3.7.10）
覆盖：列合并、偏好应用（隐藏/顺序/宽度）、持久化、重置
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


from edu_system.gui.widgets.table_columns import TableColumnManager


@pytest.fixture(autouse=True)
def isolate_settings(tmp_path):
    """每个测试独立 QSettings 存储（不污染用户真实配置）"""
    from PyQt5.QtCore import QSettings as QS

    QS.setDefaultFormat(QS.IniFormat)
    import edu_system.gui.widgets.table_columns as tc

    tc._SETTINGS_ORG = "edu_test"
    tc._SETTINGS_APP = f"tc_{tmp_path.name}"
    yield


SYSTEM = [
    {"key": "name", "label": "姓名", "width": 100, "required": True},
    {"key": "student_no", "label": "学号", "width": 120},
]


def _fd(key, label, ftype="string"):
    from types import SimpleNamespace

    return SimpleNamespace(
        field_key=key, label=label, field_type=ftype, required=False, options=None
    )


class TestBuild:
    def test_default_merge(self):
        """默认合并：系统列在前 + 动态列在后"""
        mgr = TableColumnManager("t1", SYSTEM)
        cols = mgr.build([_fd("hobby", "兴趣爱好"), _fd("height", "身高", "float")])
        keys = [c["key"] for c in cols]
        assert keys == ["name", "student_no", "hobby", "height"]

    def test_dynamic_width_by_type(self):
        """动态列宽度按类型：string 120 / float 90"""
        mgr = TableColumnManager("t1", SYSTEM)
        cols = mgr.build([_fd("hobby", "兴趣爱好"), _fd("height", "身高", "float")])
        by_key = {c["key"]: c for c in cols}
        assert by_key["hobby"]["width"] == 120
        assert by_key["height"]["width"] == 90

    def test_no_field_defs(self):
        """无动态字段时仅系统列"""
        mgr = TableColumnManager("t1", SYSTEM)
        cols = mgr.build()
        assert [c["key"] for c in cols] == ["name", "student_no"]


class TestPrefs:
    def test_save_hidden(self):
        """保存隐藏列后 build 不再返回"""
        mgr = TableColumnManager("t2", SYSTEM)
        mgr.build([_fd("hobby", "兴趣爱好")])
        mgr.save_visible(["name", "hobby"])  # 隐藏 student_no
        cols = mgr.build([_fd("hobby", "兴趣爱好")])
        keys = [c["key"] for c in cols]
        assert "student_no" not in keys
        assert "name" in keys and "hobby" in keys

    def test_save_order(self):
        """保存顺序后 build 按新顺序"""
        mgr = TableColumnManager("t3", SYSTEM)
        mgr.build([_fd("hobby", "兴趣爱好")])
        mgr.save_order(["hobby", "name", "student_no"])
        cols = mgr.build([_fd("hobby", "兴趣爱好")])
        assert [c["key"] for c in cols] == ["hobby", "name", "student_no"]

    def test_save_width(self):
        """保存宽度后 build 应用"""
        mgr = TableColumnManager("t4", SYSTEM)
        mgr.build()
        mgr.save_width("name", 200)
        cols = mgr.build()
        assert cols[0]["width"] == 200

    def test_new_column_appended(self):
        """用户保存偏好后新增的动态列仍出现（追加在最后）"""
        mgr = TableColumnManager("t5", SYSTEM)
        mgr.build([_fd("hobby", "兴趣爱好")])
        mgr.save_order(["name", "student_no"])
        cols = mgr.build([_fd("hobby", "兴趣爱好"), _fd("new_f", "新字段")])
        keys = [c["key"] for c in cols]
        assert "new_f" in keys
        assert keys[-1] == "new_f"

    def test_reset_clears_prefs(self):
        """reset 后回到默认（全部列、系统列在前）"""
        mgr = TableColumnManager("t6", SYSTEM)
        mgr.build([_fd("hobby", "兴趣爱好")])
        mgr.save_visible(["name"])
        mgr.reset()
        cols = mgr.build([_fd("hobby", "兴趣爱好")])
        assert [c["key"] for c in cols] == ["name", "student_no", "hobby"]
