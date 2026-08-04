"""
导出服务单元测试
验证：多格式导出、表头映射、空数据、异常格式、模版、预览
"""

import json

import pytest

from edu_system.services.export import (
    ExportFormatError,
    ExportOptions,
    ExportService,
    export_service,
)

SAMPLE_ROWS = [
    {"学号": "2024001", "姓名": "张三", "成绩": 92.5},
    {"学号": "2024002", "姓名": "李四", "成绩": 85.0},
    {"学号": "2024003", "姓名": "王五", "成绩": None},
]


class TestExportService:
    def test_xlsx_export(self):
        """Excel 导出应返回有效 xlsx 字节"""
        result = export_service.export(SAMPLE_ROWS, ExportOptions(format="xlsx"))
        assert result.format == "xlsx"
        assert result.row_count == 3
        assert result.data.startswith(b"PK")  # xlsx = zip 格式
        assert result.filename.endswith(".xlsx")

    def test_csv_export(self):
        """CSV 导出应带 BOM 且内容正确"""
        result = export_service.export(SAMPLE_ROWS, ExportOptions(format="csv"))
        assert result.format == "csv"
        text = result.data.decode("utf-8-sig")
        assert "学号,姓名,成绩" in text
        assert "2024001" in text
        assert result.filename.endswith(".csv")

    def test_json_export(self):
        """JSON 导出应可解析且保留中文"""
        result = export_service.export(SAMPLE_ROWS, ExportOptions(format="json"))
        data = json.loads(result.data.decode("utf-8"))
        assert len(data) == 3
        assert data[0]["姓名"] == "张三"
        assert data[2]["成绩"] is None

    def test_custom_headers(self):
        """自定义表头映射"""
        headers = ["学号", "姓名"]
        result = export_service.export(
            SAMPLE_ROWS,
            ExportOptions(format="csv", headers=headers),
        )
        text = result.data.decode("utf-8-sig")
        assert "学号,姓名" in text
        assert "成绩" not in text

    def test_empty_rows(self):
        """空数据导出不应报错"""
        result = export_service.export([], ExportOptions(format="csv"))
        assert result.row_count == 0
        assert result.data != b"" or not result.errors

    def test_unsupported_format(self):
        """不支持格式应抛异常"""
        with pytest.raises(ExportFormatError):
            export_service.validate_format("pdf")

    def test_invalid_format_in_export(self):
        """导出时传非法格式应返回错误"""
        result = export_service.export(SAMPLE_ROWS, ExportOptions(format="pdf"))
        assert result.errors
        assert len(result.errors) == 1

    def test_export_to_bytes(self):
        """便捷方法返回字节流"""
        data = export_service.export_to_bytes(SAMPLE_ROWS, fmt="json")
        assert json.loads(data.decode("utf-8"))[0]["学号"] == "2024001"

    def test_template_for_student(self):
        """学生模版表头"""
        headers = ExportService.template_for("student")
        assert "学号" in headers
        assert "姓名" in headers

    def test_template_with_dynamic_fields(self):
        """传入 session 时动态追加自定义字段（系统字段不重复）"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from edu_system.models import Base
        from edu_system.services.meta import FieldService

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        s = sessionmaker(bind=engine)()
        # 加自定义字段 + 一个系统字段
        FieldService(s).add_field("student", "hobby", "兴趣爱好", "string")
        fd = FieldService(s).add_field("student", "sys_hidden", "系统字段", "string")
        fd.is_system = True
        s.commit()

        headers = ExportService.template_for("student", session=s)
        assert "兴趣爱好" in headers  # 自定义字段追加
        assert "系统字段" not in headers  # 系统字段不追加
        s.close()

    def test_template_no_session_backward_compat(self):
        """无 session 时保持基础模板（向后兼容）"""
        headers = ExportService.template_for("teacher")
        assert headers == ["工号", "姓名", "性别", "科目", "联系电话", "邮箱"]

    def test_preview(self):
        """数据预览"""
        prev = ExportService.preview(SAMPLE_ROWS, limit=2)
        assert prev["total"] == 3
        assert len(prev["preview"]) == 2
        assert "学号" in prev["columns"]

    def test_filename_timestamp(self):
        """文件名含时间戳"""
        result = export_service.export(SAMPLE_ROWS, ExportOptions(format="csv"))
        assert "_20" in result.filename  # 时间戳 YYYYMMDD_HHMMSS

    def test_filename_custom(self):
        """自定义文件名不带时间戳"""
        result = export_service.export(
            SAMPLE_ROWS,
            ExportOptions(format="csv", filename="成绩单", include_timestamp=False),
        )
        assert result.filename == "成绩单.csv"
