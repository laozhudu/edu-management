"""
教师服务层 — Web API 与桌面共用的 CRUD 逻辑

参考 student_service 模式，供 FastAPI 路由复用。
"""

from sqlalchemy.orm import Session

from edu_system.models import Teacher


class TeacherError(Exception):
    """教师业务异常（校验失败等）"""


def _resolve_semester_id(db: Session) -> int | None:
    """解析学期：优先当前激活线程学期，回退数据库活跃学期"""
    try:
        from edu_system.database import get_active_semester

        active = get_active_semester()
        if active:
            return active
    except Exception:
        pass
    try:
        from edu_system.models import Semester

        sem = db.query(Semester).filter(Semester.is_active.is_(True)).first()
        return sem.id if sem else None
    except Exception:
        return None


def create_teacher(db: Session, data: dict) -> Teacher:
    """创建教师"""
    name = (data.get("name") or "").strip()
    if not name:
        raise TeacherError("教师姓名不能为空")
    # 姓名唯一校验
    dup = db.query(Teacher).filter(Teacher.name == name).first()
    if dup:
        raise TeacherError(f"教师「{name}」已存在")
    payload = {k: v for k, v in data.items() if hasattr(Teacher, k)}
    sem_id = _resolve_semester_id(db)
    if sem_id is None:
        raise TeacherError("无法确定当前学期，请先在学期设置中激活")
    payload["semester_id"] = sem_id
    teacher = Teacher(**payload)
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


def update_teacher(db: Session, teacher_id: int, data: dict) -> Teacher:
    """更新教师（部分字段）"""
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if teacher is None:
        raise TeacherError(f"教师不存在: {teacher_id}")
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            raise TeacherError("教师姓名不能为空")
        dup = db.query(Teacher).filter(Teacher.name == name, Teacher.id != teacher_id).first()
        if dup:
            raise TeacherError(f"教师「{name}」已存在")
    for k, v in data.items():
        if hasattr(Teacher, k) and k != "id":
            setattr(teacher, k, v)
    db.commit()
    db.refresh(teacher)
    return teacher


def delete_teacher(db: Session, teacher_id: int) -> bool:
    """删除教师（返回是否实际删除）"""
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if teacher is None:
        return False
    db.delete(teacher)
    db.commit()
    return True


def get_teacher(db: Session, teacher_id: int) -> Teacher | None:
    """按 ID 查询教师"""
    return db.query(Teacher).filter(Teacher.id == teacher_id).first()
