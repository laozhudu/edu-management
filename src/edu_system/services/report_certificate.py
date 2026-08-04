"""
证书/通知书生成服务（Sprint 4.8.2）

- docxtpl 渲染 Word 模板（{{name}} 变量、{% for %} 循环、{% if %} 条件）
- WeasyPrint 转 PDF（证书/通知书/准考证）
- 单份渲染 + 批量渲染
"""

from pathlib import Path

from docxtpl import DocxTemplate


class CertificateError(Exception):
    """证书渲染错误"""


class CertificateGenerator:
    def __init__(self, template_path: str | Path):
        self.template_path = Path(template_path)
        if not self.template_path.exists():
            raise CertificateError(f"模板不存在: {self.template_path}")

    # ── 渲染 ──
    def render_docx(self, data: dict, output_path: str | Path) -> Path:
        """渲染单份 Word（docxtpl 支持 {{var}} / {% for %} / {% if %}）"""
        doc = DocxTemplate(str(self.template_path))
        doc.render(data)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out))
        return out

    def render_pdf(self, data: dict, output_path: str | Path) -> Path:
        """渲染 Word 后转 PDF（WeasyPrint 基于 HTML 转 PDF，需先转 HTML）

        说明：docx → PDF 需经 docx2pdf/soffice；此处提供 HTML 模板方案：
        若模板为 .docx，走 docx 渲染；若为 .html，直接 WeasyPrint 转 PDF
        """
        from weasyprint import HTML

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if self.template_path.suffix.lower() == ".html":
            # HTML 模板：jinja 渲染 + WeasyPrint 转 PDF
            import jinja2

            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(self.template_path.parent)),
                autoescape=True,
            )
            tpl = env.get_template(self.template_path.name)
            html = tpl.render(**data)
            HTML(string=html).write_pdf(str(out))
            return out

        # .docx 模板：docxtpl 渲染后存 docx（PDF 转换需 soffice，此处返回 docx 并提示）
        self.render_docx(data, out.with_suffix(".docx"))
        raise CertificateError(
            "docx→PDF 需 LibreOffice soffice 转换；已生成 .docx，请用 render_docx 或 soffice 转换"
        )

    # ── 批量 ──
    def render_batch(
        self, rows: list[dict], output_dir: str | Path, prefix: str = "cert"
    ) -> list[Path]:
        """批量渲染（每行一份 docx）"""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        results = []
        for i, row in enumerate(rows, 1):
            out = out_dir / f"{prefix}_{i:03d}.docx"
            self.render_docx(row, out)
            results.append(out)
        return results
