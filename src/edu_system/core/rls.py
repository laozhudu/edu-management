"""
行级安全（RLS）服务（Sprint 3.7.18）

- RowLevelPolicy 表定义角色对实体的数据作用域
- apply_scope：查询时按作用域自动加过滤条件（应用层拦截）
- 内置作用域：all(全校)/own_class(班主任本班)/own_classes(教师任课班)/none(无数据)
"""

from sqlalchemy.orm import Session

from edu_system.models import RowLevelPolicy

# 作用域常量
SCOPE_ALL = "all"  # 全校数据
SCOPE_OWN_CLASS = "own_class"  # 班主任：本班
SCOPE_OWN_CLASSES = "own_classes"  # 教师：任课班级
SCOPE_NONE = "none"  # 无数据

# 默认策略：角色 → 实体 → 作用域（数据库无配置时的兜底）
DEFAULT_POLICIES: dict[str, dict[str, str]] = {
    "admin": {"student": SCOPE_ALL, "score": SCOPE_ALL, "attendance": SCOPE_ALL},
    "director": {"student": SCOPE_ALL, "score": SCOPE_ALL, "attendance": SCOPE_ALL},
    "teacher": {
        "student": SCOPE_OWN_CLASSES,
        "score": SCOPE_OWN_CLASSES,
        "attendance": SCOPE_OWN_CLASSES,
    },
    "reader": {"student": SCOPE_NONE, "score": SCOPE_NONE, "attendance": SCOPE_NONE},
}


class RowLevelSecurity:
    def __init__(self, session: Session):
        self.session = session

    # ── 策略查询 ──
    def get_scope(self, role_id: int, entity_type: str) -> str | None:
        """查角色对实体的作用域（DB 配置优先，回退默认策略）"""
        row = (
            self.session.query(RowLevelPolicy.scope)
            .filter_by(role_id=role_id, entity_type=entity_type)
            .first()
        )
        if row:
            return row[0]
        return None

    def get_scope_by_role_name(self, role_name: str, entity_type: str) -> str:
        """按角色名查作用域（含默认兜底）"""
        defaults = DEFAULT_POLICIES.get(role_name, {})
        return defaults.get(entity_type, SCOPE_NONE)

    # ── 策略管理 ──
    def set_policy(self, role_id: int, entity_type: str, scope: str):
        """设置/更新策略（幂等 upsert）"""
        policy = (
            self.session.query(RowLevelPolicy)
            .filter_by(role_id=role_id, entity_type=entity_type)
            .first()
        )
        if policy:
            policy.scope = scope
        else:
            self.session.add(RowLevelPolicy(role_id=role_id, entity_type=entity_type, scope=scope))
        self.session.commit()

    def delete_policy(self, role_id: int, entity_type: str):
        self.session.query(RowLevelPolicy).filter_by(
            role_id=role_id, entity_type=entity_type
        ).delete()
        self.session.commit()

    # ── 作用域应用 ──
    def apply_scope(
        self,
        query,
        entity_type: str,
        role_name: str,
        context: dict | None = None,
        role_id: int | None = None,
    ):
        """给 SQLAlchemy Query 应用行级过滤

        优先级：DB 策略（RowLevelPolicy，需 role_id）> 默认策略（DEFAULT_POLICIES）
        context: 当前用户上下文（如 {"teacher_id": 3, "class_id": 5}）
        - own_class: 限定班级（context["class_id"]）
        - own_classes: 限定任课班级列表（context["class_ids"]）
        - all: 不过滤
        - none: 返回空结果（恒假条件）
        """
        scope = None
        if role_id is not None:
            scope = self.get_scope(role_id, entity_type)
        if scope is None:
            scope = self.get_scope_by_role_name(role_name, entity_type)
        ctx = context or {}

        # 计算过滤条件
        cond = None
        if scope == SCOPE_ALL:
            pass
        elif scope == SCOPE_NONE:
            cond = text_condition(False)
        elif scope == SCOPE_OWN_CLASS:
            class_id = ctx.get("class_id")
            cond = text_condition(False) if class_id is None else _class_id_equals(class_id)
        elif scope == SCOPE_OWN_CLASSES:
            class_ids = ctx.get("class_ids") or []
            cond = text_condition(False) if not class_ids else column_in(class_ids)

        if cond is not None:
            return query.filter(cond)
        return query


def text_condition(value: bool):
    """恒真/恒假条件（SQLite 兼容）"""
    from sqlalchemy import text

    return text("1=1" if value else "1=0")


def column_in(class_ids: list):
    """class_id IN (...) 条件"""
    from sqlalchemy import text

    ids = ",".join(str(i) for i in class_ids)
    return text(f"class_id IN ({ids})")


def _class_id_equals(class_id):
    """class_id = N 条件"""
    from sqlalchemy import text

    return text(f"class_id = {int(class_id)}")
