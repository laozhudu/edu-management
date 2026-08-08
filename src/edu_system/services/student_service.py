"""
学生服务层 — Web API 与桌面共用的 CRUD 逻辑

从桌面端 StudentView 的本地直连模式提炼，供 FastAPI 路由复用：
- create_student / update_student / delete_student / get_student / list_students
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from edu_system.models import Class, Student


class StudentError(Exception):
    """学生业务异常（校验失败等）"""


def _validate_student_data(data: dict) -> None:
    """基础校验：姓名必填、班级存在"""
    name = (data.get("name") or "").strip()
    if not name:
        raise StudentError("学生姓名不能为空")
    class_id = data.get("class_id")
    if not class_id:
        raise StudentError("必须指定班级")


def _resolve_semester_id(db: Session, data: dict) -> int | None:
    """解析学期：优先请求传入，回退当前激活线程学期，最后查活跃学期"""
    if data.get("semester_id"):
        return data["semester_id"]
    try:
        from edu_system.database import get_active_semester

        active = get_active_semester()
        if active:
            return active
    except Exception:
        pass
    # 兜底：查数据库 is_active 学期
    try:
        from edu_system.models import Semester

        sem = db.query(Semester).filter(Semester.is_active.is_(True)).first()
        return sem.id if sem else None
    except Exception:
        return None


def create_student(db: Session, data: dict) -> Student:
    """创建学生"""
    _validate_student_data(data)
    if data.get("class_id"):
        cls = db.query(Class).filter(Class.id == data["class_id"]).first()
        if cls is None:
            raise StudentError(f"班级不存在: {data['class_id']}")
    payload = {k: v for k, v in data.items() if hasattr(Student, k)}
    # 注入学期（学生表 semester_id 非空）
    sem_id = _resolve_semester_id(db, data)
    if sem_id is None:
        raise StudentError("无法确定当前学期，请先在学期设置中激活")
    payload["semester_id"] = sem_id
    student = Student(**payload)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def update_student(db: Session, student_id: int, data: dict) -> Student:
    """更新学生（部分字段）"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise StudentError(f"学生不存在: {student_id}")
    if "name" in data and not (data.get("name") or "").strip():
        raise StudentError("学生姓名不能为空")
    if data.get("class_id"):
        cls = db.query(Class).filter(Class.id == data["class_id"]).first()
        if cls is None:
            raise StudentError(f"班级不存在: {data['class_id']}")
    for k, v in data.items():
        if hasattr(Student, k) and k != "id":
            setattr(student, k, v)
    db.commit()
    db.refresh(student)
    return student


def delete_student(db: Session, student_id: int) -> bool:
    """删除学生（返回是否实际删除）"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        return False
    db.delete(student)
    db.commit()
    return True


def get_student(db: Session, student_id: int) -> Student | None:
    """按 ID 查询学生"""
    return db.query(Student).filter(Student.id == student_id).first()


def list_students(
    db: Session,
    keyword: str = "",
    class_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Student], int]:
    """学生分页列表（支持关键字/班级筛选）"""
    query = db.query(Student)
    if keyword:
        kw = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Student.name.like(kw),
                Student.student_no.like(kw),
                Student.student_code.like(kw),
            )
        )
    if class_id:
        query = query.filter(Student.class_id == class_id)
    total = query.count()
    items = (
        query.order_by(Student.class_id, Student.student_no)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total
