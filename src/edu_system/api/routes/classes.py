"""
班级 API 路由

提供 Web 学生信息页新增/编辑时的班级下拉数据源。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.models import Class, User

router = APIRouter(prefix="/class", tags=["班级"])


@router.get("")
def class_list(
    page_size: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """班级列表（供学生新增/编辑下拉选择）"""
    items = db.query(Class).order_by(Class.name).limit(page_size).all()
    return {
        "items": [{"id": c.id, "name": c.name, "grade_id": c.grade_id} for c in items],
        "total": len(items),
    }
