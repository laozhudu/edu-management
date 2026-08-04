"""
SQLAlchemy 通用仓储层 — 1.4 兼容
"""

from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

from edu_system.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: Session, model_cls: type[ModelT]):
        self.session = session
        self.model = model_cls

    def get(self, id_val: Any) -> ModelT | None:
        return self.session.query(self.model).get(id_val)

    def list(self, order_by=None, limit=None, offset=None) -> list[ModelT]:
        q = self.session.query(self.model)
        if order_by is not None:
            q = q.order_by(order_by)
        if limit:
            q = q.limit(limit)
        if offset:
            q = q.offset(offset)
        return q.all()

    def count(self) -> int:
        return self.session.query(self.model).count()

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        self.session.flush()
        return instance

    def update(self, instance: ModelT) -> ModelT:
        self.session.merge(instance)
        self.session.flush()
        return instance

    def delete(self, instance: ModelT) -> None:
        self.session.delete(instance)
        self.session.flush()

    def delete_by_id(self, id_val: Any) -> bool:
        instance = self.get(id_val)
        if instance:
            self.delete(instance)
            return True
        return False
