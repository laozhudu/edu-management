"""
教师 API 路由（M5-G：教师管理）

- GET /teachers: 教师列表（分页/搜索/筛选）
- GET /teachers/{teacher_id}: 教师详情
- GET /teachers/{teacher_id}/assignments: 教师任课安排
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.core.permissions import Permission
from edu_system.models import Class, ClassSubject, Subject, Teacher, User

router = APIRouter(prefix="/teachers", tags=["教师管理"])


# ===== Pydantic 模型 =====


class SubjectSummary(BaseModel):
    id: int
    name: str
    class_name: str | None


class TeacherResponse(BaseModel):
    id: int
    staff_no: str
    name: str
    gender: str
    phone: str
    title: str
    education: str
    degree: str
    political_status: str
    birth_date: date | None
    work_start_date: date | None
    graduation_date: date | None
    semester_id: int
    note: str

    class SubjectSummary(BaseModel):
        id: int
        name: str
        class_name: str | None

    class Config:
        from_attributes = True


class TeacherListResponse(BaseModel):
    items: list[TeacherResponse]
    total: int
    page: int
    page_size: int


class TeacherAssignmentsResponse(BaseModel):
    teacher_id: int
    teacher_name: str
    assignments: list[SubjectSummary]


# ===== API 端点 =====


@router.get("", response_model=TeacherListResponse)
def list_teachers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str = Query("", description="姓名/工号关键字"),
    title: str = Query("", description="职称筛选"),
    semester_id: int | None = Query(None, description="学期 ID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """教师列表分页（M5-G）：搜索/筛选/分页，供 Web 教师管理页调用"""
    q = db.query(Teacher)

    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(or_(Teacher.name.like(kw), Teacher.staff_no.like(kw)))

    if title:
        q = q.filter(Teacher.title == title)

    if semester_id:
        q = q.filter(Teacher.semester_id == semester_id)

    total = q.count()
    items = q.order_by(Teacher.name).offset((page - 1) * page_size).limit(page_size).all()

    # 预加载任课信息
    assignments_map = {}
    if items:
        tids = [t.id for t in items]
        assigns = (
            db.query(ClassSubject)
            .join(Subject)
            .join(Class)
            .filter(ClassSubject.teacher_id.in_(tids))
            .all()
        )
        for a in assigns:
            assignments_map.setdefault(a.teacher_id, []).append(
                SubjectSummary(
                    id=a.subject.id,
                    name=a.subject.name,
                    class_name=a.class_.name if a.class_ else None,
                )
            )

    return TeacherListResponse(
        items=[
            TeacherResponse(
                id=t.id,
                staff_no=t.staff_no,
                name=t.name,
                gender=t.gender,
                phone=t.phone,
                title=t.title,
                education=t.education,
                degree=t.degree,
                political_status=t.political_status,
                birth_date=t.birth_date,
                work_start_date=t.work_start_date,
                graduation_date=t.graduation_date,
                semester_id=t.semester_id,
                note=t.note,
            )
            for t in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{teacher_id}", response_model=TeacherResponse)
def get_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """教师详情"""
    t = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="教师不存在")
    return TeacherResponse.model_validate(t)


@router.get("/{teacher_id}/assignments", response_model=TeacherAssignmentsResponse)
def get_teacher_assignments(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """教师任课安排（Web 教师管理页详情用）"""
    t = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="教师不存在")

    assigns = (
        db.query(ClassSubject)
        .join(Subject)
        .join(Class)
        .filter(ClassSubject.teacher_id == teacher_id)
        .all()
    )

    return TeacherAssignmentsResponse(
        teacher_id=t.id,
        teacher_name=t.name,
        assignments=[
            SubjectSummary(
                id=a.subject.id,
                name=a.subject.name,
                class_name=a.class_.name if a.class_ else None,
            )
            for a in assigns
        ],
    )
