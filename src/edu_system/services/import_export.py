"""
导入导出服务 — 通用导入编排
流水线: 解析文件 → 数据清洗 → 质量验证 → 预览(不落库) → 确认入库(事务+回滚) → 审计
支持: CSV/Excel/JSON、任意实体、字段映射、错误行定位
"""

from __future__ import annotations

import io
import json
from collections.abc import Callable  # noqa: TC003 运行时仅用于类型注解
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from edu_system.services.data_cleaning import CleaningConfig, DataCleaningPipeline
from edu_system.services.data_quality import data_quality_service


class ImportFormatError(ValueError):
    """导入文件格式错误"""


class ImportValidationError(ValueError):
    """数据验证失败（预览阶段阻止入库）"""


@dataclass
class ImportOptions:
    """导入选项"""

    entity: str = "student"  # student/teacher/score
    format: str = "xlsx"  # xlsx/csv/json
    dedup_keys: list[str] | None = None  # 去重键
    fill_missing: dict[str, Any] = field(default_factory=dict)
    normalize_gender: bool = False
    phone_columns: list[str] = field(default_factory=list)
    # 字段映射: {标准列名: 源文件列名}
    field_mapping: dict[str, str] = field(default_factory=dict)
    # 回调
    on_progress: Callable[[int, int], None] | None = None  # (已处理, 总数)


@dataclass
class ImportStage:
    """导入流水线各阶段产物"""

    raw_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    cleaned_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    quality_report: dict[str, Any] = field(default_factory=dict)
    rows_to_insert: list[dict[str, Any]] = field(default_factory=list)
    row_errors: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ImportResult:
    """导入结果"""

    success: bool = False
    stage: ImportStage = field(default_factory=ImportStage)
    inserted: int = 0
    error_messages: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "inserted": self.inserted,
            "error_count": len(self.error_messages),
            "errors": self.error_messages[:20],
            "quality": self.stage.quality_report,
        }


# 各实体的标准列名（用于字段映射默认值）
ENTITY_COLUMNS: dict[str, list[str]] = {
    "student": ["学号", "姓名", "性别", "年级", "班级", "出生日期", "联系电话"],
    "teacher": ["工号", "姓名", "性别", "科目", "联系电话", "邮箱"],
    "score": ["考试", "学期", "学号", "姓名", "科目", "成绩"],
}


