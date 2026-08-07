"""
PyQt5 嵌入式 FastAPI 服务器线程
使用 QThread 运行 uvicorn，支持优雅启动/停止、端口冲突重试、PID 文件
"""

import os
import socket
import sys
import time

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from edu_system.config import PROJECT_ROOT


class ServerSignals(QObject):
    """服务器信号"""

    started = pyqtSignal(str, int)  # host, port
    stopped = pyqtSignal()
    error = pyqtSignal(str)
    log = pyqtSignal(str)


class ServerThread(QThread):
    """嵌入式 uvicorn 服务器线程"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        app_module: str = "edu_system.api.main:app",
        max_retries: int = 5,
        retry_interval: int = 2,
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.app_module = app_module
        self.max_retries = max_retries
        self.retry_interval = retry_interval

        self.signals = ServerSignals()
        self._server = None
        self._should_stop = False
        self._actual_port = port
        self._pid_file = PROJECT_ROOT / "data" / "uvicorn.pid"
        self._pid_file.parent.mkdir(parents=True, exist_ok=True)

    def run(self):
        """线程主函数"""
        import asyncio

        import uvicorn

        # 设置事件循环策略
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        # 尝试绑定端口（含重试）
        actual_port = self._find_available_port()
        if actual_port is None:
            self.signals.error.emit(
                f"无法找到可用端口（尝试 {self.port} - {self.port + self.max_retries - 1}）"
            )
            return

        self._actual_port = actual_port

        # 写入 PID 文件
        try:
            self._pid_file.write_text(str(self._get_pid()))
        except Exception as e:
            self.signals.log.emit(f"写入 PID 文件失败: {e}")

        # 创建 uvicorn 配置
        config = uvicorn.Config(
            "edu_system.api.main:app",
            host=self.host,
            port=actual_port,
            log_level="warning",
            access_log=False,
            lifespan="on",
        )

        self._server = uvicorn.Server(config)

        # 发射启动信号
        self.signals.started.emit(self.host, actual_port)
        self.signals.log.emit(f"FastAPI 服务已启动: http://{self.host}:{actual_port}")

        # 运行服务器（阻塞）
        try:
            self._server.run()
        except Exception as e:
            self.signals.error.emit(f"服务器运行异常: {e}")
        finally:
            self._cleanup()

    def _find_available_port(self) -> int | None:
        """寻找可用端口"""
        # 如果目标端口被本项目自己的遗留进程占用，先尝试清理
        if not self._is_port_available(self.port):
            self._kill_stale_process(self.port)
            # 清理后等待端口释放（进程被杀后 socket 需短暂释放）
            for _ in range(self.max_retries):
                if self._is_port_available(self.port):
                    return self.port
                time.sleep(self.retry_interval)
            self.signals.log.emit(f"端口 {self.port} 被占用，尝试下一个...")
        # 正常占用的话按重试顺序找可用端口
        for i in range(self.max_retries):
            port = self.port + i
            if self._is_port_available(port):
                return port
            self.signals.log.emit(f"端口 {port} 被占用，尝试下一个...")
            time.sleep(self.retry_interval)
        return None

    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.host, port))
                return True
        except OSError:
            return False

    def _kill_stale_process(self, port: int) -> None:
        """清理占用目标端口的本项目遗留 uvicorn 进程

        场景：桌面端异常退出后，独立的 uvicorn 进程可能残留占用 8080，
        导致"启动服务"实际跳到其他端口、用户以为没启动。
        仅清理命令行含 edu_system.api.main 的本项目进程，绝不误杀其他服务。
        """
        import subprocess

        if sys.platform == "win32":
            # Windows: netstat 找 PID
            try:
                out = subprocess.check_output(
                    ["netstat", "-ano"], text=True, timeout=5
                )
                for line in out.splitlines():
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        pid = parts[-1]
                        try:
                            subprocess.run(
                                ["taskkill", "/F", "/PID", pid],
                                check=False, capture_output=True, timeout=5,
                            )
                            self.signals.log.emit(f"已清理遗留进程 PID {pid}（端口 {port}）")
                        except Exception:
                            pass
            except Exception:
                pass
            return

        # Linux: ss/lsof 找占用进程，校验命令行后再杀
        try:
            out = subprocess.check_output(
                ["ss", "-tlnp"], text=True, timeout=5
            )
            for line in out.splitlines():
                if f":{port}" not in line:
                    continue
                if "users:" not in line:
                    continue
                # 提取 pid=xxx
                import re

                m = re.search(r"pid=(\d+)", line)
                if not m:
                    continue
                pid = m.group(1)
                # 校验命令行确实包含本项目 uvicorn
                try:
                    cmdline = subprocess.check_output(
                        ["cat", f"/proc/{pid}/cmdline"], text=True, timeout=3
                    )
                except Exception:
                    continue
                if "edu_system.api.main" not in cmdline:
                    continue  # 非本项目进程，不动
                os.kill(int(pid), 9)
                self.signals.log.emit(f"已清理遗留 uvicorn 进程 PID {pid}（端口 {port}）")
        except Exception:
            pass

    def _get_pid(self) -> int:
        """获取当前进程 PID"""
        import os

        return os.getpid()

    def stop(self, timeout: int = 10) -> bool:
        """停止服务器"""
        self._should_stop = True
        self.signals.log.emit("正在停止服务器...")

        if self._server:
            self._server.should_exit = True

        # 等待线程结束
        self.wait(timeout * 1000)

        if self.isRunning():
            self.terminate()
            self.wait(3000)

        self._cleanup()
        return not self.isRunning()

    def _cleanup(self):
        """清理资源"""
        self._cleanup_pid_file()
        self.signals.stopped.emit()
        self.signals.log.emit("服务器已停止")

    def _cleanup_pid_file(self):
        """清理 PID 文件"""
        try:
            if self._pid_file.exists():
                self._pid_file.unlink()
        except Exception:
            pass

    def get_status(self) -> dict:
        """获取服务器状态"""
        return {
            "running": self.isRunning(),
            "host": self.host,
            "port": self._actual_port,
            "pid": self._get_pid() if self.isRunning() else None,
        }

    def get_qr_code_data(self) -> str:
        """获取二维码数据（用于显示局域网地址）"""
        # 获取本机局域网 IP
        local_ip = self._get_local_ip()
        return f"http://{local_ip}:{self._actual_port}"

    def _get_local_ip(self) -> str:
        """获取本机局域网 IP"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"


# 便捷函数
def create_server_thread(
    host: str = "0.0.0.0", port: int = 8080, app_module: str = "edu_system.api.main:app"
) -> ServerThread:
    """创建服务器线程"""
    return ServerThread(host=host, port=port, app_module=app_module)
