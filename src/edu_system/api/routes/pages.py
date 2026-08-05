"""
Web 页面路由 — 渲染 Jinja2 模板

提供：登录页 / 首页 / 通用功能页占位（按 ui_config.json 的 6 域 26 页签动态渲染）
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from edu_system.api.deps import get_db
from edu_system.config.ui_config import get_config

router = APIRouter(tags=["web"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _optional_user(request: Request):
    """尝试解析当前用户，未登录返回 None（不抛 401）"""
    try:
        # 从 Authorization header 读取 Bearer token
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[7:]
        if not token:
            return None
        from edu_system.api.deps import decode_token
        from edu_system.database import get_session
        from edu_system.models import User

        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            return None
        with get_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                return None
            return user if bool(user.is_active) else None
    except Exception:
        return None


# 登录页无需登录
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user=Depends(_optional_user)):
    if user:
        return RedirectResponse(url="/")
    cfg = get_config()
    return templates.TemplateResponse(
        request,
        "login.html",
        {"config": cfg.model_dump() if hasattr(cfg, "model_dump") else cfg},
    )


# 首页需要登录
@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request, user=Depends(_optional_user)):
    if not user:
        return RedirectResponse(url="/login")
    cfg = get_config()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"config": cfg.model_dump() if hasattr(cfg, "model_dump") else cfg},
    )


# 通用功能页：/page/<domain_id>/<tab_id> — 动态渲染占位（后续各功能页逐步替换）
@router.get("/page/{domain_id}/{tab_id}", response_class=HTMLResponse)
async def page_placeholder(
    request: Request,
    domain_id: str,
    tab_id: str,
    user=Depends(_optional_user),
):
    if not user:
        return RedirectResponse(url="/login")
    cfg = get_config()
    domains = getattr(cfg, "domains", [])
    domain = next((d for d in domains if d.get("id") == domain_id), None)
    tab = None
    if domain:
        tab = next((t for t in domain.get("tabs", []) if t.get("id") == tab_id), None)

    # 优先渲染特定功能页模板（如 student_list.html），不存在则回退 index.html 占位
    specific = TEMPLATES_DIR / f"{tab_id}.html"
    template_name = specific.name if specific.exists() else "index.html"
    return templates.TemplateResponse(
        request,
        template_name,
        {
            "config": cfg.model_dump() if hasattr(cfg, "model_dump") else cfg,
            "active_domain": domain_id,
            "active_tab": tab_id,
        },
    )


# ===== Web 辅助 API（供前端页面调用） =====


@router.get("/api/meta/ui-config")
def ui_config_api():
    """返回完整 ui_config（前端导航/布局驱动）"""
    cfg = get_config()
    return cfg.model_dump() if hasattr(cfg, "model_dump") else cfg


@router.get("/api/stats/current")
def semester_current_stats(db=Depends(get_db)):
    """当前激活学期的概览统计（学生/班级/教师/考试数）"""
    from edu_system.database import get_active_semester
    from edu_system.models import Class, Exam, Semester, Student, Teacher

    semester_id = get_active_semester()
    if semester_id:
        sem = db.query(Semester).filter(Semester.id == semester_id).first()
        label = sem.label if sem else None
    else:
        sem = db.query(Semester).filter(Semester.is_active.is_(True)).first()
        label = sem.label if sem else None
        semester_id = sem.id if sem else None

    if not semester_id:
        return {"students": 0, "classes": 0, "teachers": 0, "exams": 0, "label": None}

    return {
        "semester_id": semester_id,
        "label": label,
        "students": db.query(Student).filter(Student.semester_id == semester_id).count(),
        "classes": db.query(Class).filter(Class.semester_id == semester_id).count(),
        "teachers": db.query(Teacher).filter(Teacher.semester_id == semester_id).count(),
        "exams": db.query(Exam).filter(Exam.semester_id == semester_id).count(),
    }


@router.get("/api/meta/services")
def services_status():
    """服务列表（启停状态，供系统设置页展示）"""
    from edu_system.api.service_registry import service_registry

    return {"services": service_registry.list_services()}
