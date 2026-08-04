"""
角色权限规范化服务（Sprint 3.7.17）

- RolePermission 表（role_id + permission_code）替代 Role.permissions 逗号字符串
- 读写双轨：新表为准，旧字符串列保留兼容（迁移期双写）
- 提供：角色权限列表、增删、同步、判断
"""

from sqlalchemy.orm import Session

from edu_system.models import Role, RolePermission


class PermissionService:
    def __init__(self, session: Session):
        self.session = session

    # ── 查询 ──
    def get_permissions(self, role_id: int) -> list[str]:
        """按角色查权限（新表为准，空则回退旧字符串列）"""
        rows = (
            self.session.query(RolePermission.permission_code)
            .filter(RolePermission.role_id == role_id)
            .all()
        )
        codes = [r[0] for r in rows]
        if codes:
            return codes
        # 回退旧字符串列（未同步过的角色）
        role = self.session.get(Role, role_id)
        if role and role.permissions:
            return [p for p in str(role.permissions).split(",") if p]
        return []

    def has_permission(self, role_id: int, permission_code: str) -> bool:
        return permission_code in self.get_permissions(role_id)

    # ── 增删 ──
    def add_permission(self, role_id: int, permission_code: str):
        exists = (
            self.session.query(RolePermission.id)
            .filter_by(role_id=role_id, permission_code=permission_code)
            .first()
        )
        if exists:
            return
        self.session.add(RolePermission(role_id=role_id, permission_code=permission_code))
        self.session.commit()

    def remove_permission(self, role_id: int, permission_code: str):
        self.session.query(RolePermission).filter_by(
            role_id=role_id, permission_code=permission_code
        ).delete()
        self.session.commit()

    # ── 同步 ──
    def sync_from_legacy(self, role_id: int) -> int:
        """把 Role.permissions 旧字符串列同步到新表（幂等，双写）"""
        role = self.session.get(Role, role_id)
        if not role or not role.permissions:
            return 0
        codes = [p for p in str(role.permissions).split(",") if p]
        existing = {
            r[0]
            for r in self.session.query(RolePermission.permission_code)
            .filter_by(role_id=role_id)
            .all()
        }
        added = 0
        for code in codes:
            if code not in existing:
                self.session.add(RolePermission(role_id=role_id, permission_code=code))
                added += 1
        if added:
            self.session.commit()
        return added

    def sync_all_roles(self) -> int:
        """同步所有角色（初始化/迁移用），返回新增总数"""
        total = 0
        for (role_id,) in self.session.query(Role.id).all():
            total += self.sync_from_legacy(int(role_id))
        return total
