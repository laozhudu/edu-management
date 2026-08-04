"""
UI 配置 API 路由（M2-3）

暴露 ui_config 只读端点（品牌/学校/版本/6 域导航/页签/主题/状态栏），
供未来 Web 前端消费 —— 双端共享同一配置源 ui_config.json，
Web 端渲染与桌面端视觉一致的基础。
"""

from fastapi import APIRouter

from edu_system.config.ui_config import get_config

router = APIRouter(prefix="/config", tags=["UI 配置"])


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
