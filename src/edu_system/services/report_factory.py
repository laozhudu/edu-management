"""
报表工厂（Sprint 4.8.4）

统一入口：业务一行调用生成报表/证书/打印
- gen_student_roster()：学生名册 Excel
- gen_score_report()：成绩报表 Excel/Word
- gen_certificate()：证书 PDF/docx
- print_files()：批量打印
"""

from pathlib import Path


class ReportFactoryError(Exception):
    """报表工厂错误"""


class ReportFactory:
    def __init__(self, session=None):
        self.session = session
        # 延迟导入子服务（避免循环依赖/无 GUI 环境报错）
        self._excel = None
        self._cert = None
        self._print = None

    # ── 子服务懒加载 ──
    @property
    def excel(self):
        if self._excel is None:
            from edu_system.services.report_excel import ExcelTemplateService

            self._excel = ExcelTemplateService
        return self._excel

    @property
    def cert(self):
        if self._cert is None:
            from edu_system.services.report_certificate import CertificateGenerator

            self._cert = CertificateGenerator
        return self._cert

    @property
    def printer(self):
        if self._print is None:
            from edu_system.services.print_service import PrintService

            self._print = PrintService()
        return self._print

    # ── 学生名册 ──
    def gen_student_roster(
        self,
        template_path: str | Path,
        data: dict,
        output_path: str | Path | None = None,
    ) -> bytes:
        """学生名册：Excel 模板填充"""
        return self.excel.render(str(template_path), data, output_path=output_path)

    # ── 成绩报表 ──
    def gen_score_report(
        self,
        exam_id: int,
        output_path: str,
        session=None,
    ) -> str:
        """成绩报表：走 ReportService 现有实现"""
        from edu_system.services.report import ReportService

        svc = ReportService(session or self.session)
        return svc.generate_exam_report(exam_id, output_path)

    # ── 证书 ──
    def gen_certificate(
        self,
        template_path: str | Path,
        data: dict,
        output_path: str | Path,
        as_pdf: bool = False,
    ) -> Path:
        """证书/通知书：docx 或 HTML→PDF"""
        gen = self.cert(template_path)
        if as_pdf and Path(template_path).suffix.lower() == ".html":
            return gen.render_pdf(data, output_path)
        return gen.render_docx(data, output_path)

    # ── 打印 ──
    def print_files(self, file_paths: list[str | Path], copies: int = 1) -> dict[str, bool]:
        """批量打印，返回 文件→成功 映射"""
        return self.printer.print_files(file_paths, copies)

    # ── 一键流程 ──
    def gen_and_print(
        self,
        template_path: str | Path,
        rows: list[dict],
        output_dir: str | Path,
        prefix: str = "report",
    ) -> list[Path]:
        """模板批量生成并打印（报表+证书一体流程）"""
        gen = self.cert(template_path)
        outs = gen.render_batch(rows, output_dir, prefix=prefix)
        self.printer.print_files(outs)
        return outs