class ImportExportService:
    """通用导入编排服务（预览/回滚/审计）"""

    @staticmethod
    def parse_file(
        file_path: str | Path,
        fmt: str | None = None,
    ) -> pd.DataFrame:
        """解析文件为 DataFrame

        Args:
            file_path: 文件路径
            fmt: 格式（默认按扩展名推断）

        Raises:
            ImportFormatError: 格式不支持或解析失败
        """
        path = Path(file_path)
        if not path.exists():
            raise ImportFormatError(f"文件不存在: {path}")

        fmt = fmt or path.suffix.lstrip(".").lower()
        try:
            if fmt in ("xlsx", "xls"):
                return pd.read_excel(path)
            if fmt == "csv":
                return pd.read_csv(path, dtype=str)
            if fmt == "json":
                return pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
            raise ImportFormatError(f"不支持的文件格式: {fmt}")  # noqa: TRY301 显式抛出格式错误
        except ImportFormatError:  # noqa: TRY301 显式透传格式错误
            raise
        except Exception as e:
            raise ImportFormatError(f"解析失败: {e}") from e

    @staticmethod
    def parse_bytes(data: bytes, fmt: str) -> pd.DataFrame:
        """解析字节流（供 API 上传场景）"""
        try:
            if fmt in ("xlsx", "xls"):
                return pd.read_excel(io.BytesIO(data))
            if fmt == "csv":
                return pd.read_csv(io.BytesIO(data), dtype=str)
            if fmt == "json":
                return pd.DataFrame(json.loads(data.decode("utf-8")))
            raise ImportFormatError(f"不支持的文件格式: {fmt}")  # noqa: TRY301 显式抛出格式错误
        except ImportFormatError:  # noqa: TRY301 显式透传格式错误
            raise
        except Exception as e:
            raise ImportFormatError(f"解析失败: {e}") from e

    @staticmethod
    def apply_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
        """应用字段映射: {标准列名: 源列名}"""
        if not mapping:
            return df
        df = df.copy()
        for std_col, src_col in mapping.items():
            if src_col in df.columns and std_col not in df.columns:
                df = df.rename(columns={src_col: std_col})
        return df

    @staticmethod
    def build_cleaning_config(options: ImportOptions) -> CleaningConfig:
        """根据导入选项构造清洗配置"""
        dedup_keys = options.dedup_keys or (["学号"] if options.entity == "student" else None)
        phone_cols = options.phone_columns or (
            ["联系电话"] if options.entity in ("student", "teacher") else []
        )
        return CleaningConfig(
            dedup_keys=dedup_keys,
            fill_missing=options.fill_missing,
            normalize_gender=options.normalize_gender,
            phone_columns=phone_cols,
        )

    def preview(self, options: ImportOptions, df: pd.DataFrame) -> ImportStage:
        """预览阶段：清洗 + 验证，不落库

        Returns:
            ImportStage: 含清洗结果、质量报告、待插入行、错误行
        """
        stage = ImportStage()

        # 1. 字段映射
        mapped = self.apply_mapping(df, options.field_mapping)

        # 2. 数据清洗
        pipeline = DataCleaningPipeline(self.build_cleaning_config(options))
        cleaning_result = pipeline.run(mapped)
        stage.raw_df = df
        stage.cleaned_df = cleaning_result.cleaned

        # 3. 质量验证
        records = cleaning_result.cleaned.to_dict(orient="records")
        quality = data_quality_service.validate(options.entity, records)
        stage.quality_report = quality.summary()

        # 4. 隔离错误行
        error_rows = {str(i.row_index) for i in quality.issues if i.severity == "error"}
        stage.row_errors = [
            {
                "row_index": i.row_index,
                "column": i.column,
                "message": i.message,
            }
            for i in quality.issues
            if i.severity == "error"
        ]
        stage.rows_to_insert = [r for idx, r in enumerate(records) if str(idx) not in error_rows]

        return stage

    def import_rows(
        self,
        options: ImportOptions,
        stage: ImportStage,
        insert_fn: Callable[[list[dict[str, Any]]], int],
        audit_fn: Callable[[dict[str, Any]], None] | None = None,
    ) -> ImportResult:
        """确认入库阶段：事务性写入 + 审计

        Args:
            options: 导入选项
            stage: 预览阶段产物
            insert_fn: 实际入库函数（返回插入行数），由调用方实现
            audit_fn: 审计回调

        Returns:
            ImportResult: 导入结果
        """
        result = ImportResult(stage=stage)

        if stage.quality_report.get("error_count", 0) > 0:
            result.error_messages.append(
                f"存在 {stage.quality_report['error_count']} 个错误行，已隔离，未入库"
            )

        # 无待插入行
        if not stage.rows_to_insert:
            result.error_messages.append("没有可插入的有效数据行")
            result.success = True  # 空导入视为成功（无副作用）
            return result

        try:
            # 进度回调
            total = len(stage.rows_to_insert)
            if options.on_progress:
                options.on_progress(0, total)

            inserted = insert_fn(stage.rows_to_insert)
            result.inserted = inserted

            if options.on_progress:
                options.on_progress(inserted, total)

            # 审计
            if audit_fn:
                audit_fn(
                    {
                        "entity": options.entity,
                        "inserted": inserted,
                        "total_valid": total,
                        "errors": len(stage.row_errors),
                    }
                )

            result.success = True
        except Exception as e:
            result.error_messages.append(f"入库失败（已回滚）: {e}")

        return result


import_export_service = ImportExportService()
