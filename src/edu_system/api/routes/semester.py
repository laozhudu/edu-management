"""
学期管理 API 路由（M5-G：学期切换/列表/激活）

- GET /semester/list: 学期列表
- GET /semester/active: 激活学期
- POST /semester/active: 设置激活学期（Web 端切换用）
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from edu_system.api.deps import get_db, get_current_user
from edu_system.models import Semester, User

router = APIRouter(prefix="/semester", tags=["学期管理"])


class SemesterResponse(BaseModel):
    id: int
    label: str
    display_label: str
    start_date: Optional[str]
    end_date: Optional[str]
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


class SemesterListResponse(BaseModel):
    items: List[SemesterResponse]
    total: int


class ActiveSemesterResponse(BaseModel):
    semester: Optional[SemesterResponse]
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
    semester = db.query(Semester).filter(Semester.is_active == True).first()
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
            message="使用最新学期（无激活学期）"
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
        message="激活学期已切换"
    )