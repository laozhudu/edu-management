"""
学期配置继承服务
核心功能：
1. 深拷贝继承 + 选择性覆盖
2. 四色差异预览（新增/修改/保留/冲突）
3. 版本控制 + 回滚
"""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from edu_system.database import get_session
from edu_system.models import SemesterConfig


class DiffType(Enum):
    """差异类型：用于四色预览"""

    ADDED = "added"  # 绿色：新增配置
    MODIFIED = "modified"  # 蓝色：修改配置
    RETAINED = "retained"  # 灰色：保留配置（未变）
    CONFLICT = "conflict"  # 红色：冲突配置（源与目标都有值但不同）


class DiffItem:
    """单个配置差异项"""

    def __init__(
        self,
        key: str,
        diff_type: DiffType,
        source_value: Any = None,
        target_value: Any = None,
        new_value: Any = None,
        description: str = "",
    ):
        self.key = key
        self.diff_type = diff_type
        self.source_value = source_value
        self.target_value = target_value
        self.new_value = new_value
        self.description = description

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "type": self.diff_type.value,
            "source_value": self.source_value,
            "target_value": self.target_value,
            "new_value": self.new_value,
            "description": self.description,
            "color": self._get_color(),
        }

    def _get_color(self) -> str:
        colors = {
            DiffType.ADDED: "#22c55e",  # 绿色
            DiffType.MODIFIED: "#3b82f6",  # 蓝色
            DiffType.RETAINED: "#9ca3af",  # 灰色
            DiffType.CONFLICT: "#ef4444",  # 红色
        }
        return colors.get(self.diff_type, "#000000")


