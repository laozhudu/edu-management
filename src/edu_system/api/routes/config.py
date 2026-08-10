"""
UI 配置 API 路由（M2-3 + G4 热加载）

暴露 ui_config 只读端点（品牌/学校/版本/6 域导航/页签/主题/状态栏），
供未来 Web 前端消费 —— 双端共享同一配置源 ui_config.json，
Web 端渲染与桌面端视觉一致的基础。

G4 快捷验收路径：
- GET  /api/config/version  → 配置文件 mtime 哈希（前端轮询对比，变了就刷新）
- POST /api/config/reload   → 服务端重新加载配置（改完文件手动触发）
"""

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from edu_system.api.deps import get_current_user
from edu_system.config.ui_config import _DEFAULT_CONFIG_PATH, get_config, reload_config
from edu_system.models import User

router = APIRouter(prefix="/config", tags=["UI 配置"])

_CONFIG_FILE = Path(_DEFAULT_CONFIG_PATH)


def _config_fingerprint() -> str:
    """配置文件内容指纹（mtime + 内容哈希，用于热加载检测）"""
    try:
        if not _CONFIG_FILE.exists():
            return "none"
        stat = _CONFIG_FILE.stat()
        with _CONFIG_FILE.open("rb") as f:
            content = f.read()
        return hashlib.sha256(f"{stat.st_mtime_ns}:{len(content)}".encode()).hexdigest()[:16]
    except Exception:
        return "none"


@router.get("")
def get_ui_config() -> dict:
    """返回完整 UI 配置（只读；公开信息：品牌/导航结构，不含业务数据）"""
    cfg = get_config()
    return {
        "app": cfg.app.model_dump(),
        "topbar": cfg.topbar.model_dump(),
        "theme": cfg.theme.model_dump(),
        "domains": cfg.domains_parsed,
        "statusbar": cfg.statusbar.model_dump(),
    }


@router.get("/version")
def config_version() -> dict:
    """配置版本指纹（G4 热加载：前端轮询此端点，指纹变化即刷新页面）"""
    return {"fingerprint": _config_fingerprint(), "path": str(_CONFIG_FILE)}


@router.post("/reload")
def reload_ui_config(
    current_user: User = Depends(get_current_user),
):
    """重新加载配置（G4：改完 ui_config.json 后触发，两端同时生效）"""
    try:
        cfg = reload_config()
        return {
            "success": True,
            "message": "配置已重新加载",
            "fingerprint": _config_fingerprint(),
            "school": cfg.app.school_name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置加载失败: {e}")


class SaveUIConfigRequest(BaseModel):
    """样式配置保存请求（可写回 theme/topbar/login/statusbar 节）"""

    theme: dict | None = None
    topbar: dict | None = None
    login: dict | None = None
    statusbar: dict | None = None


@router.post("/save-ui")
def save_ui_config(
    body: SaveUIConfigRequest,
    current_user: User = Depends(get_current_user),
):
    """保存界面样式配置（写回 ui_config.json 合并更新 + reload 生效）

    支持节：theme（品牌/强调色/侧栏/密度）、topbar（开关/快捷键）、
    login（登录框尺寸/字体/品牌区）、statusbar（状态栏项）。
    仅覆盖传入字段，其余保留；写文件后自动 reload 双端生效。
    """
    import json

    try:
        raw = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置失败: {e}")

    payload = body.model_dump(exclude_unset=True)
    for key in ("theme", "topbar", "login", "statusbar"):
        if key in payload and payload[key]:
            merged = dict(raw.get(key) or {})
            merged.update(payload[key])
            raw[key] = merged

    try:
        _CONFIG_FILE.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        cfg = reload_config()
        return {
            "success": True,
            "message": "界面样式已保存并生效",
            "fingerprint": _config_fingerprint(),
            "theme": cfg.theme.model_dump() if hasattr(cfg.theme, "model_dump") else cfg.theme,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {e}")
