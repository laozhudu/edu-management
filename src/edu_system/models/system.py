# ruff: noqa: F405  (star import 自 base.py，__all__ 已保证定义)
"""
system 域模型
"""

from __future__ import annotations

import enum

from edu_system.models.base import *  # noqa: F401,F403,F405


class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(50), primary_key=True)
    value = Column(Text, default="")


class AuditLog(Base):
    """审计日志表"""

    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String(10), nullable=False)  # INSERT/UPDATE/DELETE
    old_values = Column(Text, nullable=True)  # JSON
    new_values = Column(Text, nullable=True)  # JSON
    operator = Column(String(20), nullable=True)
    ip = Column(String(45), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


# ═══════════════════════════════════
# 权限系统预留模型 (v1.0 表建好，逻辑暂不启用)
# ═══════════════════════════════════


# ═══════════════════════════════════
# 权限系统预留模型 (v1.0 表建好，逻辑暂不启用)
# ═══════════════════════════════════
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(32), unique=True, comment="admin/director/teacher/reader")
    description = Column(String(255), default="")
    permissions = Column(String(4096), default="")

    users = relationship("User", back_populates="role")
    permission_entries = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )


class RolePermission(Base):
    """规范化权限表（Sprint 3.7.17）：替代 Role.permissions 逗号字符串

    - role_id + permission_code 唯一
    - 读写双轨：新表为准，Role.permissions 字符串保留兼容旧数据
    """

    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_code = Column(String(64), nullable=False)
    __table_args__ = (UniqueConstraint("role_id", "permission_code", name="uq_role_permission"),)
    role = relationship("Role", back_populates="permission_entries")


class RowLevelPolicy(Base):
    """行级数据作用域策略（Sprint 3.7.18）

    - role_id + entity_type + scope（作用域类型）+ 可选参数
    - scope: all(全校)/own_class(本班)/own_classes(任课班)/none(无)
    - 应用层拦截：查询时按角色作用域加过滤条件
    """

    __tablename__ = "row_level_policies"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    entity_type = Column(String(32), nullable=False, comment="student/score/attendance...")
    scope = Column(String(32), nullable=False, comment="all/own_class/own_classes/none")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("role_id", "entity_type", name="uq_rlp_role_entity"),)
    role = relationship("Role")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True, comment="登录名")
    password_hash = Column(String(128), default="")
    display_name = Column(String(64), default="")
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    role = relationship("Role", back_populates="users")

    @property
    def permissions(self) -> list:
        """获取用户权限列表（从角色继承）"""
        if self.role and self.role.permissions:
            return [p.strip() for p in self.role.permissions.split(",") if p.strip()]
        return []


class UserColumnConfig(Base):
    """用户列配置持久化（M5-G：多端同步）"""

    __tablename__ = "user_column_configs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    page_id = Column(String(64), nullable=False, index=True, comment="页面标识")
    columns = Column(JSON, default=[], comment="列配置 JSON")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    __table_args__ = (UniqueConstraint("user_id", "page_id", name="uq_user_page_config"),)

    user = relationship("User", backref="column_configs")


class Classroom(Base):
    __tablename__ = "classrooms"
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, comment="学期")
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, comment="班级")
    floor = Column(String(10), default="", comment="楼层")
    room_no = Column(String(20), default="", comment="教室号")
    capacity = Column(Integer, default=50, comment="座位数")
    semester = relationship("Semester", back_populates="classrooms")


# ════════════════════════════════════
# 系统级配置与学期配置
# ════════════════════════════════════


# ════════════════════════════════════
# 系统级配置与学期配置
# ════════════════════════════════════
class GlobalSetting(Base):
    """全局配置（跨学期通用）"""

    __tablename__ = "global_settings"
    key = Column(String(50), primary_key=True)
    value = Column(Text, default="")
    description = Column(String(200), default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SemesterConfig(Base):
    """学期级配置（随学期隔离，支持版本控制与继承追溯）"""

    __tablename__ = "semester_configs"
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    key = Column(String(50), nullable=False, index=True)
    value = Column(Text, default="")
    version = Column(Integer, default=1, comment="配置版本号")
    inherited_from = Column(
        Integer, ForeignKey("semesters.id"), nullable=True, comment="继承来源学期ID"
    )
    description = Column(String(200), default="")
    created_by = Column(String(50), default="", comment="创建者")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("semester_id", "key", name="uq_semester_config"),
        Index("idx_semester_config_semester", "semester_id"),
    )
    semester = relationship("Semester", foreign_keys=[semester_id])
    source_semester = relationship("Semester", foreign_keys=[inherited_from])


