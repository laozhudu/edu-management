"""
Repository 层（对齐若依 Mapper）

- BaseRepository：泛型 CRUD（base.py）
- get_repo：按模型类获取对应 repository（默认 BaseRepository；可扩展特化）
- 用法：repo = get_repo(Student, session); repo.add(student)
"""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy.orm import Session

from edu_system.repository.base import BaseRepository

ModelT = TypeVar("ModelT")

# 特化 repository 注册表（如需要定制查询逻辑的实体）
_SPECIALIZED: dict = {}


def register_repository(model_cls, repo_cls) -> None:
    """注册特化 repository（覆盖默认 BaseRepository）"""
    _SPECIALIZED[model_cls] = repo_cls


def get_repo(model_cls, session: Session) -> BaseRepository:
    """获取实体的 repository（对齐若依 Mapper 注入）"""
    repo_cls = _SPECIALIZED.get(model_cls, BaseRepository)
    return repo_cls(session, model_cls)


__all__ = ["BaseRepository", "get_repo", "register_repository"]
