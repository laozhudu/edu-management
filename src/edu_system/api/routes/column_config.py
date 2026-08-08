"""
列配置持久化 API（M5-G：多端同步）

- GET /api/meta/column-config/{page_id}: 获取用户列配置
- PUT /api/meta/column-config/{page_id}: 保存用户列配置
"""

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.models import User, UserColumnConfig

router = APIRouter(prefix="/meta/column-config", tags=["列配置"])


class ColumnConfigItem(BaseModel):
    field: str
    title: str
    visible: bool = True
    width: int | None = None
    order: int | None = None


class ColumnConfigRequest(BaseModel):
    columns: list[ColumnConfigItem]


class ColumnConfigResponse(BaseModel):
    page_id: str
    columns: list[ColumnConfigItem]
    updated_at: str


router = APIRouter(prefix="/meta/column-config")


@router.get("/{page_id:path}")
def get_column_config(
    page_id: str = Path(..., description="页面标识，如 students/student_list"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的列配置"""
    config = (
        db.query(UserColumnConfig)
        .filter(
            UserColumnConfig.user_id == current_user.id,
            UserColumnConfig.page_id == page_id,
        )
        .first()
    )

    if not config:
        return ColumnConfigResponse(page_id=page_id, columns=[], updated_at="")

    return ColumnConfigResponse(
        page_id=config.page_id,
        columns=[ColumnConfigItem(**c) for c in config.columns],
        updated_at=config.updated_at.isoformat() if config.updated_at else "",
    )


@router.put("/{page_id:path}", response_model=ColumnConfigResponse)
def save_column_config(
    request: ColumnConfigRequest,
    page_id: str = Path(..., description="页面标识"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保存当前用户的列配置"""
    from datetime import datetime

    config = (
        db.query(UserColumnConfig)
        .filter(
            UserColumnConfig.user_id == current_user.id,
            UserColumnConfig.page_id == page_id,
        )
        .first()
    )

    columns_data = [c.dict() for c in request.columns]

    if config:
        config.columns = columns_data
        config.updated_at = datetime.utcnow()
    else:
        config = UserColumnConfig(
            user_id=current_user.id,
            page_id=page_id,
            columns=columns_data,
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    return ColumnConfigResponse(
        page_id=config.page_id,
        columns=[ColumnConfigItem(**c) for c in config.columns],
        updated_at=config.updated_at.isoformat() if config.updated_at else "",
    )
