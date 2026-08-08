"""
班级 API 路由

提供 Web 学生信息页新增/编辑时的班级下拉数据源 + 班级管理 CRUD。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.models import Class, User

router = APIRouter(prefix="/class", tags=["班级"])


@router.get("/grades")
def grade_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """年级列表（班级新增/编辑下拉数据源）"""
    from edu_system.models import Grade

    items = db.query(Grade).order_by(Grade.id).all()
    return {"items": [{"id": g.id, "name": g.name} for g in items], "total": len(items)}


class ClassCreateRequest(BaseModel):
    """创建班级请求"""

    name: str
    grade_id: int
    head_teacher: str = ""
    class_type: str = ""
    room: str = ""


class ClassUpdateRequest(BaseModel):
    """更新班级请求（部分字段）"""

    name: str | None = None
    grade_id: int | None = None
    head_teacher: str | None = None
    class_type: str | None = None
    room: str | None = None


def _resolve_semester_id(db: Session) -> int:
    """解析当前学期：优先激活线程学期，回退数据库活跃学期"""
    try:
        from edu_system.database import get_active_semester

        active = get_active_semester()
        if active:
            return active
    except Exception:
        pass
    from edu_system.models import Semester

    sem = db.query(Semester).filter(Semester.is_active.is_(True)).first()
    if sem is None:
        raise HTTPException(status_code=400, detail="无法确定当前学期，请先在学期设置中激活")
    return sem.id


@router.get("")
def class_list(
    page_size: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """班级列表（供学生新增/编辑下拉选择）"""
    items = db.query(Class).order_by(Class.name).limit(page_size).all()
    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "grade_id": c.grade_id,
                "grade_name": c.grade.name if c.grade else None,
                "head_teacher": c.head_teacher,
                "class_type": c.class_type,
                "room": c.room,
                "student_count": len(c.students) if hasattr(c, "students") else 0,
            }
            for c in items
        ],
        "total": len(items),
    }


@router.post("", status_code=201)
def create_class(
    body: ClassCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建班级"""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="班级名称不能为空")
    # 重名校验（同年级学期内唯一）
    sem_id = _resolve_semester_id(db)
    dup = (
        db.query(Class)
        .filter(Class.grade_id == body.grade_id, Class.semester_id == sem_id, Class.name == name)
        .first()
    )
    if dup:
        raise HTTPException(status_code=400, detail=f"班级「{name}」已存在")
    cls = Class(
        name=name,
        grade_id=body.grade_id,
        semester_id=sem_id,
        head_teacher=body.head_teacher,
        class_type=body.class_type,
        room=body.room,
    )
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return {"id": cls.id, "name": cls.name}


@router.put("/{class_id}")
def update_class(
    class_id: int,
    body: ClassUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新班级"""
    cls = db.query(Class).filter(Class.id == class_id).first()
    if cls is None:
        raise HTTPException(status_code=404, detail=f"班级不存在: {class_id}")
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="班级名称不能为空")
        cls.name = name
    for field in ("grade_id", "head_teacher", "class_type", "room"):
        val = getattr(body, field)
        if val is not None:
            setattr(cls, field, val)
    db.commit()
    db.refresh(cls)
    return {"id": cls.id, "name": cls.name}


@router.delete("/{class_id}")
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除班级（有学生的班级拒绝删除）"""
    cls = db.query(Class).filter(Class.id == class_id).first()
    if cls is None:
        raise HTTPException(status_code=404, detail=f"班级不存在: {class_id}")
    student_count = len(cls.students) if hasattr(cls, "students") else 0
    if student_count:
        raise HTTPException(
            status_code=400, detail=f"班级「{cls.name}」有 {student_count} 名学生，不能删除"
        )
    db.delete(cls)
    db.commit()
    return {"ok": True}