class SemesterConfigHistory(Base):
    """学期配置版本快照表：保存每次写入/回滚的历史（key/value/version）

    semester_configs 表保持 (semester_id, key) 唯一存当前值；
    历史版本存此快照表，支持回滚追溯（回避 SQLite 约束 batch 迁移）。
    """

    __tablename__ = "semester_config_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    key = Column(String(50), nullable=False)
    value = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, index=True)
    action = Column(String(20), nullable=False, default="SAVE", comment="SAVE/ROLLBACK/INHERIT")
    operator = Column(String(50), nullable=True, default="")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("ix_config_history_semester_version", "semester_id", "version"),)


# ════════════════════════════════════
# 多校区支持
# ════════════════════════════════════


# ════════════════════════════════════
# 多校区支持
# ════════════════════════════════════
class School(Base):
    """校区/学校模型"""

    __tablename__ = "schools"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    config_json = Column(Text, default="{}", comment="校区级配置 JSON")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


# ════════════════════════════════════
# 服务注册表（持久化配置）
# ════════════════════════════════════


# ════════════════════════════════════
# 服务注册表（持久化配置）
# ════════════════════════════════════
class ServiceConfig(Base):
    """服务配置持久化表"""

    __tablename__ = "service_configs"
    id = Column(Integer, primary_key=True)
    service_code = Column(String(50), unique=True, nullable=False, index=True, comment="服务代码")
    name = Column(String(100), nullable=False, comment="服务名称")
    description = Column(Text, default="", comment="服务描述")
    api_prefix = Column(String(100), nullable=False, comment="API 前缀")
    enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    required_permissions = Column(Text, default="", comment="所需权限，逗号分隔")
    allowed_roles = Column(Text, default="", comment="允许角色，逗号分隔")
    rate_limit = Column(Integer, default=100, nullable=False, comment="限流阈值（请求数/窗口）")
    rate_limit_window = Column(Integer, default=60, nullable=False, comment="限流窗口（秒）")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ════════════════════════════════════
# 数据锁定机制
# ════════════════════════════════════


# ════════════════════════════════════
# 数据锁定机制
# ════════════════════════════════════
class LockLevel(enum.StrEnum):
    """锁定级别枚举"""

    none = "none"  # 无锁定
    soft = "soft"  # 软锁定：提示只读，管理员可强制编辑
    hard = "hard"  # 硬锁定：仅 DATA_UNLOCK 权限可解锁
    semester = "semester"  # 学期级锁定：整学期只读（归档态）


class DataLock(Base):
    """通用数据锁定表"""

    __tablename__ = "data_locks"
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    entity_type = Column(
        String(50), nullable=False, index=True, comment="实体类型：class/student/score/exam等"
    )
    entity_id = Column(Integer, nullable=False, index=True, comment="实体ID，0表示表级锁定")
    lock_level = Column(SQLEnum(LockLevel), default=LockLevel.soft, nullable=False)
    locked_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="锁定操作人")
    locked_at = Column(DateTime, server_default=func.now())
    reason = Column(Text, default="", comment="锁定理由")
    __table_args__ = (
        Index("idx_data_lock_entity", "entity_type", "entity_id"),
        Index("idx_data_lock_semester", "semester_id"),
    )
    semester = relationship("Semester")


# ════════════════════════════════════
# 幂等性键表
# ════════════════════════════════════


# ════════════════════════════════════
# 幂等性键表
# ════════════════════════════════════
class IdempotencyKey(Base):
    """幂等性键表：防止重复请求"""

    __tablename__ = "idempotency_keys"
    key = Column(String(64), primary_key=True)
    response_body = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=True)
    response_headers = Column(Text, nullable=True)  # JSON 存储
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False, index=True)
    __table_args__ = (UniqueConstraint("key", name="uq_idempotency_key"),)


# ════════════════════════════════════
# Outbox 事件表
# ════════════════════════════════════


# ════════════════════════════════════
# Outbox 事件表
# ════════════════════════════════════
class OutboxEvent(Base):
    """Outbox 事件表：保证事件可靠投递"""

    __tablename__ = "outbox_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_id = Column(String(64), nullable=False, index=True)
    payload = Column(Text, nullable=False)  # JSON
    trace_id = Column(String(64), nullable=True, index=True)
    retry_count = Column(Integer, default=0)
    dead_letter = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    processed_at = Column(DateTime, nullable=True)
    __table_args__ = (Index("ix_outbox_unprocessed", "processed_at", "dead_letter"),)


# ════════════════════════════════════
# 考勤管理
# ════════════════════════════════════


# ════════════════════════════════════
# 设备信任表
# ════════════════════════════════════
class DeviceTrust(Base):
    """设备信任表：存储用户受信设备，支持免密登录"""

    __tablename__ = "device_trusts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_name = Column(String(100), nullable=False)
    fingerprint = Column(String(64), nullable=False, index=True)
    user_agent = Column(String(500), nullable=True)
    ip = Column(String(45), nullable=True)
    trusted = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False, index=True)
    last_used_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "fingerprint", name="uq_user_device_fingerprint"),
        Index("idx_device_trust_user_trusted", "user_id", "trusted"),
    )

    user = relationship("User")


