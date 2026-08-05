"""
M5-F4 优雅停机集成测试

覆盖：
- ServerThread 启动后 uvicorn 运行
- stop() 后线程停止（无残留线程/进程）
- PID 文件清理
"""

import sys
import tempfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PyQt5.QtCore import QCoreApplication

from edu_system.gui.server_thread import ServerThread

# 必须显式创建 QCoreApplication（无 GUI 环境）
_app = QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture()
def server_thread():
    st = ServerThread(port=0)  # 自动选端口
    # 用临时 PID 路径避免污染真实 data/
    st._pid_file = Path(tempfile.mkdtemp()) / "server.pid"
    yield st
    if st.isRunning():
        st.stop()


class TestGracefulShutdown:
    def test_start_and_stop(self, server_thread):
        """启动 → 停止：线程结束 + PID 文件清理（F4 无残留进程）"""
        server_thread.start()
        # 等待启动（uvicorn 就绪）
        deadline = time.time() + 15
        while time.time() < deadline:
            if server_thread._server is not None:
                break
            time.sleep(0.2)
        assert server_thread._server is not None, "服务器未启动"

        # 停止
        ok = server_thread.stop(timeout=10)
        assert ok, "stop() 应返回 True（线程已停止）"
        assert not server_thread.isRunning(), "线程应已退出"

        # PID 文件清理
        assert not server_thread._pid_file.exists(), "PID 文件应被清理"

    def test_stop_when_not_running(self, server_thread):
        """未启动时 stop() 幂等（不崩溃）"""
        ok = server_thread.stop(timeout=5)
        assert ok is True or server_thread.isRunning() is False

    def test_double_stop(self, server_thread):
        """连续两次 stop() 幂等"""
        server_thread.start()
        deadline = time.time() + 15
        while time.time() < deadline:
            if server_thread._server is not None:
                break
            time.sleep(0.2)

        first = server_thread.stop(timeout=10)
        second = server_thread.stop(timeout=5)
        assert first is True
        assert second is True
