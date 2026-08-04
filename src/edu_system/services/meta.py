"""
字段元数据服务 — 动态字段增删（Sprint 3.7 核心）

职责：
1. FieldDefinition 注册表 CRUD（增/删/改/查自定义字段）
2. 实体 ext_json 读写（get/set 自定义字段值）
3. 字段校验（类型/必填/枚举）

设计：
- 系统字段 is_system=1 不可删除（保护核心结构）
- 自定义字段写入实体 ext_json（JSON 对象），零表结构变更
- 查询用 SQLite JSON1 json_extract（低频字段）；高频字段可提升为真实列（迁移脚本）
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from edu_system.models import FieldDefinition

# 实体类型白名单（可扩展字段的业务实体）
ENTITY_TYPES = ("student", "teacher", "class", "exam", "score")

# 字段类型白名单
FIELD_TYPES = ("string", "int", "float", "date", "enum", "select", "bool")


class FieldValidationError(ValueError):
    """字段校验错误"""


class FieldService:
    """字段注册表 + ext_json 读写服务"""

    def __init__(self, session: Session):
        self._session = session

    # ── 字段定义 CRUD ──
    def list_fields(self, entity_type: str) -> list[FieldDefinition]:
        """查询某实体的全部字段定义（按 sort_order 排序）"""
        self._check_entity(entity_type)
        return (
            self._session.query(FieldDefinition)
            .filter_by(entity_type=entity_type)
            .order_by(FieldDefinition.sort_order, FieldDefinition.id)
            .all()
        )

    def get_field(self, entity_type: str, field_key: str) -> FieldDefinition | None:
        return (
            self._session.query(FieldDefinition)
            .filter_by(entity_type=entity_type, field_key=field_key)
            .first()
        )

    def add_field(
        self,
        entity_type: str,
        field_key: str,
        label: str,
        field_type: str = "string",
        options: list | None = None,
        required: bool = False,
        sort_order: int = 0,
        created_by: str | None = None,
    ) -> FieldDefinition:
        """新增自定义字段（field_key 唯一）"""
        self._check_entity(entity_type)
        if field_type not in FIELD_TYPES:
            raise FieldValidationError(f"不支持的字段类型: {field_type}")
        if not field_key or not field_key.isidentifier():
            raise FieldValidationError(f"非法字段键: {field_key}")
        if self.get_field(entity_type, field_key):
            raise FieldValidationError(f"字段已存在: {entity_type}.{field_key}")
        if field_type in ("enum", "select") and not options:
            raise FieldValidationError("枚举/选择字段必须提供 options")

        fd = FieldDefinition(
            entity_type=entity_type,
            field_key=field_key,
            label=label,
            field_type=field_type,
            options=json.dumps(options, ensure_ascii=False) if options else None,
            required=required,
            sort_order=sort_order,
            is_system=False,
            created_by=created_by,
        )
        self._session.add(fd)
        self._session.commit()
        return fd

    def update_field(
        self,
        entity_type: str,
        field_key: str,
        label: str | None = None,
        field_type: str | None = None,
        options: list | None = None,
        required: bool | None = None,
        sort_order: int | None = None,
    ) -> FieldDefinition:
        """修改自定义字段定义"""
        fd = self.get_field(entity_type, field_key)
        if not fd:
            raise FieldValidationError(f"字段不存在: {entity_type}.{field_key}")
        if label is not None:
            fd.label = label
        if field_type is not None:
            if field_type not in FIELD_TYPES:
                raise FieldValidationError(f"不支持的字段类型: {field_type}")
            fd.field_type = field_type
        if options is not None:
            fd.options = json.dumps(options, ensure_ascii=False)
        if required is not None:
            fd.required = required
        if sort_order is not None:
            fd.sort_order = sort_order
        self._session.commit()
        return fd

    def delete_field(self, entity_type: str, field_key: str) -> bool:
        """删除自定义字段（系统字段受保护）"""
        fd = self.get_field(entity_type, field_key)
        if not fd:
            return False
        if fd.is_system:
            raise FieldValidationError(f"系统字段不可删除: {entity_type}.{field_key}")
        self._session.delete(fd)
        self._session.commit()
        return True

    # ── 实体 ext_json 读写 ──
    @staticmethod
    def get_value(entity, field_key: str, default: Any = None) -> Any:
        """读取实体自定义字段值"""
        if not entity or not getattr(entity, "ext_json", None):
            return default
        try:
            data = json.loads(entity.ext_json)
        except (TypeError, json.JSONDecodeError):
            return default
        return data.get(field_key, default)

    @staticmethod
    def set_value(entity, field_key: str, value: Any) -> None:
        """写入实体自定义字段值（保留其他字段）"""
        data = {}
        if getattr(entity, "ext_json", None):
            try:
                data = json.loads(entity.ext_json)
            except (TypeError, json.JSONDecodeError):
                data = {}
        data[field_key] = value
        entity.ext_json = json.dumps(data, ensure_ascii=False)

    def validate_value(self, entity_type: str, field_key: str, value: Any) -> Any:
        """按字段定义校验并规范化值（类型/必填/枚举）"""
        fd = self.get_field(entity_type, field_key)
        if not fd:
            raise FieldValidationError(f"字段未定义: {entity_type}.{field_key}")
        # 必填
        if fd.required and value in (None, ""):
            raise FieldValidationError(f"字段必填: {fd.label}")

        if value in (None, ""):
            return None

        # 类型转换与校验（映射表 + 转换器函数，避免分支过多）
        converters = {
            "int": int,
            "float": float,
            "bool": lambda v: (
                bool(v) if isinstance(v, bool) else str(v).lower() in ("1", "true", "是", "yes")
            ),
            "date": self._convert_date,
        }
        try:
            if fd.field_type in converters:
                return converters[fd.field_type](value)
            if fd.field_type in ("enum", "select"):
                options = json.loads(fd.options) if fd.options else []
                if str(value) not in [str(o) for o in options]:
                    raise FieldValidationError(f"非法选项: {value}（可选: {options}）")
                return str(value)
        except (ValueError, TypeError) as e:
            raise FieldValidationError(f"字段格式错误: {fd.label}（{e}）") from e

        return value

    @staticmethod
    def _convert_date(value: Any):
        from datetime import date, datetime

        if isinstance(value, date):
            return value
        return datetime.strptime(str(value), "%Y-%m-%d").date()

    # ── 实体级 ext_json 批量读写（API 层调用）──
    ENTITY_MODELS = {}  # 延迟导入填充，见下方 _get_model

    @staticmethod
    def _get_model(entity_type: str):
        """实体类型 → ORM 模型类"""
        if not FieldService.ENTITY_MODELS:
            from edu_system.models import Class, Exam, Score, Student, Teacher

            FieldService.ENTITY_MODELS = {
                "student": Student,
                "teacher": Teacher,
                "class": Class,
                "exam": Exam,
                "score": Score,
            }
        return FieldService.ENTITY_MODELS.get(entity_type)

    def set_entity_values(self, entity_type: str, entity_id: int, values: dict) -> dict:
        """按实体 ID 批量写入自定义字段（校验类型/必填/枚举），返回实际写入值

        - 实体不存在抛 FieldValidationError
        - 未定义的 field_key 忽略（只写已注册字段）
        """
        model = self._get_model(entity_type)
        if not model:
            raise FieldValidationError(f"不支持的实体类型: {entity_type}")
        entity = self._session.get(model, entity_id)
        if not entity:
            raise FieldValidationError(f"{entity_type} #{entity_id} 不存在")

        written = {}
        for key, value in values.items():
            if not self.get_field(entity_type, key):
                continue  # 未注册字段忽略
            normalized = self.validate_value(entity_type, key, value)
            FieldService.set_value(entity, key, normalized)
            written[key] = normalized
        self._session.commit()
        return written

    def query_by_field(
        self, entity_type: str, field_key: str, value: Any, limit: int = 100
    ) -> list:
        """按自定义字段值查询实体（SQLite json_extract，Sprint 3.7.12）

        - 仅支持已注册的自定义字段（系统列走普通查询）
        - 值匹配：字符串精确匹配；数字比较；None 查缺失
        """
        model = self._get_model(entity_type)
        if not model:
            raise FieldValidationError(f"不支持的实体类型: {entity_type}")
        fd = self.get_field(entity_type, field_key)
        if not fd:
            raise FieldValidationError(f"字段未定义: {entity_type}.{field_key}")
        if not hasattr(model, "ext_json"):
            raise FieldValidationError(f"{entity_type} 无 ext_json 列")

        from sqlalchemy import text

        # SQLite JSON1: json_extract(ext_json, '$.key')
        if value is None:
            cond = f"json_extract(ext_json, '$.{field_key}') IS NULL"
            params = {}
        else:
            cond = f"json_extract(ext_json, '$.{field_key}') = :val"
            params = {"val": str(value)}
        sql = text(f"SELECT id FROM {model.__tablename__} WHERE {cond} LIMIT :lim")
        ids = [row[0] for row in self._session.execute(sql, {**params, "lim": limit}).fetchall()]
        if not ids:
            return []
        return self._session.query(model).filter(model.id.in_(ids)).all()

    # ── 工具 ──
    def _check_entity(self, entity_type: str):
        if entity_type not in ENTITY_TYPES:
            raise FieldValidationError(f"不支持的实体类型: {entity_type}（可选: {ENTITY_TYPES}）")
