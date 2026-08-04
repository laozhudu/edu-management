"""
M5-A5 学期维度权限测试

测试细粒度学期权限：
- SEMESTER_VIEW: 查看学期设置
- SEMESTER_EDIT: 编辑学期（新建/切换/归档）
- SEMESTER_ADMIN: 学期管理员权限（跨学年升年级等）
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.core.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    clear_current_user,
    has_permission,
    set_current_user,
)
from edu_system.models import Base


@pytest.fixture
def session():
    """内存 SQLite 会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


class TestSemesterPermissions:
    """学期维度权限测试"""

    def test_semester_permission_enums_exist(self):
        """验证学期相关权限枚举存在"""
        # 这些权限应已在 Permission 枚举中定义
        assert hasattr(Permission, "SEMESTER_VIEW")
        assert hasattr(Permission, "SEMESTER_EDIT")
        assert hasattr(Permission, "SEMESTER_ADMIN")

    def test_director_has_semester_permissions(self):
        """教务主任拥有学期查看/编辑权限"""
        user = type("User", (), {"permissions": ROLE_PERMISSIONS["director"]})()
        set_current_user(user)

        assert has_permission(Permission.SEMESTER_VIEW)
        assert has_permission(Permission.SEMESTER_EDIT)
        assert not has_permission(Permission.SEMESTER_ADMIN)  # 管理员专属

        clear_current_user()

    def test_admin_has_all_semester_permissions(self):
        """管理员拥有所有学期权限"""
        user = type("User", (), {"permissions": ROLE_PERMISSIONS["admin"]})()
        set_current_user(user)

        assert has_permission(Permission.SEMESTER_VIEW)
        assert has_permission(Permission.SEMESTER_EDIT)
        assert has_permission(Permission.SEMESTER_ADMIN)

        clear_current_user()

    def test_teacher_no_semester_permissions(self):
        """教师无学期管理权限"""
        user = type("User", (), {"permissions": ROLE_PERMISSIONS["teacher"]})()
        set_current_user(user)

        assert not has_permission(Permission.SEMESTER_VIEW)
        assert not has_permission(Permission.SEMESTER_EDIT)
        assert not has_permission(Permission.SEMESTER_ADMIN)

        clear_current_user()

    def test_reader_no_semester_permissions(self):
        """只读角色无学期管理权限"""
        user = type("User", (), {"permissions": ROLE_PERMISSIONS["reader"]})()
        set_current_user(user)

        assert not has_permission(Permission.SEMESTER_VIEW)
        assert not has_permission(Permission.SEMESTER_EDIT)
        assert not has_permission(Permission.SEMESTER_ADMIN)

        clear_current_user()


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
