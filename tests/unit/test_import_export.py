"""
导入导出服务单元测试
验证：文件解析、字段映射、预览流水线（清洗+验证+错误隔离）、确认入库、回滚
"""

import json

import pandas as pd
import pytest

from edu_system.services.import_export import (
    ImportExportService,
    ImportFormatError,
    ImportOptions,
    import_export_service,
)

VALID_ROWS = [
    {
        "学号": "2024001",
        "姓名": "张三",
        "性别": "男",
        "年级": "初三",
        "班级": "1班",
        "联系电话": "13800138000",
    },
    {
        "学号": "2024002",
        "姓名": "李四",
        "性别": "女",
        "年级": "初三",
        "班级": "1班",
        "联系电话": "13900139000",
    },
]


class TestParse:
    def test_parse_csv_bytes(self):
        """CSV 字节流解析"""
        data = "学号,姓名,性别\n2024001,张三,男\n".encode()
        df = ImportExportService.parse_bytes(data, "csv")
        assert len(df) == 1
        assert df.iloc[0]["姓名"] == "张三"

    def test_parse_json_bytes(self):
        """JSON 字节流解析"""
        data = json.dumps(VALID_ROWS).encode("utf-8")
        df = ImportExportService.parse_bytes(data, "json")
        assert len(df) == 2

    def test_parse_unsupported(self):
        """不支持格式抛异常"""
        with pytest.raises(ImportFormatError):
            ImportExportService.parse_bytes(b"", "pdf")

    def test_parse_missing_file(self):
        """文件不存在抛异常"""
        with pytest.raises(ImportFormatError):
            ImportExportService.parse_file("/nonexistent/x.xlsx")

    def test_parse_csv_file(self, tmp_path):
        """CSV 文件解析"""
        p = tmp_path / "students.csv"
        p.write_text("学号,姓名\n2024001,张三\n", encoding="utf-8")
        df = ImportExportService.parse_file(p)
        assert len(df) == 1


class TestMapping:
    def test_field_mapping(self):
        """字段映射：源列名 → 标准列名"""
        df = pd.DataFrame({"学号": ["2024001"], "学生姓名": ["张三"], "性别": ["男"]})
        mapped = ImportExportService.apply_mapping(df, {"姓名": "学生姓名"})
        assert "姓名" in mapped.columns
        assert mapped.iloc[0]["姓名"] == "张三"


class TestPreviewPipeline:
    def test_preview_valid(self):
        """合法数据预览通过"""
        df = pd.DataFrame(VALID_ROWS)
        options = ImportOptions(entity="student")
        stage = import_export_service.preview(options, df)
        assert stage.quality_report["error_count"] == 0
        assert len(stage.rows_to_insert) == 2

    def test_preview_error_isolation(self):
        """错误行隔离：非法手机号行不进入待插入"""
        rows = VALID_ROWS + [
            {
                "学号": "2024003",
                "姓名": "王五",
                "性别": "男",
                "年级": "初三",
                "班级": "1班",
                "联系电话": "123",
            }
        ]
        df = pd.DataFrame(rows)
        options = ImportOptions(entity="student")
        stage = import_export_service.preview(options, df)
        assert stage.quality_report["error_count"] >= 1
        assert len(stage.rows_to_insert) == 2  # 非法行被隔离

    def test_preview_dedup(self):
        """预览阶段去重"""
        rows = VALID_ROWS + [dict(VALID_ROWS[0])]
        df = pd.DataFrame(rows)
        options = ImportOptions(entity="student", dedup_keys=["学号"])
        stage = import_export_service.preview(options, df)
        assert len(stage.rows_to_insert) == 2  # 重复学号行被清洗掉

    def test_preview_gender_normalize(self):
        """预览阶段性别标准化"""
        rows = [
            {"学号": "2024001", "姓名": "张三", "性别": "m", "年级": "初三", "班级": "1班"},
        ]
        df = pd.DataFrame(rows)
        options = ImportOptions(entity="student", normalize_gender=True)
        stage = import_export_service.preview(options, df)
        assert stage.cleaned_df.iloc[0]["性别"] == "男"


class TestImportRows:
    def test_import_success(self):
        """确认入库成功"""
        df = pd.DataFrame(VALID_ROWS)
        options = ImportOptions(entity="student")
        stage = import_export_service.preview(options, df)
        result = import_export_service.import_rows(options, stage, insert_fn=len)
        assert result.success is True
        assert result.inserted == 2

    def test_import_progress_callback(self):
        """进度回调被调用"""
        calls = []
        df = pd.DataFrame(VALID_ROWS)
        options = ImportOptions(entity="student", on_progress=lambda a, b: calls.append((a, b)))
        stage = import_export_service.preview(options, df)
        result = import_export_service.import_rows(options, stage, insert_fn=len)
        assert result.success
        assert len(calls) >= 2

    def test_import_audit(self):
        """审计回调收到统计信息"""
        audits = []
        df = pd.DataFrame(VALID_ROWS)
        options = ImportOptions(entity="student")
        stage = import_export_service.preview(options, df)
        result = import_export_service.import_rows(
            options, stage, insert_fn=len, audit_fn=audits.append
        )
        assert len(audits) == 1
        assert audits[0]["entity"] == "student"
        assert audits[0]["inserted"] == 2

    def test_import_rollback_on_error(self):
        """入库抛异常时报告失败（回滚语义）"""

        def bad_insert(rows):
            raise RuntimeError("数据库连接断开")

        df = pd.DataFrame(VALID_ROWS)
        options = ImportOptions(entity="student")
        stage = import_export_service.preview(options, df)
        result = import_export_service.import_rows(options, stage, insert_fn=bad_insert)
        assert result.success is False
        assert any("回滚" in m for m in result.error_messages)

    def test_import_empty_rows(self):
        """无有效行时提示"""
        rows = [
            {
                "学号": "2024003",
                "姓名": "王五",
                "性别": "男",
                "年级": "初三",
                "班级": "1班",
                "联系电话": "123",
            }
        ]
        df = pd.DataFrame(rows)
        options = ImportOptions(entity="student")
        stage = import_export_service.preview(options, df)
        result = import_export_service.import_rows(options, stage, insert_fn=len)
        assert result.inserted == 0
        assert any("没有可插入" in m for m in result.error_messages)

    def test_summary(self):
        """摘要包含错误信息"""
        df = pd.DataFrame(VALID_ROWS)
        options = ImportOptions(entity="student")
        stage = import_export_service.preview(options, df)
        result = import_export_service.import_rows(options, stage, insert_fn=len)
        s = result.summary()
        assert s["success"] is True
        assert s["inserted"] == 2
