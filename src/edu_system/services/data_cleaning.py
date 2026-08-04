"""
数据清洗管道 — 通用字段标准化/去重/缺失填补/错误隔离
纯 DataFrame 操作，无 DB 依赖，可独立测试复用
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class CleaningConfig:
    """清洗配置"""

    # 去重键（None = 不去重）
    dedup_keys: list[str] | None = None
    # 缺失值填补规则: {列名: 填补值}
    fill_missing: dict[str, Any] = field(default_factory=dict)
    # 去空格列
    strip_columns: list[str] = field(default_factory=list)
    # 性别标准化
    normalize_gender: bool = False
    # 手机号校验列
    phone_columns: list[str] = field(default_factory=list)


@dataclass
class CleaningResult:
    """清洗结果"""

    cleaned: pd.DataFrame
    dropped_rows: int = 0
    filled_cells: int = 0
    issues: list[dict[str, str]] = field(default_factory=list)  # {row, column, message}

    def summary(self) -> dict[str, Any]:
        return {
            "rows_after": len(self.cleaned),
            "dropped_rows": self.dropped_rows,
            "filled_cells": self.filled_cells,
            "issue_count": len(self.issues),
        }


class DataCleaningPipeline:
    """数据清洗管道"""

    GENDER_MAP = {"男": "男", "女": "女", "m": "男", "f": "女", "male": "男", "female": "女"}

    def __init__(self, config: CleaningConfig | None = None):
        self.config = config or CleaningConfig()

    def run(self, df: pd.DataFrame) -> CleaningResult:
        """执行完整清洗管道"""
        result = CleaningResult(cleaned=df.copy())
        result.cleaned = self._normalize_columns(result.cleaned)
        result.cleaned = self._strip_text(result.cleaned)
        result.cleaned, filled = self._fill_missing(result.cleaned)
        result.filled_cells = filled
        if self.config.normalize_gender:
            result.cleaned = self._normalize_gender_values(result.cleaned)
        result.cleaned, dropped, issues = self._validate_phones(result.cleaned)
        result.dropped_rows += dropped
        result.issues.extend(issues)
        result.cleaned, dropped, issues = self._dedup(result.cleaned)
        result.dropped_rows += dropped
        result.issues.extend(issues)
        return result

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """列名标准化：去首尾空格、统一空白"""
        df = df.copy()
        df.columns = [str(c).strip().replace("\u3000", " ").replace("  ", "") for c in df.columns]
        return df

    def _strip_text(self, df: pd.DataFrame) -> pd.DataFrame:
        """去首尾空格"""
        df = df.copy()
        for col in df.columns:
            if self.config.strip_columns and col not in self.config.strip_columns:
                continue
            if pd.api.types.is_string_dtype(df[col]):
                df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)
        return df

    def _fill_missing(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        """缺失值填补"""
        df = df.copy()
        filled = 0
        for col, value in self.config.fill_missing.items():
            if col in df.columns:
                mask = df[col].isna()
                df.loc[mask, col] = value
                filled += int(mask.sum())
        return df, filled

    def _normalize_gender_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """性别值标准化"""
        df = df.copy()
        for col in df.columns:
            if "性别" in str(col):
                df[col] = df[col].map(lambda v: self.GENDER_MAP.get(str(v).strip().lower(), v))
        return df

    def _validate_phones(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int, list[dict]]:
        """手机号校验（非法行标记错误但保留，由调用方决定）"""
        issues: list[dict[str, str]] = []
        for col in self.config.phone_columns:
            if col not in df.columns:
                continue
            for idx, val in df[col].items():
                if pd.isna(val):
                    continue
                s = str(val).strip()
                if not (s.isdigit() and len(s) == 11 and s.startswith("1")):
                    issues.append(
                        {"row": str(idx), "column": col, "message": f"手机号格式非法: {s}"}
                    )
        return df, 0, issues

    def _dedup(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int, list[dict]]:
        """按指定键去重（保留首行）"""
        keys = self.config.dedup_keys or []
        keys = [k for k in keys if k in df.columns]
        if not keys:
            return df, 0, []
        before = len(df)
        df = df.drop_duplicates(subset=keys, keep="first")
        dropped = before - len(df)
        issues = [{"row": "-", "column": ",".join(keys), "message": f"重复行已去重 ({dropped} 行)"}]
        return df, dropped, issues


def standardize_gender(value: Any) -> str:
    """单值性别标准化（供非 DataFrame 场景复用）"""
    if value is None:
        return ""
    return DataCleaningPipeline.GENDER_MAP.get(str(value).strip().lower(), str(value).strip())


def normalize_phone(value: Any) -> str | None:
    """单值手机号标准化：去空格/横线，返回纯数字或 None"""
    if value is None:
        return None
    s = str(value).strip().replace(" ", "").replace("-", "")
    return s if s.isdigit() else None


data_cleaning_pipeline = DataCleaningPipeline()
