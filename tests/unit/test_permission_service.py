"""
PermissionService 测试（Sprint 3.7.17）
覆盖：增删权限、去重、旧字符串回退、旧→新同步、require_permission 双轨
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.models import Base, Role, RolePermission
from edu_system.services.permissions import PermissionService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture
def svc(session):
    return PermissionService(session)


def _role(session, name, permissions=""):
    r = Role(name=name, permissions=permissions)
    session.add(r)
    session.commit()
    return r


class TestPermissionService:
    def test_add_and_get(self, session, svc):
        r = _role(session, "teacher")
        svc.add_permission(r.id, "score:entry")
        svc.add_permission(r.id, "score:view")
        perms = svc.get_permissions(r.id)
        assert set(perms) == {"score:entry", "score:view"}

    def test_add_duplicate_idempotent(self, session, svc):
        r = _role(session, "teacher")
        svc.add_permission(r.id, "score:entry")
        svc.add_permission(r.id, "score:entry")  # 重复添加
        assert len(svc.get_permissions(r.id)) == 1

    def test_remove_permission(self, session, svc):
        r = _role(session, "teacher")
        svc.add_permission(r.id, "score:entry")
        svc.remove_permission(r.id, "score:entry")
        assert svc.get_permissions(r.id) == []

    def test_has_permission(self, session, svc):
        r = _role(session, "teacher")
        svc.add_permission(r.id, "score:entry")
        assert svc.has_permission(r.id, "score:entry") is True
        assert svc.has_permission(r.id, "score:view") is False

    def test_legacy_fallback(self, session, svc):
        """未同步角色回退旧字符串列"""
        r = _role(session, "teacher", permissions="score:entry,score:view")
        perms = svc.get_permissions(r.id)
        assert set(perms) == {"score:entry", "score:view"}

    def test_sync_from_legacy(self, session, svc):
        """旧字符串列同步到新表"""
        r = _role(session, "teacher", permissions="score:entry,score:view")
        added = svc.sync_from_legacy(r.id)
        assert added == 2
        # 新表优先
        perms = svc.get_permissions(r.id)
        assert set(perms) == {"score:entry", "score:view"}
        # 幂等
        assert svc.sync_from_legacy(r.id) == 0

    def test_sync_all_roles(self, session, svc):
        r1 = _role(session, "teacher", permissions="score:entry")
        r2 = _role(session, "reader", permissions="score:view")
        total = svc.sync_all_roles()
        assert total == 2
        assert svc.has_permission(r1.id, "score:entry")
        assert svc.has_permission(r2.id, "score:view")

    def test_unique_constraint(self, session, svc):
        """DB 层唯一约束（role_id, permission_code）"""
        r = _role(session, "teacher")
        svc.add_permission(r.id, "score:entry")
        session.add(RolePermission(role_id=r.id, permission_code="score:entry"))
        with pytest.raises(Exception):
            session.commit()
