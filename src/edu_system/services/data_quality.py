"""
数据质量服务 — Pandera DataFrame Schema 验证
支持：Schema 校验、自动画像、异常检测、业务规则检查
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import pandera as pa
from pandera.typing import Series  # noqa: TC002 运行时用于 DataFrameModel 字段注解

# ===== 常用数据质量 Schema =====


class StudentSchema(pa.DataFrameModel):
    """学生数据 Schema"""

    学号: Series[str] = pa.Field(str_matches=r"^\d{4,20}$", unique=True)
    姓名: Series[str] = pa.Field(str_length={"min_value": 2, "max_value": 30})
    性别: Series[str] = pa.Field(isin=["男", "女"])
    年级: Series[str] = pa.Field()
    班级: Series[str] = pa.Field()
    出生日期: Series[str] = pa.Field(nullable=True)
    联系电话: Series[str] = pa.Field(nullable=True, str_matches=r"^1\d{10}$")

    class Config:
        strict = False  # 允许多余列


class TeacherSchema(pa.DataFrameModel):
    """教师数据 Schema"""

    工号: Series[str] = pa.Field(str_matches=r"^\d{4,20}$", unique=True)
    姓名: Series[str] = pa.Field(str_length={"min_value": 2, "max_value": 30})
    性别: Series[str] = pa.Field(isin=["男", "女"], nullable=True)
    科目: Series[str] = pa.Field(nullable=True)
    联系电话: Series[str] = pa.Field(nullable=True, str_matches=r"^1\d{10}$")
    邮箱: Series[str] = pa.Field(nullable=True, str_matches=r"^[\w.+-]+@[\w-]+\.[\w.]+$")

    class Config:
        strict = False


class ScoreSchema(pa.DataFrameModel):
    """成绩数据 Schema"""

    考试: Series[str] = pa.Field()
    学号: Series[str] = pa.Field(str_matches=r"^\d{4,20}$")
    科目: Series[str] = pa.Field()
    成绩: Series[float] = pa.Field(nullable=True, ge=0, le=150)

    class Config:
        strict = False


# Schema 注册表
SCHEMAS: dict[str, type[pa.DataFrameModel]] = {
    "student": StudentSchema,
    "teacher": TeacherSchema,
    "score": ScoreSchema,
}


def _schema_columns(schema_cls: type[pa.DataFrameModel]) -> dict[str, dict[str, Any]]:
    """提取 DataFrameModel 的列定义（列名 -> 属性信息）"""
    info: dict[str, dict[str, Any]] = {}
    try:
        schema = schema_cls.to_schema()
    except Exception:
        return info
    for name, column in schema.columns.items():
        info[name] = {"nullable": bool(getattr(column, "nullable", False))}
    return info


def _extract_column_from_message(message: str) -> str:
    """从 pandera 错误消息提取列名（如 \"Column '联系电话'...\" 或 \"series '学号'...\"）"""
    import re

    match = re.search(r"(?:Column|series|column) '([^']+)'", message, re.IGNORECASE)
    return match.group(1) if match else ""


@dataclass
class QualityIssue:
    """质量问题"""

    row_index: int  # 0-based 行号
    column: str
    message: str
    severity: str = "error"  # error/warning


@dataclass
class QualityReport:
    """质量报告"""

    entity: str
    total_rows: int = 0
    passed: bool = True
    issues: list[QualityIssue] = field(default_factory=list)
    column_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def summary(self) -> dict[str, Any]:
        """摘要（API 友好）"""
        return {
            "entity": self.entity,
            "total_rows": self.total_rows,
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [
                {
                    "row_index": i.row_index,
                    "column": i.column,
                    "message": i.message,
                    "severity": i.severity,
                }
                for i in self.issues
            ],
        }


class DataQualityService:
    """数据质量验证服务"""

    @staticmethod
    def validate(entity: str, data: list[dict[str, Any]]) -> QualityReport:
        """按实体类型验证数据

        Args:
            entity: student/teacher/score
            data: 数据行列表

        Returns:
            QualityReport: 质量报告
        """
        schema_cls = SCHEMAS.get(entity)
        report = QualityReport(entity=entity, total_rows=len(data))

        if not schema_cls:
            report.passed = False
            report.issues.append(QualityIssue(0, "", f"未知实体类型: {entity}"))
            return report

        if not data:
            report.passed = True
            return report

        df = pd.DataFrame(data)

        # 1. 补齐 schema 中可空但数据缺省的列（容缺失列）
        for col, col_info in _schema_columns(schema_cls).items():
            if col not in df.columns and col_info.get("nullable", False):
                df[col] = None

        # 2. 列画像
        report.column_profiles = DataQualityService._profile(df)

        # 3. Schema 验证
        try:
            schema_cls.validate(df)
        except pa.errors.SchemaErrors as e:
            report.passed = False
            for err in e.schema_errors:
                row_idx = int(err.data["index"]) if "index" in err.data else 0
                report.issues.append(
                    QualityIssue(
                        row_index=row_idx,
                        column=str(err.data.get("column", "")),
                        message=err.message,
                        severity="error",
                    )
                )
        except pa.errors.SchemaError as e:
            report.passed = False
            err_msg = str(e)
            report.issues.append(
                QualityIssue(
                    row_index=0,
                    column=_extract_column_from_message(err_msg),
                    message=err_msg,
                    severity="error",
                )
            )

        # 3. 业务规则补充检查
        DataQualityService._business_checks(entity, df, report)

        report.passed = report.error_count == 0
        return report

    @staticmethod
    def _profile(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
        """自动画像：每列的统计信息"""
        profiles: dict[str, dict[str, Any]] = {}
        for col in df.columns:
            series = df[col]
            profile: dict[str, Any] = {
                "dtype": str(series.dtype),
                "non_null": int(series.notna().sum()),
                "null_count": int(series.isna().sum()),
                "unique_count": int(series.nunique()),
            }
            if pd.api.types.is_numeric_dtype(series):
                profile.update(
                    {
                        "min": float(series.min()) if series.notna().any() else None,
                        "max": float(series.max()) if series.notna().any() else None,
                        "mean": round(float(series.mean()), 2) if series.notna().any() else None,
                    }
                )
            elif pd.api.types.is_object_dtype(series):
                profile["sample_values"] = series.dropna().astype(str).unique()[:5].tolist()
            profiles[str(col)] = profile
        return profiles

    @staticmethod
    def _business_checks(entity: str, df: pd.DataFrame, report: QualityReport) -> None:
        """业务规则检查（Schema 之外）"""
        if entity == "score":
            # 成绩重复检查（同一考试+学号+科目）
            if all(c in df.columns for c in ("考试", "学号", "科目")):
                dup = df.duplicated(subset=["考试", "学号", "科目"], keep=False)
                for idx in df.index[dup]:
                    report.issues.append(
                        QualityIssue(
                            row_index=int(idx),
                            column="成绩",
                            message="重复记录：同一考试+学号+科目",
                            severity="warning",
                        )
                    )

        elif entity == "student" and "联系电话" in df.columns:
            # 电话号码为空预警
            for idx in df.index[df["联系电话"].isna()]:
                report.issues.append(
                    QualityIssue(
                        row_index=int(idx),
                        column="联系电话",
                        message="缺少联系电话",
                        severity="warning",
                    )
                )


data_quality_service = DataQualityService()
