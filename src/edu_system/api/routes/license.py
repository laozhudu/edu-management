"""
授权 API 路由（M6 Sprint 7）

- POST /api/license/activate  激活（body: {code})
- GET  /api/license/status    查询授权状态
- GET  /api/license/machine-id 获取本机 ID（用于生成授权码）
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.models import User
from edu_system.services.license import LicenseService, get_machine_id

router = APIRouter(prefix="/license", tags=["授权"])


class ActivateRequest(BaseModel):
    code: str


@router.post("/activate")
def activate_license(
    request: ActivateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """激活授权码"""
    svc = LicenseService(db)
    result = svc.activate(request.code)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("reason", "激活失败"))
    return result


@router.get("/status")
def license_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询授权状态"""
    svc = LicenseService(db)
    return svc.get_status()


@router.get("/machine-id")
def machine_id():
    """获取本机 ID（供生成授权码用，无需登录）"""
    return {"machine_id": get_machine_id()}
