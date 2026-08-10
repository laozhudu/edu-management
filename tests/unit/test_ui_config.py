"""
UI 配置加载器单元测试
验证：模板变量渲染、域加载、权限过滤、热键配置、默认值兜底
"""

from edu_system.config.ui_config import UIConfig, get_config, reload_config


class TestUIConfig:
    def test_template_rendering(self):
        """模板变量正确渲染"""
        cfg = get_config()
        assert cfg.window_title == "示例学校 教务管理系统 · 3.8.0"
        assert cfg.footer_text == "示例学校 · 3.8.0"
        assert cfg.brand_text == "示例学校教务管理系统"

    def test_domains_loaded(self):
        """9 个域正确加载并按 order 排序"""
        cfg = get_config()
        domains = cfg.domains_parsed
        assert len(domains) == 9
        titles = [d["title"] for d in domains]
        assert titles == [
            "首页",
            "学生管理",
            "教师管理",
            "班级科目",
            "教室位置",
            "考试管理",
            "成绩管理",
            "报表工具",
            "系统设置",
        ]

    def test_students_permissions(self):
        """学生管理域的权限正确"""
        cfg = get_config()
        students = next(d for d in cfg.domains_parsed if d["title"] == "学生管理")
        assert students["permissions"] == ["admin", "academic_staff"]

    def test_student_register_admin_only(self):
        """新生注册页签仅 admin 可见"""
        cfg = get_config()
        students = next(d for d in cfg.domains_parsed if d["title"] == "学生管理")
        reg_tab = next(t for t in students["tabs"] if t.id == "student_register")
        assert reg_tab.permissions == ["admin"]

    def test_admin_sees_all(self):
        """admin 角色看到全部 9 个域"""
        cfg = get_config()
        visible = cfg.filter_domains(["admin"])
        assert len(visible) == 9

    def test_teacher_filtered(self):
        """teacher 角色被过滤掉学生管理域（其余 8 域可见）"""
        cfg = get_config()
        visible = cfg.filter_domains(["teacher"])
        titles = [d["title"] for d in visible]
        assert "学生管理" not in titles
        assert len(visible) == 8

    def test_academic_staff_sees_students(self):
        """academic_staff 角色看到学生管理"""
        cfg = get_config()
        visible = cfg.filter_domains(["academic_staff"])
        titles = [d["title"] for d in visible]
        assert "学生管理" in titles

    def test_hotkeys_config(self):
        """热键配置正确"""
        cfg = get_config()
        shortcuts = cfg.topbar.shortcuts
        assert shortcuts["command_palette"] == "Ctrl+K"
        assert shortcuts["score_entry"] == "Ctrl+E"
        assert shortcuts["refresh"] == "F5"

    def test_default_fallback(self):
        """无配置文件时内嵌默认兜底（精简 6 域，仅保证可用）"""
        try:
            cfg = reload_config("/nonexistent/path.json")
            assert isinstance(cfg, UIConfig)
            assert cfg.window_title == "示例学校 教务管理系统 v3.0.0"
            # 兜底保持精简 6 域（无外部文件时的最小可用集，非完整 8 域）
            assert len(cfg.domains_parsed) == 6
        finally:
            # 恢复真实配置，避免污染后续测试（reload_config 改全局单例）
            reload_config()

    def test_app_config_fields(self):
        """AppConfig 字段完整"""
        app = UIConfig().app
        assert app.name == "教务管理系统"
        assert app.school_name == "示例学校"
        assert app.version == "3.0.0"

    def test_theme_config(self):
        """ThemeConfig 字段完整"""
        cfg = get_config()
        assert cfg.theme.accent_color == "#3498DB"
        assert cfg.theme.sidebar_bg == "#2C3E50"
        assert cfg.theme.density == "compact"

    def test_hotkeys_detail(self):
        """热键配置完整"""
        shortcuts = get_config().topbar.shortcuts
        assert shortcuts["command_palette"] == "Ctrl+K"
        assert shortcuts["score_entry"] == "Ctrl+E"
        assert shortcuts["refresh"] == "F5"
