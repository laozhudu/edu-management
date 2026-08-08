"""
学期管理 API 路由（M5-G：学期切换/列表/激活）

- GET /semester/list: 学期列表
- GET /semester/active: 激活学期
- POST /semester/active: 设置激活学期（Web 端切换用）
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.models import Semester, User

router = APIRouter(prefix="/semester", tags=["学期管理"])


class SemesterResponse(BaseModel):
    id: int
    label: str
    display_label: str
    start_date: str | None
    end_date: str | None
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


class SemesterListResponse(BaseModel):
    items: list[SemesterResponse]
    total: int


class ActiveSemesterResponse(BaseModel):
    semester: SemesterResponse | None
    message: str = ""


class SetActiveRequest(BaseModel):
    semester_id: int


@router.get("/list", response_model=SemesterListResponse)
def list_semesters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有学期列表"""
    semesters = db.query(Semester).order_by(Semester.sort_order.desc(), Semester.id.desc()).all()
    return SemesterListResponse(
        items=[
            SemesterResponse(
                id=s.id,
                label=s.label,
                display_label=s.display_label,
                start_date=s.start_date.isoformat() if s.start_date else None,
                end_date=s.end_date.isoformat() if s.end_date else None,
                is_active=s.is_active,
                sort_order=s.sort_order,
            )
            for s in semesters
        ],
        total=len(semesters),
    )


@router.get("/active", response_model=ActiveSemesterResponse)
def get_active_semester_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前激活学期（Web 端顶部栏显示用）"""
    from edu_system.database import get_active_semester

    # 优先从线程上下文获取（桌面端已设置）
    active_id = get_active_semester()

    if active_id:
        semester = db.query(Semester).filter(Semester.id == active_id).first()
        if semester:
            return ActiveSemesterResponse(
                semester=SemesterResponse(
                    id=semester.id,
                    label=semester.label,
                    display_label=semester.display_label,
                    start_date=semester.start_date.isoformat() if semester.start_date else None,
                    end_date=semester.end_date.isoformat() if semester.end_date else None,
                    is_active=semester.is_active,
                    sort_order=semester.sort_order,
                )
            )

    # 回退：DB 中 is_active=True 的学期
    semester = db.query(Semester).filter(Semester.is_active).first()
    if semester:
        return ActiveSemesterResponse(
            semester=SemesterResponse(
                id=semester.id,
                label=semester.label,
                display_label=semester.display_label,
                start_date=semester.start_date.isoformat() if semester.start_date else None,
                end_date=semester.end_date.isoformat() if semester.end_date else None,
                is_active=semester.is_active,
                sort_order=semester.sort_order,
            )
        )

    # 再回退：最新学期
    semester = db.query(Semester).order_by(Semester.id.desc()).first()
    if semester:
        return ActiveSemesterResponse(
            semester=SemesterResponse(
                id=semester.id,
                label=semester.label,
                display_label=semester.display_label,
                start_date=semester.start_date.isoformat() if semester.start_date else None,
                end_date=semester.end_date.isoformat() if semester.end_date else None,
                is_active=semester.is_active,
                sort_order=semester.sort_order,
            ),
            message="使用最新学期（无激活学期）",
        )

    return ActiveSemesterResponse(semester=None, message="无可用学期")


@router.post("/active", response_model=ActiveSemesterResponse)
def set_active_semester_api(
    request: SetActiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """设置激活学期（Web 端顶部栏切换用）"""
    from edu_system.database import set_active_semester

    semester = db.query(Semester).filter(Semester.id == request.semester_id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="学期不存在")

    # 设置线程局部激活学期（当前请求生效）
    set_active_semester(request.semester_id)

    # 同时更新 DB：清除所有 is_active，设置新的
    db.query(Semester).update({Semester.is_active: False})
    semester.is_active = True
    db.commit()

    return ActiveSemesterResponse(
        semester=SemesterResponse(
            id=semester.id,
            label=semester.label,
            display_label=semester.display_label,
            start_date=semester.start_date.isoformat() if semester.start_date else None,
            end_date=semester.end_date.isoformat() if semester.end_date else None,
            is_active=semester.is_active,
            sort_order=semester.sort_order,
        ),
        message="激活学期已切换",
    )


class SemesterCreateRequest(BaseModel):
    """创建学期请求"""

    label: str
    year_start: int
    semester: str = "1"
    sort_order: int = 1
    start_date: str | None = None
    end_date: str | None = None


@router.post("", status_code=201)
def create_semester(
    body: SemesterCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建学期（Web 学期设置页新建）"""
    from datetime import date

    from edu_system.models import AcademicYear

    label = body.label.strip()
    if not label:
        raise HTTPException(status_code=400, detail="学期名称不能为空")
    dup = db.query(Semester).filter(Semester.label == label).first()
    if dup:
        raise HTTPException(status_code=400, detail=f"学期「{label}」已存在")

    # 查找或创建学年（name 格式：2027-2028）
    ay_name = f"{body.year_start}-{body.year_start + 1}"
    ay = db.query(AcademicYear).filter(AcademicYear.name == ay_name).first()
    if ay is None:
        ay = AcademicYear(name=ay_name, sort_order=body.year_start)
        db.add(ay)
        db.flush()

    def _parse_date(v: str | None) -> date | None:
        if not v:
            return None
        try:
            return date.fromisoformat(v)
        except ValueError:
            return None

    sem = Semester(
        academic_year_id=ay.id,
        year_start=body.year_start,
        semester=body.semester,
        label=label,
        sort_order=body.sort_order,
        start_date=_parse_date(body.start_date),
        end_date=_parse_date(body.end_date),
        is_active=False,
    )
    db.add(sem)
    db.commit()
    db.refresh(sem)
    return {"id": sem.id, "label": sem.label}
