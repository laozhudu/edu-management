"""
服务注册表：管理所有可暴露的 API 服务
支持：持久化配置、数据库同步、内存缓存
"""

from sqlalchemy.orm import Session

from edu_system.database import get_session
from edu_system.models import ServiceConfig


class ServiceRegistry:
    """服务注册表：管理所有可暴露的 API 服务"""

    # 单一数据源：全部默认服务定义（P1 重构，消除三处重复）
    # 供 _init_default_services 注册 / _get_default_service 查询 / default_codes 派生
    DEFAULT_SERVICES = {
        "score": {
            "name": "成绩录入",
            "description": "教师录入成绩、Excel导入、排名计算",
            "api_prefix": "/api/score",
            "enabled": True,
            "required_permissions": ["score:entry"],
            "allowed_roles": ["teacher", "director", "admin"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "attendance": {
            "name": "考勤打卡",
            "description": "学生考勤打卡、请假审批、统计",
            "api_prefix": "/api/attendance",
            "enabled": True,
            "required_permissions": ["attendance:entry"],
            "allowed_roles": ["teacher", "director", "admin"],
            "rate_limit": 200,
            "rate_limit_window": 60,
        },
        "score_query": {
            "name": "学生查分",
            "description": "学生/家长查询成绩、排名、趋势",
            "api_prefix": "/api/score/query",
            "enabled": True,
            "required_permissions": ["score:query"],
            "allowed_roles": ["student", "parent", "teacher", "director", "admin"],
            "rate_limit": 300,
            "rate_limit_window": 60,
        },
        "exam_schedule": {
            "name": "考试安排",
            "description": "考试时间表、考场分布、准考证",
            "api_prefix": "/api/exam",
            "enabled": True,
            "required_permissions": ["exam:view"],
            "allowed_roles": ["student", "parent", "teacher", "director", "admin"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "exam": {
            "name": "考试管理",
            "description": "考试 CRUD、考场座位、监考、准考证",
            "api_prefix": "/api/exam",
            "enabled": True,
            "required_permissions": ["exam:view"],
            "allowed_roles": ["teacher", "director", "admin"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "meta": {
            "name": "字段元数据",
            "description": "动态字段注册表增删改查、实体自定义字段读写",
            "api_prefix": "/api/meta",
            "enabled": True,
            "required_permissions": ["config:view"],
            "allowed_roles": ["admin", "director"],
            "rate_limit": 60,
            "rate_limit_window": 60,
        },
        "class": {
            "name": "班级管理",
            "description": "班级列表（Web 学生新增/编辑下拉数据源）",
            "api_prefix": "/api/class",
            "enabled": True,
            "required_permissions": ["class:view"],
            "allowed_roles": ["teacher", "director", "admin"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "class_roster": {
            "name": "班级名单",
            "description": "班级学生名单、基本信息查询",
            "api_prefix": "/api/class",
            "enabled": True,
            "required_permissions": ["class:view"],
            "allowed_roles": ["teacher", "director", "admin"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "maintenance": {
            "name": "数据维护",
            "description": "数据备份/清理/备份列表",
            "api_prefix": "/api/maintenance",
            "enabled": True,
            "required_permissions": ["admin:maintenance"],
            "allowed_roles": ["admin"],
            "rate_limit": 30,
            "rate_limit_window": 60,
        },
        "students": {
            "name": "学生管理",
            "description": "学生信息列表、搜索、筛选、分页",
            "api_prefix": "/api/students",
            "enabled": True,
            "required_permissions": ["student:view"],
            "allowed_roles": ["teacher", "director", "admin"],
            "rate_limit": 200,
            "rate_limit_window": 60,
        },
        "report_export": {
            "name": "报表导出",
            "description": "成绩单、统计报表、Excel/PDF 导出",
            "api_prefix": "/api/report",
            "enabled": True,
            "required_permissions": ["report:export"],
            "allowed_roles": ["teacher", "director", "admin"],
            "rate_limit": 20,
            "rate_limit_window": 60,
        },
        "admin_api": {
            "name": "管理接口",
            "description": "系统配置、用户管理、服务管理、备份恢复",
            "api_prefix": "/api/admin",
            "enabled": True,
            "required_permissions": ["system:admin"],
            "allowed_roles": ["admin"],
            "rate_limit": 50,
            "rate_limit_window": 60,
        },
        "column_config": {
            "name": "列配置管理",
            "description": "用户表格列配置持久化、多端同步",
            "api_prefix": "/api/meta/column-config",
            "enabled": True,
            "required_permissions": ["config:edit"],
            "allowed_roles": ["admin", "director", "teacher"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "audit": {
            "name": "审计日志",
            "description": "服务访问日志查询",
            "api_prefix": "/api/audit",
            "enabled": True,
            "required_permissions": ["system:audit"],
            "allowed_roles": ["admin", "director"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "dict": {
            "name": "字典管理",
            "description": "字典类型与数据 CRUD、表单下拉数据源",
            "api_prefix": "/api/dict",
            "enabled": True,
            "required_permissions": ["config:edit"],
            "allowed_roles": ["admin", "director"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "params": {
            "name": "参数管理",
            "description": "系统动态参数 CRUD",
            "api_prefix": "/api/params",
            "enabled": True,
            "required_permissions": ["config:edit"],
            "allowed_roles": ["admin", "director"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "notice": {
            "name": "通知公告",
            "description": "通知公告发布、阅读统计",
            "api_prefix": "/api/notice",
            "enabled": True,
            "required_permissions": ["config:view"],
            "allowed_roles": ["admin", "director", "teacher"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "login-logs": {
            "name": "登录日志",
            "description": "登录成功/失败日志查询",
            "api_prefix": "/api/login-logs",
            "enabled": True,
            "required_permissions": ["system:audit"],
            "allowed_roles": ["admin", "director"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "online-users": {
            "name": "在线用户",
            "description": "在线用户列表、强制下线",
            "api_prefix": "/api/online-users",
            "enabled": True,
            "required_permissions": ["system:audit"],
            "allowed_roles": ["admin", "director"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "parent_notify": {
            "name": "家长通知",
            "description": "成绩单推送、通知发送、回执追踪",
            "api_prefix": "/api/notify",
            "enabled": True,
            "required_permissions": ["parent:notify"],
            "allowed_roles": ["director", "admin"],
            "rate_limit": 50,
            "rate_limit_window": 60,
        },
        "stats": {
            "name": "统计数据",
            "description": "学期统计数据查询、缓存管理、重算触发",
            "api_prefix": "/api/stats",
            "enabled": True,
            "required_permissions": ["stats:view"],
            "allowed_roles": ["teacher", "director", "admin", "student", "parent"],
            "rate_limit": 200,
            "rate_limit_window": 60,
        },
        "teachers": {
            "name": "教师管理",
            "description": "教师档案、任课安排、排课",
            "api_prefix": "/api/teachers",
            "enabled": True,
            "required_permissions": ["teacher:view"],
            "allowed_roles": ["teacher", "director", "admin"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "users": {
            "name": "用户管理",
            "description": "用户列表、创建、角色分配、停启用、重置密码",
            "api_prefix": "/api/users",
            "enabled": True,
            "required_permissions": ["admin:users"],
            "allowed_roles": ["admin"],
            "rate_limit": 60,
            "rate_limit_window": 60,
        },
        "semester": {
            "name": "学期管理",
            "description": "学期列表、激活学期、学期切换",
            "api_prefix": "/api/semester",
            "enabled": True,
            "required_permissions": ["semester:view"],
            "allowed_roles": ["teacher", "director", "admin", "student", "parent"],
            "rate_limit": 200,
            "rate_limit_window": 60,
        },
        "license": {
            "name": "授权许可",
            "description": "安装授权码、许可状态查询",
            "api_prefix": "/api/license",
            "enabled": True,
            "required_permissions": [],
            "allowed_roles": ["admin"],
            "rate_limit": 50,
            "rate_limit_window": 60,
        },
        "monitor": {
            "name": "系统监控",
            "description": "服务监控、缓存统计",
            "api_prefix": "/api/monitor",
            "enabled": True,
            "required_permissions": ["system:admin"],
            "allowed_roles": ["admin", "director"],
            "rate_limit": 50,
            "rate_limit_window": 60,
        },
        "dept": {
            "name": "部门管理",
            "description": "部门树形 CRUD",
            "api_prefix": "/api/dept",
            "enabled": True,
            "required_permissions": ["config:edit"],
            "allowed_roles": ["admin", "director"],
            "rate_limit": 100,
            "rate_limit_window": 60,
        },
        "config": {
            "name": "UI 配置",
            "description": "UI 配置查询、热加载",
            "api_prefix": "/api/config",
            "enabled": True,
            "required_permissions": [],
            "allowed_roles": ["admin"],
            "rate_limit": 200,
            "rate_limit_window": 60,
        },
        "reports": {
            "name": "报表导出",
            "description": "报表生成、打印、打印机查询",
            "api_prefix": "/api/reports",
            "enabled": True,
            "required_permissions": [],
            "allowed_roles": ["teacher", "director", "admin"],
            "rate_limit": 50,
            "rate_limit_window": 60,
        },
    }

    def __init__(self):
        self._services = {}
        self._initialized = False

    def _init_default_services(self):
        """注册默认服务"""
        for code, config in self.DEFAULT_SERVICES.items():
            self.register(code, **config)

    def initialize_from_db(self, session: Session = None):
        """从数据库加载配置"""
        if self._initialized:
            return

        close_session = False
        if session is None:
            session = get_session()
            close_session = True

        try:
            configs = session.query(ServiceConfig).all()
            for cfg in configs:
                self._services[cfg.service_code] = {
                    "service_code": cfg.service_code,
                    "name": cfg.name,
                    "description": cfg.description,
                    "api_prefix": cfg.api_prefix,
                    "enabled": cfg.enabled,
                    "required_permissions": (
                        cfg.required_permissions.split(",") if cfg.required_permissions else []
                    ),
                    "allowed_roles": cfg.allowed_roles.split(",") if cfg.allowed_roles else [],
                    "rate_limit": cfg.rate_limit,
                    "rate_limit_window": cfg.rate_limit_window,
                }

            # 为数据库中没有的默认服务创建记录
            default_codes = set(self.DEFAULT_SERVICES.keys())
            existing_codes = set(cfg.service_code for cfg in configs)
            for code in default_codes - existing_codes:
                default = self._get_default_service(code)
                if default:
                    self._sync_to_db(session, code, default)

        except Exception as e:
            print(f"加载服务配置失败: {e}")
            # 回退到默认配置
            self._init_default_services()
        finally:
            if close_session:
                session.close()

        self._initialized = True

    def _get_default_service(self, code: str) -> dict | None:
        """获取默认服务配置（单一数据源 DEFAULT_SERVICES）"""
        return self.DEFAULT_SERVICES.get(code)

    def _sync_to_db(self, session: Session, code: str, config: dict):
        """同步配置到数据库（同时更新内存 _services，保证网关立即生效）"""
        # 同步更新内存（新增默认服务时网关可立即识别）
        self._services[code] = {
            "service_code": code,
            "name": config["name"],
            "description": config["description"],
            "api_prefix": config["api_prefix"],
            "enabled": config["enabled"],
            "required_permissions": config.get("required_permissions", []),
            "allowed_roles": config.get("allowed_roles", []),
            "rate_limit": config.get("rate_limit", 100),
            "rate_limit_window": config.get("rate_limit_window", 60),
        }
        try:
            cfg = ServiceConfig(
                service_code=code,
                name=config["name"],
                description=config["description"],
                api_prefix=config["api_prefix"],
                enabled=config["enabled"],
                required_permissions=",".join(config.get("required_permissions", [])),
                allowed_roles=",".join(config.get("allowed_roles", [])),
                rate_limit=config.get("rate_limit", 100),
                rate_limit_window=config.get("rate_limit_window", 60),
            )
            session.add(cfg)
            session.commit()
        except Exception as e:
            print(f"同步服务配置失败 {code}: {e}")
            session.rollback()

    def register(
        self,
        service_code: str,
        name: str,
        description: str,
        api_prefix: str,
        enabled: bool = True,
        required_permissions: list = None,
        allowed_roles: list[str] = None,
        rate_limit: int = 100,
        rate_limit_window: int = 60,
    ):
        """注册服务（内存 + 数据库）"""
        self._services[service_code] = {
            "service_code": service_code,
            "name": name,
            "description": description,
            "api_prefix": api_prefix,
            "enabled": enabled,
            "required_permissions": required_permissions or [],
            "allowed_roles": allowed_roles or [],
            "rate_limit": rate_limit,
            "rate_limit_window": rate_limit_window,
        }

        # 同步到数据库
        try:
            session = get_session()
            existing = session.query(ServiceConfig).filter_by(service_code=service_code).first()
            if existing:
                existing.name = name
                existing.description = description
                existing.api_prefix = api_prefix
                existing.enabled = enabled
                existing.required_permissions = ",".join(required_permissions or [])
                existing.allowed_roles = ",".join(allowed_roles or [])
                existing.rate_limit = rate_limit
                existing.rate_limit_window = rate_limit_window
            else:
                cfg = ServiceConfig(
                    service_code=service_code,
                    name=name,
                    description=description,
                    api_prefix=api_prefix,
                    enabled=enabled,
                    required_permissions=",".join(required_permissions or []),
                    allowed_roles=",".join(allowed_roles or []),
                    rate_limit=rate_limit,
                    rate_limit_window=rate_limit_window,
                )
                session.add(cfg)
            session.commit()
            session.close()
        except Exception as e:
            print(f"同步服务配置到数据库失败 {service_code}: {e}")

    def is_enabled(self, service_code: str) -> bool:
        """检查服务是否启用"""
        return self._services.get(service_code, {}).get("enabled", False)

    def get_config(self, service_code: str) -> dict | None:
        return self._services.get(service_code)

    def get_required_permissions(self, service_code: str) -> list:
        return self._services.get(service_code, {}).get("required_permissions", [])

    def get_allowed_roles(self, service_code: str) -> list[str]:
        return self._services.get(service_code, {}).get("allowed_roles", [])

    def get_rate_limit(self, service_code: str) -> int | None:
        return self._services.get(service_code, {}).get("rate_limit")

    def set_enabled(self, service_code: str, enabled: bool):
        """启用/禁用服务"""
        if service_code in self._services:
            self._services[service_code]["enabled"] = enabled
            # 同步到数据库
            try:
                session = get_session()
                cfg = session.query(ServiceConfig).filter_by(service_code=service_code).first()
                if cfg:
                    cfg.enabled = enabled
                    session.commit()
                session.close()
            except Exception as e:
                print(f"更新服务状态失败 {service_code}: {e}")

    def set_rate_limit(self, service_code: str, rate_limit: int, window: int = 60):
        """设置服务限流"""
        if service_code in self._services:
            self._services[service_code]["rate_limit"] = rate_limit
            self._services[service_code]["rate_limit_window"] = window
            # 同步到数据库
            try:
                session = get_session()
                cfg = session.query(ServiceConfig).filter_by(service_code=service_code).first()
                if cfg:
                    cfg.rate_limit = rate_limit
                    cfg.rate_limit_window = window
                    session.commit()
                session.close()
            except Exception as e:
                print(f"更新服务限流失败 {service_code}: {e}")

    def list_services(self) -> list[dict]:
        """列出所有服务"""
        return [
            {
                "service_code": code,
                "name": config["name"],
                "description": config["description"],
                "api_prefix": config["api_prefix"],
                "enabled": config["enabled"],
                "required_permissions": config.get("required_permissions", []),
                "allowed_roles": config.get("allowed_roles", []),
                "rate_limit": config.get("rate_limit"),
                "rate_limit_window": config.get("rate_limit_window", 60),
            }
            for code, config in self._services.items()
        ]


# 全局服务注册表实例
service_registry = ServiceRegistry()


def register_services(app):
    """向 FastAPI 注册服务注册表"""
    # 初始化服务注册表（从数据库加载）
    service_registry.initialize_from_db()
    app.state.service_registry = service_registry
