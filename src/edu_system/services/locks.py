"""
数据锁定服务
核心功能：
1. 通用锁定表 DataLock：支持行级/表级/学期级
2. 三级锁语义：soft/hard/semester
3. SQLAlchemy before_flush 拦截
4. 批量锁定/解锁
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import Session as SASession

from edu_system.core.permissions import Permission, has_permission
from edu_system.database import get_session
from edu_system.models import DataLock, Semester


class LockLevel(Enum):
    """锁定级别"""

    NONE = "none"  # 无锁定
    SOFT = "soft"  # 软锁：提示只读，管理员可强制编辑
    HARD = "hard"  # 硬锁：仅 DATA_UNLOCK 权限可解锁
    SEMESTER = "semester"  # 学期锁：整学期只读（归档态）


class LockError(Exception):
    """锁定异常"""

    def __init__(self, message: str, lock_info: dict = None):
        super().__init__(message)
        self.lock_info = lock_info or {}


class DataLockService:
    """数据锁定服务"""

    def __init__(self, session: Session):
        self.session = session

    # ===== 锁定操作 =====

    def lock(
        self,
        semester_id: int,
        entity_type: str,
        entity_id: int = None,
        lock_level: LockLevel = LockLevel.SOFT,
        locked_by: str = "system",
        reason: str = "",
    ) -> DataLock:
        """
        加锁
        entity_id=None 表示表级锁
        """
        # 检查是否已锁定
        existing = self._get_lock(semester_id, entity_type, entity_id)
        if existing:
            # 升级锁级别
            if self._lock_level_priority(lock_level) > self._lock_level_priority(
                LockLevel(existing.lock_level)
            ):
                existing.lock_level = lock_level.value
                existing.locked_by = locked_by
                existing.locked_at = datetime.now()
                existing.reason = reason
                self.session.commit()
                return existing
            return existing

        lock = DataLock(
            semester_id=semester_id,
            entity_type=entity_type,
            entity_id=entity_id,
            lock_level=lock_level.value,
            locked_by=locked_by,
            locked_at=datetime.now(),
            reason=reason,
        )
        self.session.add(lock)
        self.session.commit()
        return lock

    def unlock(
        self,
        semester_id: int,
        entity_type: str,
        entity_id: int = None,
        unlocker: str = "system",
        force: bool = False,
    ) -> bool:
        """
        解锁
        force=True: 忽略权限检查（仅 DATA_UNLOCK 或管理员）
        """
        lock = self._get_lock(semester_id, entity_type, entity_id)
        if not lock:
            return True  # 本身未锁定

        # 权限检查
        if not force and lock.lock_level in (LockLevel.HARD.value, LockLevel.SEMESTER.value):
            # 需要 DATA_UNLOCK 权限
            if not has_permission(Permission.DATA_UNLOCK):
                raise LockError(
                    "硬锁/学期锁需要 DATA_UNLOCK 权限解锁",
                    {"lock_level": lock.lock_level, "locked_by": lock.locked_by},
                )

        self.session.delete(lock)
        self.session.commit()
        return True

    def batch_lock(self, semester_id: int, locks: list[dict]) -> list[DataLock]:
        """批量加锁"""
        result = []
        for item in locks:
            lock = self.lock(
                semester_id=semester_id,
                entity_type=item["entity_type"],
                entity_id=item.get("entity_id"),
                lock_level=LockLevel(item.get("lock_level", "soft")),
                locked_by=item.get("locked_by", "system"),
                reason=item.get("reason", ""),
            )
            result.append(lock)
        return result

    def batch_unlock(
        self, semester_id: int, items: list[dict], unlocker: str = "system", force: bool = False
    ) -> int:
        """批量解锁"""
        count = 0
        for item in items:
            try:
                self.unlock(
                    semester_id=semester_id,
                    entity_type=item["entity_type"],
                    entity_id=item.get("entity_id"),
                    unlocker=unlocker,
                    force=force,
                )
                count += 1
            except LockError:
                pass  # 记录日志但继续
        return count

    def lock_semester(
        self, semester_id: int, locked_by: str = "system", reason: str = "学期归档"
    ) -> DataLock:
        """学期级锁定：整学期只读"""
        return self.lock(
            semester_id=semester_id,
            entity_type="semester",
            entity_id=semester_id,
            lock_level=LockLevel.SEMESTER,
            locked_by=locked_by,
            reason=reason,
        )

    def unlock_semester(
        self, semester_id: int, unlocker: str = "system", force: bool = True
    ) -> bool:
        """解锁学期"""
        return self.unlock(
            semester_id=semester_id,
            entity_type="semester",
            entity_id=semester_id,
            unlocker=unlocker,
            force=force,
        )

    # ===== 查询操作 =====

    def get_lock(
        self, semester_id: int, entity_type: str, entity_id: int = None
    ) -> DataLock | None:
        """获取锁信息"""
        return self._get_lock(semester_id, entity_type, entity_id)

    def is_locked(self, semester_id: int, entity_type: str, entity_id: int = None) -> bool:
        """检查是否被锁定"""
        return self._get_lock(semester_id, entity_type, entity_id) is not None

    @classmethod
    def check_lock(cls, db: Session, entity_type: str, entity_id: int) -> DataLock | None:
        """检查指定实体是否被锁定（类方法，用于 API 调用）"""
        # 获取当前活跃学期
        current_semester = db.query(Semester).filter(Semester.is_active).first()
        if not current_semester:
            return None
        service = cls(db)
        return service._get_lock(current_semester.id, entity_type, entity_id)

    def get_lock_level(
        self, semester_id: int, entity_type: str, entity_id: int = None
    ) -> LockLevel | None:
        """获取锁级别"""
        lock = self._get_lock(semester_id, entity_type, entity_id)
        return LockLevel(lock.lock_level) if lock else None

    def list_locks(self, semester_id: int = None, entity_type: str = None) -> list[DataLock]:
        """列出锁"""
        query = self.session.query(DataLock)
        if semester_id:
            query = query.filter(DataLock.semester_id == semester_id)
        if entity_type:
            query = query.filter(DataLock.entity_type == entity_type)
        return query.order_by(DataLock.locked_at.desc()).all()

    # ===== 内部方法 =====

    def _get_lock(
        self, semester_id: int, entity_type: str, entity_id: int = None
    ) -> DataLock | None:
        query = self.session.query(DataLock).filter(
            DataLock.semester_id == semester_id,
            DataLock.entity_type == entity_type,
        )
        if entity_id is not None:
            query = query.filter(DataLock.entity_id == entity_id)
        else:
            query = query.filter(DataLock.entity_id.is_(None))
        return query.first()

    def _lock_level_priority(self, level: LockLevel) -> int:
        """锁级别优先级：数值越大越强"""
        priorities = {
            LockLevel.NONE: 0,
            LockLevel.SOFT: 1,
            LockLevel.HARD: 2,
            LockLevel.SEMESTER: 3,
        }
        return priorities.get(level, 0)

    # ===== 业务场景便捷方法 =====

    def lock_scores_after_publish(self, exam_id: int, locked_by: str = "system") -> list[DataLock]:
        """成绩发布后锁定：锁定该考试所有成绩"""
        from edu_system.models import Exam

        exam = self.session.query(Exam).get(exam_id)
        if not exam:
            return []

        locks = []
        # 锁定考试级别
        locks.append(
            self.lock(
                semester_id=exam.semester_id,
                entity_type="exam_scores",
                entity_id=exam_id,
                lock_level=LockLevel.HARD,
                locked_by=locked_by,
                reason=f'考试 "{exam.name}" 成绩已发布',
            )
        )
        return locks

    def lock_movements_after_approval(
        self, movement_ids: list[int], locked_by: str = "system"
    ) -> list[DataLock]:
        """学籍变动审核通过后锁定"""
        from edu_system.models import StudentMovement

        locks = []
        for mid in movement_ids:
            mov = self.session.query(StudentMovement).get(mid)
            if mov:
                locks.append(
                    self.lock(
                        semester_id=mov.semester_id,
                        entity_type="student_movement",
                        entity_id=mid,
                        lock_level=LockLevel.HARD,
                        locked_by=locked_by,
                        reason="学籍变动已审核通过",
                    )
                )
        return locks

    def lock_exam_numbers(self, semester_id: int, locked_by: str = "system") -> DataLock:
        """考号生成后锁定"""
        return self.lock(
            semester_id=semester_id,
            entity_type="exam_numbers",
            entity_id=semester_id,
            lock_level=LockLevel.HARD,
            locked_by=locked_by,
            reason="考号已生成",
        )


# ===== SQLAlchemy before_flush 拦截器 =====


def _is_entity_locked(session: Session, entity) -> DataLock | None:
    """检查实体是否被锁定"""
    # 获取实体对应的表名和主键
    mapper = inspect(entity).mapper
    table_name = mapper.class_.__tablename__
    pk = mapper.primary_key

    # 获取学期 ID（从实体或 session 上下文）
    semester_id = getattr(entity, "semester_id", None)
    if semester_id is None:
        # 尝试从关联获取
        from edu_system.database import get_active_semester

        semester_id = get_active_semester()

    if not semester_id:
        return None

    # 实体 ID
    entity_id = getattr(entity, pk[0].name, None) if pk else None

    # 检查三个层级的锁
    lock_service = DataLockService(session)

    # 1. 行级锁
    row_lock = lock_service.get_lock(semester_id, table_name, entity_id)
    if row_lock:
        return row_lock

    # 2. 表级锁
    table_lock = lock_service.get_lock(semester_id, table_name, None)
    if table_lock:
        return table_lock

    # 3. 学期级锁
    semester_lock = lock_service.get_lock(semester_id, "semester", semester_id)
    if semester_lock:
        return semester_lock

    return None


def _check_lock_before_flush(session: Session, flush_context, instances):
    """before_flush 事件：检查脏对象是否被锁定"""
    # 遍历新增/修改/删除的对象
    for obj in session.dirty:
        # 跳过系统表
        if obj.__class__.__tablename__ in (
            "audit_logs",
            "semester_configs",
            "global_settings",
            "data_locks",
        ):
            continue

        lock = _is_entity_locked(session, obj)
        if lock:
            # 检查锁级别
            if lock.lock_level == LockLevel.SOFT.value:
                # 软锁：仅警告，允许管理员强制
                import logging

                logging.warning(
                    f"软锁警告: {obj.__class__.__name__}#{getattr(obj, 'id', '?')} 被软锁定，允许强制修改"
                )
                continue  # 允许继续

            elif lock.lock_level in (LockLevel.HARD.value, LockLevel.SEMESTER.value):
                # 硬锁/学期锁：检查权限
                from edu_system.core.permissions import Permission, has_permission

                if not has_permission(Permission.DATA_UNLOCK):
                    raise LockError(
                        f"对象被 {lock.lock_level} 锁定，无法修改。锁定原因: {lock.reason}",
                        {
                            "entity_type": lock.entity_type,
                            "entity_id": lock.entity_id,
                            "lock_level": lock.lock_level,
                            "locked_by": lock.locked_by,
                            "reason": lock.reason,
                        },
                    )

    # 检查新增对象（新增也要检查表级/学期级锁）
    for obj in session.new:
        if obj.__class__.__tablename__ in (
            "audit_logs",
            "semester_configs",
            "global_settings",
            "data_locks",
        ):
            continue

        lock = _is_entity_locked(session, obj)
        if lock and lock.lock_level in (LockLevel.HARD.value, LockLevel.SEMESTER.value):
            from edu_system.core.permissions import Permission, has_permission

            if not has_permission(Permission.DATA_UNLOCK):
                raise LockError(
                    f"表被 {lock.lock_level} 锁定，无法新增数据。锁定原因: {lock.reason}",
                    {
                        "entity_type": lock.entity_type,
                        "entity_id": lock.entity_id,
                        "lock_level": lock.lock_level,
                        "reason": lock.reason,
                    },
                )


# 注册 before_flush 事件
def register_lock_interceptor():
    """注册锁定拦截器（应用启动时调用一次）"""
    event.listen(SASession, "before_flush", _check_lock_before_flush)


def get_lock_service(session: Session = None) -> DataLockService:
    """获取锁定服务实例"""
    if session is None:
        session = next(get_session())
    return DataLockService(session)
