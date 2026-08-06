"""
配置继承 API 路由（M5-E5）

- GET  /semester/{id}/inherit/preview?source_id=&target_id=
      四色差异预览（新增绿/修改蓝/保留灰/冲突红，不落库）
- POST /semester/{id}/inherit/execute
      执行继承（深拷贝 + 选择性覆盖 + 版本记录 + 审计）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.models import User
from edu_system.services.semester_config import SemesterConfigService

router = APIRouter(prefix="/semester", tags=["学期配置"])


class InheritExecuteRequest(BaseModel):
    source_semester_id: int
    target_semester_id: int
    overwrite_keys: list[str] = []


@router.get("/{semester_id}/inherit/preview")
def preview_inherit_api(
    semester_id: int,
    source_id: int,
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """四色差异预览（M5-E5）

    source_id: 源学期；target_id: 目标学期
    返回差异列表（type: added/modified/unchanged/conflict）
    """
    svc = SemesterConfigService(db)
    try:
        result = svc.preview_inherit(source_id, target_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.post("/{semester_id}/inherit/execute")
def execute_inherit_api(
    semester_id: int,
    request: InheritExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """执行配置继承（M5-E5）：深拷贝 + 覆盖 + 版本记录 + 审计"""
    svc = SemesterConfigService(db)
    try:
        result = svc.execute_inherit(
            request.source_semester_id,
            request.target_semester_id,
            overwrite_keys=request.overwrite_keys,
            operator=current_user.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not result.get("success", False):
        raise HTTPException(status_code=409, detail=result.get("error", "继承失败"))
    return result


# ===== M5-C2 配置版本回滚 =====


@router.get("/{semester_id}/versions")
def list_versions_api(
    semester_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取学期所有配置版本列表（M5-C2）"""
    svc = SemesterConfigService(db)
    try:
        return svc.get_versions(semester_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{semester_id}/versions/{version}")
def get_version_configs_api(
    semester_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指定版本的所有配置（M5-C2）"""
    svc = SemesterConfigService(db)
    try:
        configs = svc.get_version_configs(semester_id, version)
        return {"semester_id": semester_id, "version": version, "configs": configs}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{semester_id}/versions/{version}/rollback")
def rollback_version_api(
    semester_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """回滚到指定版本（M5-C2）"""
    svc = SemesterConfigService(db)
    try:
        result = svc.rollback_to_version(semester_id, version, operator=current_user.username)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not result.get("success", False):
        raise HTTPException(status_code=409, detail=result.get("error", "回滚失败"))
    return result
