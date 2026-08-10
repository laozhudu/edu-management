"""
base — 模型基座：Base + 通用列/工具

域模型文件通过 `from edu_system.models.base import *` 引入全部通用符号。
__all__ 明确导出，防止 ruff 误删间接使用的 import。
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

__all__ = [
    "JSON",
    "Boolean",
    "Column",
    "Date",
    "DateTime",
    "Float",
    "ForeignKey",
    "Index",
    "Integer",
    "LargeBinary",
    "String",
    "Text",
    "Time",
    "UniqueConstraint",
    "func",
    "SQLEnum",
    "declarative_base",
    "relationship",
    "Base",
    "enum",
    "datetime",
    "_ext_json_column",
]


def _ext_json_column() -> Column:
    """返回通用 ext_json 扩展列定义（JSON 文本）"""
    return Column(Text, nullable=True, comment="自定义扩展字段（JSON 对象）")
