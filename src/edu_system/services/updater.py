"""
自动更新服务 (M6 Sprint7 - Windows 自动更新)

功能：
1. 启动时检查 GitHub Release 是否有新版本
2. 下载新版本安装包到临时目录
3. 静默安装 / 替换当前可执行文件
4. 重启应用完成更新
"""

import json
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from urllib.request import Request, urlopen

from PyQt5.QtCore import QObject, pyqtSignal


class Updater(QObject):
    """自动更新检查与安装"""

    # 信号
    check_finished = pyqtSignal(bool, str, str)  # success, version, message
    download_progress = pyqtSignal(int)  # 0-100
    download_finished = pyqtSignal(bool, str)  # success, local_path
    update_ready = pyqtSignal()  # 更新包就绪，可重启

    def __init__(
        self, current_version: str, repo_owner: str = "laozhudu", repo_name: str = "edu-management"
    ):
        super().__init__()
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_api = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self._cancel = False

    def check_for_update(self) -> None:
        """异步检查更新"""
        thread = threading.Thread(target=self._check_update_worker, daemon=True)
        thread.start()

    def _check_update_worker(self):
        try:
            url = f"{self.github_api}/releases/latest"
            req = Request(url, headers={"User-Agent": "edu-management-updater"})
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            latest_version = data.get("tag_name", "").lstrip("v")
            if not latest_version:
                self.check_finished.emit(False, "", "无法解析最新版本")
                return

            # 版本比较
            if self._is_newer(latest_version, self.current_version):
                # 找到 .exe 资源
                assets = data.get("assets", [])
                exe_asset = next((a for a in assets if a["name"].endswith(".exe")), None)
                if exe_asset:
                    self.check_finished.emit(
                        True,
                        latest_version,
                        f"发现新版本 v{latest_version}，点击下载更新",
                        exe_asset["browser_download_url"],
                        exe_asset.get("size", 0),
                    )
                else:
                    self.check_finished.emit(False, latest_version, "未找到 Windows 安装包")
            else:
                self.check_finished.emit(False, latest_version, "当前已是最新版本")

        except Exception as e:
            self.check_finished.emit(False, "", f"检查更新失败: {e}")

    def _is_newer(self, latest: str, current: str) -> bool:
        """语义化版本比较"""
        try:
            latest_parts = [int(x) for x in latest.split(".")]
            current_parts = [int(x) for x in current.split(".")]
            # 补齐长度
            max_len = max(len(latest_parts), len(current_parts))
            latest_parts += [0] * (max_len - len(latest_parts))
            current_parts += [0] * (max_len - len(current_parts))
            return latest_parts > current_parts
        except:
            return latest > current  # 兜底字符串比较

    def download_update(
        self, download_url: str, progress_cb: Callable[[int], None] | None = None
    ) -> str:
        """下载更新包，返回本地路径"""
        self._cancel = False
        temp_dir = Path(tempfile.gettempdir()) / "edu_management_update"
        temp_dir.mkdir(parents=True, exist_ok=True)
        local_path = temp_dir / "edu-management-new.exe"

        try:
            req = Request(download_url, headers={"User-Agent": "edu-management-updater"})
            with urlopen(req, timeout=30) as response:
                total = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 8192

                with open(local_path, "wb") as f:
                    while True:
                        if self._cancel:
                            raise InterruptedError("用户取消下载")
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0 and progress_cb:
                            progress_cb(int(downloaded * 100 / total))

            # 验证文件完整性（可选：SHA256）
            return str(local_path)
        except Exception as e:
            if local_path.exists():
                local_path.unlink()
            raise

    def cancel_download(self):
        self._cancel = True

    def install_update(self, exe_path: str) -> bool:
        """安装更新：替换当前 exe 并重启（Windows）"""
        try:
            current_exe = Path(sys.executable)
            if not current_exe.exists():
                return False

            # 创建批处理脚本：等待主进程退出 -> 替换文件 -> 重启
            bat_path = Path(tempfile.gettempdir()) / "edu_management_update.bat"
            with open(bat_path, "w", encoding="gbk") as f:
                f.write(f"""@echo off
chcp 65001 >nul
echo 等待主程序退出...
timeout /t 2 /nobreak >nul
echo 正在替换程序...
move /y "{exe_path}" "{current_exe}"
if errorlevel 1 (
    echo 替换失败
    pause
    exit /b 1
)
echo 启动新版本...
start "" "{current_exe}"
del "%~f0"
""")

            # 启动批处理并退出当前进程
            subprocess.Popen(
                ["cmd", "/c", str(bat_path)],
                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010),
            )
            return True
        except Exception as e:
            print(f"安装更新失败: {e}")
            return False

    def verify_signature(self, exe_path: str) -> bool:
        """验证 Windows 代码签名（可选）"""
        try:
            result = subprocess.run(
                ["signtool", "verify", "/pa", exe_path], capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except:
            return False


class UpdateManager:
    """高层更新管理器：集成到主程序"""

    def __init__(self, current_version: str):
        self.updater = Updater(current_version)
        self._auto_check_timer = None

    def start_auto_check(self, interval_hours: int = 24):
        """启动定时自动检查"""
        from PyQt5.QtCore import QTimer

        self._auto_check_timer = QTimer()
        self._auto_check_timer.timeout.connect(self.updater.check_for_update)
        self._auto_check_timer.start(interval_hours * 3600 * 1000)
        # 启动时立即检查一次
        self.updater.check_for_update()

    def on_update_available(self, callback: Callable[[str, str], None]):
        """绑定更新可用回调"""
        self.updater.check_finished.connect(
            lambda success, version, msg, *args: callback(version, msg) if success else None
        )


# 便捷函数
def get_current_version() -> str:
    """从 pyproject.toml 或 __init__.py 获取版本"""
    try:
        import toml

        with open("pyproject.toml") as f:
            data = toml.load(f)
            return data.get("project", {}).get("version", "0.0.0")
    except:
        try:
            from edu_system import __version__

            return __version__
        except:
            return "0.0.0"


if __name__ == "__main__":
    # 简单测试
    v = get_current_version()
    print(f"当前版本: {v}")

    updater = Updater(v)
    updater.check_finished.connect(lambda s, v, m, *args: print(f"检查结果: {s} {v} {m}"))
    updater.check_for_update()

    # 保持主线程运行以接收回调
    import time

    time.sleep(5)
