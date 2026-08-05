"""
考勤实时推送 Notifier 单测（M5-E2）

覆盖：
- 推送事件入队（离线补偿：无论是否在线都记录 pending）
- 重连补发：register 时 flush pending 队列
- 连接注销
- 单例复用
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from edu_system.services.attendance_notifier import (
    AttendanceNotifier,
    get_notifier,
    reset_notifier,
)


class FakeWS:
    """模拟 WebSocket：记录收到的消息，可模拟发送失败"""

    def __init__(self, fail_send=False):
        self.received = []
        self.fail_send = fail_send

    async def send_json(self, data):
        if self.fail_send:
            raise ConnectionError("模拟断线")
        self.received.append(data)

    async def close(self):
        pass


@pytest.fixture(autouse=True)
def _clean_notifier():
    reset_notifier()
    yield
    reset_notifier()


@pytest.mark.asyncio
class TestAttendanceNotifier:
    async def test_notify_records_pending(self):
        """推送事件进入 pending 队列（离线补偿基础）"""
        n = AttendanceNotifier()
        await n.notify({"type": "attendance.checkin", "data": {"student_id": 1}})
        assert n.pending_count() == 1

    async def test_register_flushes_pending(self):
        """重连时补发离线期间事件"""
        n = AttendanceNotifier()
        await n.notify({"type": "attendance.checkin", "data": {"id": 1}})
        await n.notify({"type": "attendance.checkin", "data": {"id": 2}})
        assert n.pending_count() == 2

        ws = FakeWS()
        await n.register(ws)
        # 补发全部 pending
        assert len(ws.received) == 2
        assert ws.received[0]["data"]["id"] == 1
        assert ws.received[1]["data"]["id"] == 2

    async def test_notify_to_online_connection(self):
        """在线连接实时收到推送"""
        n = AttendanceNotifier()
        ws = FakeWS()
        await n.register(ws)
        await n.notify({"type": "attendance.checkin", "data": {"id": 42}})
        assert len(ws.received) == 1
        assert ws.received[0]["data"]["id"] == 42

    async def test_dead_connection_cleaned(self):
        """发送失败的连接被清理（不会影响后续推送）"""
        n = AttendanceNotifier()
        dead_ws = FakeWS(fail_send=True)
        live_ws = FakeWS()
        await n.register(dead_ws)
        await n.register(live_ws)
        await n.notify({"type": "attendance.checkin", "data": {"id": 7}})
        # 死连接被清理，活连接收到
        assert len(live_ws.received) == 1
        assert len(n._connections) == 1

    async def test_unregister(self):
        """注销后不再收到推送"""
        n = AttendanceNotifier()
        ws = FakeWS()
        await n.register(ws)
        await n.unregister(ws)
        assert len(n._connections) == 0

    async def test_singleton(self):
        """get_notifier 返回同一实例"""
        a = get_notifier()
        b = get_notifier()
        assert a is b

    async def test_pending_cap(self):
        """pending 队列有上限，防内存膨胀"""
        n = AttendanceNotifier()
        for i in range(600):
            await n.notify({"type": "x", "data": {"i": i}})
        assert n.pending_count() <= 500
