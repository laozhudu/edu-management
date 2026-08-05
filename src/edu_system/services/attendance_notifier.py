"""
考勤实时推送 + 离线队列（M5-E2）

- AttendanceNotifier: WebSocket 连接管理器
  - register/unregister: 客户端订阅
  - notify: 考勤事件推送给所有订阅者
  - 连接断开时事件进入 pending 队列，重连后 flush（离线补偿）
- 单例：app 启动时创建，注入 attendance 路由

设计：单进程内存实现（桌面内嵌场景足够）；
多进程部署需换 Redis pub/sub（预留接口注释）。
"""

import asyncio
import logging
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

_MAX_PENDING = 500  # 离线队列上限，防内存膨胀


class AttendanceNotifier:
    """考勤事件推送器（WebSocket + 离线队列）"""

    def __init__(self):
        self._connections: set[Any] = set()  # WebSocket 连接集合
        self._pending: deque[dict] = deque(maxlen=_MAX_PENDING)
        self._lock = asyncio.Lock()

    async def register(self, ws) -> None:
        """注册订阅连接"""
        async with self._lock:
            self._connections.add(ws)
        # 重连后补发离线期间的事件
        pending = list(self._pending)
        for event in pending:
            try:
                await ws.send_json(event)
            except Exception:
                break

    async def unregister(self, ws) -> None:
        """注销订阅连接"""
        async with self._lock:
            self._connections.discard(ws)

    async def notify(self, event: dict) -> None:
        """推送考勤事件给所有在线订阅者

        推送失败（连接断开）的事件进入 pending 队列，
        客户端重连时由 register() 补发（离线补偿）。
        """
        async with self._lock:
            connections = list(self._connections)
        dead = []
        for ws in connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        # 记录离线事件（有死连接或无人订阅时都入队，供重连补发）
        self._pending.append(event)
        # 清理断开连接
        for ws in dead:
            await self.unregister(ws)

    def pending_count(self) -> int:
        """待补发事件数（测试/诊断用）"""
        return len(self._pending)


# 全局单例（app 启动时复用）
_notifier: AttendanceNotifier | None = None


def get_notifier() -> AttendanceNotifier:
    """获取考勤推送单例"""
    global _notifier  # noqa: PLW0603
    if _notifier is None:
        _notifier = AttendanceNotifier()
    return _notifier


def reset_notifier() -> None:
    """重置单例（测试用）"""
    global _notifier  # noqa: PLW0603
    _notifier = None