class SemesterConfigService:
    """学期配置服务：继承、版本控制、回滚"""

    def __init__(self, session: Session):
        self.session = session

    # ===== 配置继承核心 =====

    def preview_inherit(
        self, source_semester_id: int, target_semester_id: int, overwrite_keys: list[str] = None
    ) -> dict:
        """
        预览继承结果：返回四色差异列表
        不写入数据库，仅供 UI 预览
        """
        source_configs = self._get_all_configs(source_semester_id)
        target_configs = self._get_all_configs(target_semester_id)

        overwrite_keys = set(overwrite_keys or [])
        diffs = []

        all_keys = set(source_configs.keys()) | set(target_configs.keys())

        for key in sorted(all_keys):
            src_val = source_configs.get(key)
            tgt_val = target_configs.get(key)

            if key in overwrite_keys:
                # 强制覆盖模式
                if src_val is not None:
                    if tgt_val is None:
                        diffs.append(
                            DiffItem(key, DiffType.ADDED, source_value=src_val, new_value=src_val)
                        )
                    elif src_val != tgt_val:
                        diffs.append(
                            DiffItem(
                                key,
                                DiffType.MODIFIED,
                                source_value=src_val,
                                target_value=tgt_val,
                                new_value=src_val,
                            )
                        )
                    else:
                        diffs.append(
                            DiffItem(
                                key,
                                DiffType.RETAINED,
                                source_value=src_val,
                                target_value=tgt_val,
                                new_value=src_val,
                            )
                        )
                else:
                    # 源无值，保留目标
                    if tgt_val is not None:
                        diffs.append(
                            DiffItem(
                                key,
                                DiffType.RETAINED,
                                source_value=None,
                                target_value=tgt_val,
                                new_value=tgt_val,
                            )
                        )
            else:
                # 智能合并模式
                if src_val is None:
                    # 源无值，保留目标
                    if tgt_val is not None:
                        diffs.append(
                            DiffItem(
                                key,
                                DiffType.RETAINED,
                                source_value=None,
                                target_value=tgt_val,
                                new_value=tgt_val,
                            )
                        )
                elif tgt_val is None:
                    # 目标无值，新增
                    diffs.append(
                        DiffItem(key, DiffType.ADDED, source_value=src_val, new_value=src_val)
                    )
                elif src_val == tgt_val:
                    # 值相同，保留
                    diffs.append(
                        DiffItem(
                            key,
                            DiffType.RETAINED,
                            source_value=src_val,
                            target_value=tgt_val,
                            new_value=src_val,
                        )
                    )
                else:
                    # 值不同，冲突
                    diffs.append(
                        DiffItem(
                            key,
                            DiffType.CONFLICT,
                            source_value=src_val,
                            target_value=tgt_val,
                            new_value=tgt_val,
                        )
                    )

        # 统计
        stats = {
            "added": sum(1 for d in diffs if d.diff_type == DiffType.ADDED),
            "modified": sum(1 for d in diffs if d.diff_type == DiffType.MODIFIED),
            "retained": sum(1 for d in diffs if d.diff_type == DiffType.RETAINED),
            "conflict": sum(1 for d in diffs if d.diff_type == DiffType.CONFLICT),
            "total": len(diffs),
        }

        return {
            "source_semester_id": source_semester_id,
            "target_semester_id": target_semester_id,
            "overwrite_keys": list(overwrite_keys),
            "diffs": [d.to_dict() for d in diffs],
            "stats": stats,
            "preview_time": datetime.now().isoformat(),
        }

    def execute_inherit(
        self,
        source_semester_id: int,
        target_semester_id: int,
        overwrite_keys: list[str] = None,
        operator: str = "system",
    ) -> dict:
        """
        执行继承：深拷贝 + 选择性覆盖 + 版本记录
        返回执行结果
        """
        preview = self.preview_inherit(source_semester_id, target_semester_id, overwrite_keys)

        # 检查是否有冲突未解决
        conflicts = [d for d in preview["diffs"] if d["type"] == "conflict"]
        if conflicts:
            return {
                "success": False,
                "error": f"存在 {len(conflicts)} 个冲突配置，请先在预览中解决",
                "conflicts": conflicts,
            }

        # 获取源配置
        source_configs = self._get_all_configs(source_semester_id)

        # 获取目标现有配置（用于版本记录）
        old_configs = self._get_all_configs(target_semester_id)

        # 计算新配置
        new_configs = {}
        overwrite_keys = set(overwrite_keys or [])

        for key, diff in zip(
            sorted(set(source_configs.keys()) | set(old_configs.keys())), preview["diffs"]
        ):
            new_configs[key] = diff["new_value"]

        # 快照目标旧配置到历史表（保留回滚能力）
        self._snapshot(
            target_semester_id, old_configs, version=0, action="INHERIT", operator=operator
        )

        # 写入新配置（每 key 一行当前值 + 当前版本号）
        version = self._get_next_version(target_semester_id)
        now = datetime.now()

        for key, value in new_configs.items():
            if value is not None:
                config = (
                    self.session.query(SemesterConfig)
                    .filter(
                        SemesterConfig.semester_id == target_semester_id,
                        SemesterConfig.key == key,
                    )
                    .first()
                )
                if config:
                    config.value = str(value)
                    config.version = version
                    config.inherited_from = source_semester_id
                    config.created_by = operator
                    config.updated_at = now
                else:
                    config = SemesterConfig(
                        semester_id=target_semester_id,
                        key=key,
                        value=str(value),
                        version=version,
                        inherited_from=source_semester_id,
                        created_by=operator,
                        created_at=now,
                    )
                    self.session.add(config)

        # 快照新配置到历史表（当前版本）
        self._snapshot(
            target_semester_id, new_configs, version=version, action="INHERIT", operator=operator
        )

        # 记录继承历史
        self._record_inheritance_history(
            source_semester_id,
            target_semester_id,
            version,
            overwrite_keys,
            operator,
            old_configs,
            new_configs,
        )

        self.session.commit()

        return {
            "success": True,
            "version": version,
            "config_count": len(new_configs),
            "stats": preview["stats"],
            "message": f"继承完成，版本 {version}，共 {len(new_configs)} 项配置",
        }

    # ===== 版本控制 =====

    def get_versions(self, semester_id: int) -> list[dict]:
        """获取学期的所有配置版本（从历史快照表）"""
        from sqlalchemy import func

        from edu_system.models import SemesterConfigHistory

        # 用 group_by 替代 distinct，避免 SQLite 生成带 LIMIT 的子查询
        # 与 before_compile 的 semester 过滤注入钩子冲突
        versions = (
            self.session.query(
                SemesterConfigHistory.version.label("v"),
                func.max(SemesterConfigHistory.created_at).label("created_at"),
                func.max(SemesterConfigHistory.operator).label("operator"),
            )
            .filter(
                SemesterConfigHistory.semester_id == semester_id,
                SemesterConfigHistory.version > 0,
            )
            .group_by(SemesterConfigHistory.version)
            .order_by(SemesterConfigHistory.version.desc())
            .all()
        )

        result = []
        for row in versions:
            count = (
                self.session.query(SemesterConfigHistory)
                .filter(
                    SemesterConfigHistory.semester_id == semester_id,
                    SemesterConfigHistory.version == row.v,
                )
                .count()
            )
            result.append(
                {
                    "version": row.v,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "created_by": row.operator,
                    "inherited_from": None,
                    "config_count": count,
                }
            )
        return result

    def get_version_configs(self, semester_id: int, version: int) -> dict[str, str]:
        """获取指定版本的所有配置（从历史快照表）"""
        from edu_system.models import SemesterConfigHistory

        configs = (
            self.session.query(SemesterConfigHistory)
            .filter(
                SemesterConfigHistory.semester_id == semester_id,
                SemesterConfigHistory.version == version,
            )
            .all()
        )
        return {c.key: c.value for c in configs}

    def rollback_to_version(
        self, semester_id: int, target_version: int, operator: str = "system"
    ) -> dict:
        """回滚到指定版本（从历史快照恢复）"""
        # 获取目标版本配置（历史快照）
        target_configs = self.get_version_configs(semester_id, target_version)
        if not target_configs:
            return {"success": False, "error": f"版本 {target_version} 不存在或为空"}

        # 当前配置（用于快照保留）
        current_configs = self._get_all_configs(semester_id)

        # 当前版本
        current_version = self._get_current_version(semester_id)

        # 写入回滚配置（新版本号，每 key 一行覆盖当前值）
        new_version = current_version + 1
        now = datetime.now()

        for key, value in target_configs.items():
            config = (
                self.session.query(SemesterConfig)
                .filter(SemesterConfig.semester_id == semester_id, SemesterConfig.key == key)
                .first()
            )
            if config:
                config.value = value
                config.version = new_version
                config.inherited_from = None  # 回滚不记录继承来源
                config.created_by = operator
                config.updated_at = now
            else:
                config = SemesterConfig(
                    semester_id=semester_id,
                    key=key,
                    value=value,
                    version=new_version,
                    inherited_from=None,
                    created_by=operator,
                    created_at=now,
                )
                self.session.add(config)

        # 删除当前值里目标版本没有的 key（回滚语义：完全恢复目标版本）
        target_keys = set(target_configs.keys())
        stale_query = self.session.query(SemesterConfig).filter(
            SemesterConfig.semester_id == semester_id
        )
        if target_keys:
            stale_query = stale_query.filter(SemesterConfig.key.notin_(target_keys))
        for s in stale_query.all():
            self.session.delete(s)

        # 快照回滚后的配置到历史表（新版本）
        self._snapshot(
            semester_id, target_configs, version=new_version, action="ROLLBACK", operator=operator
        )

        # 记录回滚历史
        self._record_rollback_history(
            semester_id, current_version, target_version, new_version, operator
        )

        self.session.commit()

        return {
            "success": True,
            "old_version": current_version,
            "target_version": target_version,
            "new_version": new_version,
            "config_count": len(target_configs),
            "message": f"回滚完成：从 v{current_version} 回滚到 v{target_version}，新版本 v{new_version}",
        }

    # ===== 内部辅助方法 =====

    def _snapshot(
        self,
        semester_id: int,
        configs: dict,
        version: int,
        action: str = "SAVE",
        operator: str = "system",
    ) -> None:
        """将配置快照写入历史表（每次写入/回滚/继承记录）"""
        from edu_system.models import SemesterConfigHistory

        now = datetime.now()
        for key, value in configs.items():
            self.session.add(
                SemesterConfigHistory(
                    semester_id=semester_id,
                    key=key,
                    value=str(value) if value is not None else None,
                    version=version,
                    action=action,
                    operator=operator,
                    created_at=now,
                )
            )

    def _get_all_configs(self, semester_id: int) -> dict[str, str]:
        """获取学期所有配置（最新版本）"""
        latest_version = self._get_current_version(semester_id)
        if latest_version == 0:
            return {}

        configs = (
            self.session.query(SemesterConfig)
            .filter(
                SemesterConfig.semester_id == semester_id,
                SemesterConfig.version == latest_version,
            )
            .all()
        )
        return {c.key: c.value for c in configs}

    def _get_current_version(self, semester_id: int) -> int:
        """获取学期当前最大版本号（含软删除标记的版本）"""
        from sqlalchemy import func

        max_ver = (
            self.session.query(func.max(SemesterConfig.version))
            .filter(SemesterConfig.semester_id == semester_id)
            .scalar()
        )
        return max_ver or 0

    def _get_next_version(self, semester_id: int) -> int:
        return self._get_current_version(semester_id) + 1

    def _record_inheritance_history(
        self,
        source_id: int,
        target_id: int,
        version: int,
        overwrite_keys: set,
        operator: str,
        old_configs: dict,
        new_configs: dict,
    ):
        """记录继承历史到审计日志"""
        from edu_system.core.audit import manual_audit

        manual_audit(
            self.session,
            table_name="semester_configs",
            record_id=target_id,
            action="INHERIT",
            old_values={
                "version": version - 1,
                "configs": old_configs,
                "source_semester": source_id,
            },
            new_values={
                "version": version,
                "configs": new_configs,
                "overwrite_keys": list(overwrite_keys),
            },
            operator=operator,
        )

    def _record_rollback_history(
        self,
        semester_id: int,
        old_version: int,
        target_version: int,
        new_version: int,
        operator: str,
    ):
        """记录回滚历史"""
        from edu_system.core.audit import manual_audit

        manual_audit(
            self.session,
            table_name="semester_configs",
            record_id=semester_id,
            action="ROLLBACK",
            old_values={"version": old_version},
            new_values={"version": new_version, "rolled_back_to": target_version},
            operator=operator,
        )


def get_config_service(session: Session = None) -> SemesterConfigService:
    """获取配置服务实例"""
    if session is None:
        session = next(get_session())
    return SemesterConfigService(session)
