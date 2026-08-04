"""
崩溃防护 — 全局异常捕获 + 启动自检（根治 GUI 打不开）

三层防护：
1. sys.excepthook：未捕获异常 → 写崩溃日志 + 弹窗（不再静默退出）
2. Qt 消息处理：qInstallMessageHandler 捕获 Qt 内部错误（C++ 对象删除等）
3. 启动自检：config 可解析 / registry 完整 / DB 可连 → 失败给出明确指引

日志位置：~/.edu_system/crash.log（追加式，含时间戳/异常栈）
"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

_LOG_DIR = Path.home() / ".edu_system"
_LOG_FILE = _LOG_DIR / "crash.log"


def ensure_log_dir() -> Path:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _LOG_FILE


def write_crash_log(source: str, exc_info=None, message: str = "") -> str:
    """写崩溃日志，返回日志文件路径"""
    log_file = ensure_log_dir()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'=' * 60}\n[{ts}] 来源: {source}\n")
        if message:
            f.write(f"信息: {message}\n")
        if exc_info:
            f.write("".join(traceback.format_exception(*exc_info)))
        else:
            f.write(traceback.format_exc())
    return str(log_file)


def install_global_excepthook() -> None:
    """安装全局异常钩子：任何未捕获异常 → 日志 + 弹窗（不静默）"""
    sys.excepthook = _global_excepthook


def _global_excepthook(exc_type, exc_value, exc_tb):
    # 忽略 KeyboardInterrupt / SystemExit
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    log_file = write_crash_log(
        "sys.excepthook", exc_info=(exc_type, exc_value, exc_tb)
    )
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance()
        if app is not None:
            QMessageBox.critical(
                None,
                "程序异常",
                f"程序遇到未处理的异常，已记录到:\n{log_file}\n\n"
                f"错误类型: {exc_type.__name__}\n"
                f"错误信息: {exc_value}\n\n"
                "请将日志文件发送给开发人员。",
            )
    except Exception:
        pass  # 弹窗失败也不影响日志已写入


def install_qt_message_handler() -> None:
    """安装 Qt 消息处理器：捕获 Qt 内部错误（C++ 对象已删除等）写入日志"""
    try:
        from PyQt5.QtCore import qInstallMessageHandler

        def handler(mode, context, message):
            # 只记录错误级（QtCriticalMsg=3, QtFatalMsg=4）
            if mode >= 3:
                write_crash_log("Qt 消息", message=message)

        qInstallMessageHandler(handler)
    except Exception:
        pass


# ═══════════════════════════════════
# 启动自检
# ═══════════════════════════════════

def preflight_checks() -> list[str]:
    """启动前自检，返回问题列表（空 = 全部通过）

    检查项：
    1. ui_config.json 可解析（含必需键）
    2. 视图注册表完整（config 的 view 都能在 registry 找到）
    3. 数据库可连接
    """
    problems: list[str] = []

    # 1. UI 配置
    cfg = None
    try:
        from edu_system.config.ui_config import load_config

        cfg = load_config()
        if not cfg.domains_parsed:
            problems.append("ui_config.json 未解析出任何工作台（配置为空或格式错误）")
    except Exception as e:
        problems.append(f"ui_config.json 解析失败: {e}")

    # 2. 视图注册表
    try:
        from edu_system.gui.views.registry import VIEW_REGISTRY

        if cfg is not None:
            for domain in cfg.domains_parsed:
                for tab in domain.get("tabs", []):
                    view_id = tab.view if hasattr(tab, "view") else tab["view"]
                    if view_id not in VIEW_REGISTRY:
                        problems.append(
                            f"视图未注册: {view_id}（ui_config 与 registry 不一致）"
                        )
    except Exception as e:
        problems.append(f"视图注册表检查失败: {e}")

    # 3. 数据库
    try:
        from sqlalchemy import text

        from edu_system.database import get_session

        session = get_session()
        session.execute(text("SELECT 1"))
        session.close()
    except Exception as e:
        problems.append(f"数据库连接失败: {e}")

    return problems


def run_preflight() -> None:
    """运行自检；有问题则弹窗明示（GUI 可用时）或打印（无 GUI）"""
    problems = preflight_checks()
    if not problems:
        return
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance()
        if app is not None:
            QMessageBox.critical(
                None,
                "启动自检未通过",
                "以下问题将导致界面无法正常打开:\n\n" + "\n".join(f"• {p}" for p in problems),
            )
            return
    except Exception:
        pass
    print("[启动自检] 未通过:", *problems, sep="\n  - ")
