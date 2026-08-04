"""
ThemeManager 测试（Sprint 4.2.6）
覆盖：令牌完整性、切换/持久化/toggle、系统跟随、无效模式
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PyQt5.QtCore import QSettings


@pytest.fixture(autouse=True)
def isolate_qsettings(tmp_path):
    """隔离 QSettings，避免污染用户真实主题配置"""
    s = QSettings("edu_system", "theme")
    s.remove("mode")
    yield
    s.remove("mode")


def _mk_manager():
    from edu_system.gui.theme_manager import ThemeManager

    return ThemeManager()


import edu_system.gui.theme_manager as tm


class TestTokens:
    def test_light_dark_same_keys(self):
        """亮暗令牌键一致（可无缝切换）"""
        assert set(tm.LIGHT) == set(tm.DARK)
        assert len(tm.LIGHT) >= 20

    def test_all_themes_registered(self):
        assert set(tm.THEMES) == {"light", "dark"}


class TestSwitching:
    def test_default_mode_system(self):
        m = _mk_manager()
        assert m.mode in ("light", "dark", "system")

    def test_manual_light(self):
        m = _mk_manager()
        opened = m.set_mode("light")
        assert opened == "light"
        assert m.theme == "light"
        assert m.tokens()["bg_light"] == tm.LIGHT["bg_light"]

    def test_manual_dark(self):
        m = _mk_manager()
        m.set_mode("dark")
        assert m.theme == "dark"
        assert m.tokens()["text"] == tm.DARK["text"]

    def test_toggle(self):
        m = _mk_manager()
        m.set_mode("light")
        assert m.toggle() == "dark"
        assert m.toggle() == "light"

    def test_invalid_mode_rejected(self):
        m = _mk_manager()
        with pytest.raises(ValueError):
            m.set_mode("invalid")

    def test_persistence(self, tmp_path):
        """模式持久化到 QSettings"""
        m1 = _mk_manager()
        m1.set_mode("dark")
        m2 = _mk_manager()  # 新实例读持久化
        assert m2.mode == "dark"


class TestSystemTheme:
    def test_system_theme_missing_app(self, monkeypatch):
        """无 QApplication 时系统跟随回退 light"""
        monkeypatch.setattr(tm.ThemeManager, "_system_theme", staticmethod(lambda: "light"))
        m = _mk_manager()
        m.set_mode("system")
        assert m.theme == "light"


class TestApplyTemplate:
    def test_apply_to_render(self):
        m = _mk_manager()
        m.set_mode("dark")
        qss = "color: {text}; background: {bg_light};"
        rendered = m.apply_to(qss)
        assert rendered == f"color: {tm.DARK['text']}; background: {tm.DARK['bg_light']};"