# ════════════════════════════════════
# 数据锁定机制
# ════════════════════════════════════


# ═══════════════════════════════════
# 字段动态增删机制（Sprint 3.7 核心：灵活度高、耦合低）
# ═══════════════════════════════════
class FieldDefinition(Base):
    """字段注册表：定义各实体的可扩展字段（自定义字段可增删，系统字段受保护）

    entity_type: student / teacher / class / exam / score / ...
    field_type: string / int / float / date / enum / select / bool
    """

    __tablename__ = "field_definitions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(30), nullable=False, index=True, comment="所属实体类型")
    field_key = Column(String(50), nullable=False, comment="字段键（写入 ext_json）")
    label = Column(String(100), nullable=False, comment="显示名称")
    field_type = Column(
        String(20), default="string", comment="string/int/float/date/enum/select/bool"
    )
    options = Column(Text, nullable=True, comment="enum/select 选项，JSON 数组")
    required = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    is_system = Column(Boolean, default=False, comment="系统字段不可删除")
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("entity_type", "field_key", name="uq_field_definition"),)


# ════════════════════════════════════
# 字典管理（M1：对齐若依 #6 字典）
# ════════════════════════════════════
class DictType(Base):
    """字典类型"""

    __tablename__ = "dict_types"
    id = Column(Integer, primary_key=True)
    dict_type = Column(String(64), unique=True, nullable=False, comment="字典类型编码")
    dict_name = Column(String(64), default="", comment="字典类型名称")
    status = Column(String(4), default="0", comment="状态: 0正常/1停用")
    remark = Column(String(255), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DictData(Base):
    """字典数据"""

    __tablename__ = "dict_data"
    id = Column(Integer, primary_key=True)
    dict_type = Column(String(64), nullable=False, comment="字典类型编码", index=True)
    dict_label = Column(String(64), default="", comment="显示标签（中文）")
    dict_value = Column(String(64), default="", comment="实际值")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(String(4), default="0", comment="状态: 0正常/1停用")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_dict_type_sort", "dict_type", "sort_order"),)


# ════════════════════════════════════
# M2：通知公告 / 登录日志 / 在线用户（对齐若依 #8/#10/#11）
# ════════════════════════════════════


# ════════════════════════════════════
# M2：通知公告 / 登录日志 / 在线用户（对齐若依 #8/#10/#11）
# ════════════════════════════════════
class Notice(Base):
    """通知公告"""

    __tablename__ = "notices"
    id = Column(Integer, primary_key=True)
    title = Column(String(120), nullable=False, comment="标题")
    content = Column(Text, default="")
    notice_type = Column(String(10), default="notice", comment="类型: notice通知/announce公告")
    status = Column(String(4), default="0", comment="状态: 0发布/1草稿/2已下线")
    publisher = Column(String(32), default="", comment="发布人")
    read_count = Column(Integer, default=0, comment="阅读数")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class NoticeRead(Base):
    """公告已读记录"""

    __tablename__ = "notice_reads"
    id = Column(Integer, primary_key=True)
    notice_id = Column(Integer, ForeignKey("notices.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, nullable=False)
    read_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("notice_id", "user_id", name="uq_notice_user"),)


class LoginLog(Base):
    """登录日志"""

    __tablename__ = "login_logs"
    id = Column(Integer, primary_key=True)
    username = Column(String(32), default="")
    status = Column(String(4), default="0", comment="0成功/1失败")
    msg = Column(String(120), default="")
    ip = Column(String(45), default="")
    user_agent = Column(String(200), default="")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_loginlog_time", "created_at"),)


class OnlineUser(Base):
    """在线用户（登录会话跟踪）"""

    __tablename__ = "online_users"
    id = Column(Integer, primary_key=True)
    token_fp = Column(
        String(64), unique=True, nullable=False, comment="token 指纹（sha256 前 16 位）"
    )
    username = Column(String(32), default="")
    display_name = Column(String(64), default="")
    ip = Column(String(45), default="")
    user_agent = Column(String(200), default="")
    login_at = Column(DateTime, server_default=func.now())
    expire_at = Column(DateTime, nullable=True)
    __table_args__ = (Index("idx_online_expire", "expire_at"),)


# ── 外部模块模型注册（确保全部表进入 Base.metadata，init_db 可建全量表）──
# 模型按业务模块分散定义在 services/ 下，必须在此 import 触发注册，
# 否则 Base.metadata.create_all() 不会创建对应表（如 stored_files）。
from edu_system.services.storage import StoredFile  # noqa: E402, F401  (注册 stored_files 表)
