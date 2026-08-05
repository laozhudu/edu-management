"""
报表模板管理服务测试（M5-D5）

覆盖：
- 模板注册：版本递增，同名旧版本保留
- 版本管理：get_versions 全版本 / list_all 最新
- 回滚：rollback_to 置目标版本 active
- 变量扫描：Excel/Word 模板占位符解析
- 测试渲染：样例数据渲染 + 缺失变量报告
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.models import Base, ReportTemplate
from edu_system.services.report_template import (
    ReportTemplateError,
    ReportTemplateService,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture
def svc(session):
    return ReportTemplateService(session)


def _make_xlsx(path: Path, cell_text: str = "{{name}} 的成绩单 {{grade}}"):
    """生成含占位符的迷你 xlsx 模板"""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws["A1"] = cell_text
    wb.save(path)
    wb.close()
    return path


class TestRegister:
    def test_register_first_version(self, svc, session):
        tpl = svc.register("成绩单", "excel", "templates/score.xlsx", created_by="admin")
        assert tpl.version == 1
        assert tpl.is_active is True
        assert tpl.template_type == "excel"

    def test_register_increments_version(self, svc, session):
        svc.register("成绩单", "excel", "templates/score_v1.xlsx")
        tpl2 = svc.register("成绩单", "excel", "templates/score_v2.xlsx")
        assert tpl2.version == 2
        # 旧版本停用，历史保留
        old = (
            session.query(ReportTemplate)
            .filter(ReportTemplate.name == "成绩单", ReportTemplate.version == 1)
            .first()
        )
        assert old is not None
        assert old.is_active is False

    def test_register_validation(self, svc):
        with pytest.raises(ReportTemplateError):
            svc.register("", "excel", "path")
        with pytest.raises(ReportTemplateError):
            svc.register("成绩单", "pdf", "path")

    def test_get_latest(self, svc, session):
        svc.register("成绩单", "excel", "v1.xlsx")
        svc.register("成绩单", "excel", "v2.xlsx")
        latest = svc.get_latest("成绩单")
        assert latest.version == 2
        assert latest.file_path == "v2.xlsx"


class TestVersioning:
    def test_get_versions_desc(self, svc, session):
        svc.register("成绩单", "excel", "v1.xlsx")
        svc.register("成绩单", "excel", "v2.xlsx")
        svc.register("成绩单", "excel", "v3.xlsx")
        versions = svc.get_versions("成绩单")
        assert [v["version"] for v in versions] == [3, 2, 1]
        assert versions[0]["is_active"] is True

    def test_list_all_latest_only(self, svc, session):
        svc.register("成绩单", "excel", "v1.xlsx")
        svc.register("成绩单", "excel", "v2.xlsx")
        svc.register("荣誉证书", "certificate", "cert.docx")
        all_tpls = svc.list_all()
        names = {t["name"] for t in all_tpls}
        assert names == {"成绩单", "荣誉证书"}
        score = next(t for t in all_tpls if t["name"] == "成绩单")
        assert score["version"] == 2

    def test_rollback_to_version(self, svc, session):
        svc.register("成绩单", "excel", "v1.xlsx")
        svc.register("成绩单", "excel", "v2.xlsx")
        svc.rollback_to("成绩单", 1)
        latest = svc.get_latest("成绩单")
        # 回滚后 v1 为 active（latest 仍返回最大版本，但 active 状态切换）
        v1 = (
            session.query(ReportTemplate)
            .filter(ReportTemplate.name == "成绩单", ReportTemplate.version == 1)
            .first()
        )
        v2 = (
            session.query(ReportTemplate)
            .filter(ReportTemplate.name == "成绩单", ReportTemplate.version == 2)
            .first()
        )
        assert v1.is_active is True
        assert v2.is_active is False

    def test_rollback_missing_version(self, svc):
        svc.register("成绩单", "excel", "v1.xlsx")
        with pytest.raises(ReportTemplateError):
            svc.rollback_to("成绩单", 99)


class TestVariableScan:
    def test_scan_excel(self, svc, tmp_path):
        p = _make_xlsx(tmp_path / "tpl.xlsx")
        vars_ = svc.scan_variables(str(p))
        keys = {v["key"] for v in vars_}
        assert {"name", "grade"}.issubset(keys)

    def test_scan_missing_file(self, svc):
        with pytest.raises(ReportTemplateError):
            svc.scan_variables("/nonexistent/tpl.xlsx")

    def test_scan_unsupported(self, svc, tmp_path):
        p = tmp_path / "tpl.pdf"
        p.write_text("x")
        with pytest.raises(ReportTemplateError):
            svc.scan_variables(str(p))


class TestTestRender:
    def test_render_all_vars(self, svc, tmp_path):
        p = _make_xlsx(tmp_path / "tpl.xlsx", "{{name}} {{grade}}")
        r = svc.test_render(str(p), {"name": "张三", "grade": "一年级"})
        assert r["ok"] is True
        assert r["rendered_cells"] == 2
        assert r["missing_vars"] == []

    def test_render_missing_vars(self, svc, tmp_path):
        p = _make_xlsx(tmp_path / "tpl.xlsx", "{{name}} {{grade}}")
        r = svc.test_render(str(p), {"name": "张三"})
        assert r["ok"] is False
        assert r["missing_vars"] == ["grade"]
