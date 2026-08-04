"""
结构化 JSON 日志
使用 structlog + orjson，字段：timestamp level service user_id semester_id trace_id
"""

import logging
from pathlib import Path
from typing import Any

try:
    import orjson
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

from edu_system.config import PROJECT_ROOT


def setup_structured_logging(
    log_level: str = "INFO",
    log_dir: str = None,
    service_name: str = "edu_system",
    json_output: bool = True,
) -> logging.Logger:
    """
    配置结构化日志

    日志字段：
    - timestamp: ISO8601 时间戳
    - level: 日志级别
    - service: 服务名
    - user_id: 用户ID（如有）
    - semester_id: 学期ID（如有）
    - trace_id: 链路追踪ID（如有）
    - logger: 日志器名
    - message: 日志消息
    - extra: 附加字段
    """

    if log_dir is None:
        log_dir = PROJECT_ROOT / "logs"
    else:
        log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 标准库 logging 配置
    log_file = log_dir / f"{service_name}.log"

    # 清理现有 handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # 设置级别
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(level)

    if STRUCTLOG_AVAILABLE and json_output:
        # 使用 structlog
        return _setup_structlog(root_logger, log_file, service_name, level)
    else:
        # 回退到标准 logging
        return _setup_standard_logging(root_logger, log_file, level)


def _setup_structlog(root_logger, log_file: Path, service_name: str, level: int) -> logging.Logger:
    """配置 structlog"""

    import structlog

    # 文件处理器（JSON 格式）
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)

    # 控制台处理器（彩色输出）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # 添加到 root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(serializer=orjson.dumps),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 返回 structlog logger
    return structlog.get_logger(service_name)


def _setup_standard_logging(root_logger, log_file: Path, level: int) -> logging.Logger:
    """标准 logging 回退配置"""

    import json
    from datetime import datetime

    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_obj = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "service": getattr(record, "service", "edu_system"),
                "logger": record.name,
                "message": record.getMessage(),
                "user_id": getattr(record, "user_id", None),
                "semester_id": getattr(record, "semester_id", None),
                "trace_id": getattr(record, "trace_id", None),
            }
            if record.exc_info:
                log_obj["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_obj, ensure_ascii=False)

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(JSONFormatter())

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger


# ===== 便捷函数 =====


def get_logger(name: str = None):
    """获取结构化 logger"""
    if STRUCTLOG_AVAILABLE:
        import structlog

        return structlog.get_logger(name or "edu_system")
    else:
        return logging.getLogger(name or "edu_system")


def log_with_context(logger, level: str, message: str, **context):
    """带上下文的日志记录"""
    extra = {
        "user_id": context.pop("user_id", None),
        "semester_id": context.pop("semester_id", None),
        "trace_id": context.pop("trace_id", None),
    }
    extra.update(context)

    getattr(logger, level.lower())(message, **extra)


# ===== 中间件集成 =====


class LoggingMiddleware:
    """请求日志中间件"""

    def __init__(self, app, logger=None):
        self.app = app
        self.logger = logger or get_logger("http")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time

        start_time = time.time()

        # 提取请求信息
        method = scope.get("method", "")
        path = scope.get("path", "")
        query_string = scope.get("query_string", b"").decode()
        client = scope.get("client", ["unknown", 0])
        client_ip = client[0] if client else "unknown"

        # 生成 trace_id
        import uuid

        trace_id = str(uuid.uuid4())[:8]

        # 记录请求开始
        self._log_request_start(method, path, query_string, client_ip, trace_id)

        # 包装 send 以捕获响应
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            self._log_request_error(method, path, str(e), trace_id)
            raise
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_request_complete(method, path, status_code, duration_ms, trace_id)

    def _log_request_start(self, method: str, path: str, query: str, client_ip: str, trace_id: str):
        """记录请求开始"""
        if STRUCTLOG_AVAILABLE:
            self.logger.info(
                "http_request_started",
                method=method,
                path=path,
                query=query,
                client_ip=client_ip,
                trace_id=trace_id,
            )
        else:
            self.logger.info(
                f"HTTP request started: {method} {path} from {client_ip} (trace={trace_id})"
            )

    def _log_request_error(self, method: str, path: str, error: str, trace_id: str):
        """记录请求错误"""
        if STRUCTLOG_AVAILABLE:
            self.logger.error(
                "http_request_failed", method=method, path=path, error=error, trace_id=trace_id
            )
        else:
            self.logger.error(f"HTTP request failed: {method} {path} - {error} (trace={trace_id})")

    def _log_request_complete(
        self, method: str, path: str, status_code: int, duration_ms: int, trace_id: str
    ):
        """记录请求完成"""
        if STRUCTLOG_AVAILABLE:
            self.logger.info(
                "http_request_completed",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                trace_id=trace_id,
            )
        else:
            self.logger.info(
                f"HTTP request completed: {method} {path} -> {status_code} in {duration_ms}ms (trace={trace_id})"
            )


# ===== 初始化函数 =====


def init_logging(config: dict[str, Any] = None):
    """初始化日志系统（应用启动时调用一次）"""
    config = config or {}

    logger = setup_structured_logging(
        log_level=config.get("level", "INFO"),
        log_dir=config.get("log_dir"),
        service_name=config.get("service", "edu_system"),
        json_output=config.get("json", True),
    )

    # 设置第三方库日志级别
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)

    return logger
