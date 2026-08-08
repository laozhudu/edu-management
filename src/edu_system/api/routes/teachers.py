"""
教师 API 路由（M5-G：教师管理）

- GET /teachers: 教师列表（分页/搜索/筛选）
- GET /teachers/{teacher_id}: 教师详情
- GET /teachers/{teacher_id}/assignments: 教师任课安排
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.models import Class, ClassSubject, Semester, Subject, Teacher

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


class AssignmentItem(BaseModel):
    id: int
    teacher_id: int
    teacher_name: str
    teacher_no: str
    subject_id: int
    subject_name: str
    class_id: int
    class_name: str
    semester_id: int
    semester_label: str

    class Config:
        from_attributes = True


class AssignmentsListResponse(BaseModel):
    items: list[AssignmentItem]
    total: int
    page: int
    page_size: int


class WorkloadItem(BaseModel):
    teacher_id: int
    teacher_name: str
    teacher_no: str
    title: str
    course_count: int
    class_count: int
    total_hours: int
    weekly_hours: int


class WorkloadListResponse(BaseModel):
    items: list[WorkloadItem]
    total: int
    page: int
    page_size: int


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


@router.get("/assignments", response_model=AssignmentsListResponse)
def list_assignments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str = Query("", description="教师姓名/工号/科目关键字"),
    subject_id: int | None = Query(None, description="科目 ID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """任课分配列表（分页/搜索/筛选）"""
    q = db.query(ClassSubject).join(Teacher).join(Subject).join(Class).join(Semester)

    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(
            or_(
                Teacher.name.like(kw),
                Teacher.staff_no.like(kw),
                Subject.name.like(kw),
            )
        )

    if subject_id:
        q = q.filter(ClassSubject.subject_id == subject_id)

    total = q.count()
    items = (
        q.order_by(Teacher.name, Subject.name).offset((page - 1) * page_size).limit(page_size).all()
    )

    return AssignmentsListResponse(
        items=[
            AssignmentItem(
                id=a.id,
                teacher_id=a.teacher.id,
                teacher_name=a.teacher.name,
                teacher_no=a.teacher.staff_no,
                subject_id=a.subject.id,
                subject_name=a.subject.name,
                class_id=a.class_.id,
                class_name=a.class_.name,
                semester_id=a.semester.id,
                semester_label=a.semester.label,
            )
            for a in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/workload", response_model=WorkloadListResponse)
def list_workload(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str = Query("", description="教师姓名/工号关键字"),
    semester_id: int | None = Query(None, description="学期 ID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """教师工作量统计（分页/搜索/筛选）"""
    from sqlalchemy import func

    # 子查询：每个教师的任课统计
    subq = (
        db.query(
            Teacher.id.label("teacher_id"),
            Teacher.name.label("teacher_name"),
            Teacher.staff_no.label("teacher_no"),
            Teacher.title.label("title"),
            func.count(ClassSubject.id.distinct()).label("course_count"),
            func.count(ClassSubject.class_id.distinct()).label("class_count"),
            func.sum(Subject.full_mark).label("total_hours"),
        )
        .join(ClassSubject, ClassSubject.teacher_id == Teacher.id)
        .join(Subject, Subject.id == ClassSubject.subject_id)
        .filter(Subject.full_mark.isnot(None))
        .group_by(Teacher.id, Teacher.name, Teacher.staff_no, Teacher.title)
        .subquery()
    )

    q = db.query(subq)

    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(
            or_(
                subq.c.teacher_name.like(kw),
                subq.c.teacher_no.like(kw),
            )
        )

    if semester_id:
        # 这里需要关联学期，暂时简化处理
        pass

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    return WorkloadListResponse(
        items=[
            WorkloadItem(
                teacher_id=row.teacher_id,
                teacher_name=row.teacher_name,
                teacher_no=row.teacher_no,
                title=row.title,
                course_count=row.course_count or 0,
                class_count=row.class_count or 0,
                total_hours=row.total_hours or 0,
                weekly_hours=(row.total_hours or 0) // 18
                if row.total_hours
                else 0,  # 简化：假设18周
            )
            for row in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
