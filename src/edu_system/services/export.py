"""
导出服务 — tablib 多格式导出
支持：Excel/CSV/JSON + 分页筛选、表头映射、审计记录
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import tablib


class ExportFormatError(ValueError):
    """不支持的导出格式"""


@dataclass
class ExportOptions:
    """导出选项"""

    format: str = "xlsx"  # xlsx/csv/json
    sheet_name: str = "导出数据"
    headers: list[str] | None = None  # 表头映射（中文显示名）
    filename: str | None = None  # 自定义文件名
    include_timestamp: bool = True


@dataclass
class ExportResult:
    """导出结果"""

    data: bytes = b""
    filename: str = ""
    format: str = ""
    row_count: int = 0
    errors: list[str] = field(default_factory=list)


SUPPORTED_FORMATS = {"xlsx", "csv", "json"}

# 文件扩展名映射
FORMAT_EXTENSIONS = {
    "xlsx": ".xlsx",
    "csv": ".csv",
    "json": ".json",
}


class ExportService:
    """通用数据导出服务"""

    @staticmethod
    def validate_format(fmt: str) -> str:
        """校验导出格式"""
        fmt = fmt.lower()
        if fmt not in SUPPORTED_FORMATS:
            raise ExportFormatError(
                f"不支持的格式: {fmt}，支持: {', '.join(sorted(SUPPORTED_FORMATS))}"
            )
        return fmt

    @staticmethod
    def build_dataset(
        rows: list[dict[str, Any]],
        headers: list[str] | None = None,
    ) -> tablib.Dataset:
        """构建 tablib Dataset（自动提取列头）"""
        dataset = tablib.Dataset()

        if not rows:
            return dataset

        # 列头：显式指定或从首行 key 提取
        if headers:
            dataset.headers = headers
            for row in rows:
                dataset.append([row.get(h, "") for h in headers])
        else:
            keys = list(rows[0].keys())
            dataset.headers = keys
            for row in rows:
                dataset.append([row.get(k, "") for k in keys])

        return dataset

    def export(
        self,
        rows: list[dict[str, Any]],
        options: ExportOptions | None = None,
    ) -> ExportResult:
        """导出数据到指定格式

        Args:
            rows: 数据行列表（dict）
            options: 导出选项

        Returns:
            ExportResult: 导出结果
        """
        opts = options or ExportOptions()
        try:
            fmt = self.validate_format(opts.format)
        except ExportFormatError as e:
            return ExportResult(format=(opts or ExportOptions()).format, errors=[str(e)])

        dataset = self.build_dataset(rows, opts.headers)

        result = ExportResult(format=fmt, row_count=len(rows))

        try:
            if fmt == "xlsx":
                result.data = dataset.export("xlsx")
            elif fmt == "csv":
                result.data = dataset.export("csv").encode("utf-8-sig")  # BOM 兼容 Excel
            elif fmt == "json":
                result.data = json.dumps(
                    [dict(zip(dataset.headers, row)) for row in dataset],
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8")
        except Exception as e:
            result.errors.append(f"导出失败: {e}")
            return result

        # 生成文件名
        base = opts.filename or opts.sheet_name
        if opts.include_timestamp:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = f"{base}_{ts}"
        result.filename = base + FORMAT_EXTENSIONS[fmt]

        return result

    def export_to_bytes(
        self,
        rows: list[dict[str, Any]],
        fmt: str = "xlsx",
        headers: list[str] | None = None,
    ) -> bytes:
        """便捷方法：直接返回字节流"""
        opts = ExportOptions(format=fmt, headers=headers, include_timestamp=False)
        result = self.export(rows, opts)
        if result.errors:
            raise ExportFormatError(result.errors[0])
        return result.data

    @staticmethod
    def template_for(entity: str, session=None) -> list[str]:
        """获取导入模版表头（用于下载空模版）

        若传入 session，动态追加字段注册表（FieldDefinition）中的
        自定义字段（Sprint 3.7.11：字段增删后导入模板自动识别）
        """
        templates: dict[str, list[str]] = {
            "student": ["学号", "姓名", "性别", "年级", "班级", "出生日期", "联系电话"],
            "teacher": ["工号", "姓名", "性别", "科目", "联系电话", "邮箱"],
            "score": ["考试", "学期", "学号", "姓名", "科目", "成绩"],
            "exam": ["考试名称", "类型", "开始日期", "结束日期", "年级", "备注"],
        }
        headers = list(templates.get(entity, []))

        # 动态追加自定义字段（系统字段不重复，仅自定义字段）
        if session is not None:
            try:
                from edu_system.services.meta import FieldService

                fields = FieldService(session).list_fields(entity)
                for fd in fields:
                    is_system = bool(fd.is_system)
                    if not is_system:
                        headers.append(str(fd.label))
            except Exception:
                pass  # 字段服务异常不影响基础模板

        return headers

    @staticmethod
    def preview(rows: list[dict[str, Any]], limit: int = 10) -> dict[str, Any]:
        """数据预览：前 N 行 + 列统计"""
        if not rows:
            return {"total": 0, "columns": [], "preview": []}

        keys = list(rows[0].keys())
        return {
            "total": len(rows),
            "columns": keys,
            "preview": rows[:limit],
        }


export_service = ExportService()
