"""
统计手动触发契约测试（M5-B4）

覆盖：
- 全量重算手动触发（admin 权限）
- 增量重算手动触发（admin 权限）
- 幂等：连续触发返回 200 不报错，worker 状态可查
- 权限：无 admin 权限返回 403
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

from edu_system.api.main import create_app


class TestStatsRecomputeContract:
    """统计重算触发接口契约测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """登录获取 admin token"""
        app = create_app()
        client = TestClient(app)
        self.client = client

        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        self.access_token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

        # 动态创建 teacher 角色用户（无 system:admin 权限），验证权限拒绝
        from edu_system.core.auth import get_password_hash
        from edu_system.database import get_session
        from edu_system.models import Role, User

        self._db = get_session()
        role = self._db.query(Role).filter_by(name="teacher").first()
        if not role:
            role = Role(name="teacher", description="教师", permissions="student:view,exam:view")
            self._db.add(role)
            self._db.flush()
        if not self._db.query(User).filter_by(username="teacher").first():
            self._db.add(
                User(
                    username="teacher",
                    password_hash=get_password_hash("teacher123"),
                    role=role,
                    is_active=True,
                )
            )
            self._db.commit()
        self._teacher_headers = {"Authorization": f"Bearer {self._login_teacher_token()}"}

    def _login_teacher_token(self):
        resp = self.client.post(
            "/api/auth/login",
            json={"username": "teacher", "password": "teacher123"},
        )
        assert resp.status_code == 200
        return resp.json()["access_token"]

    @pytest.fixture(autouse=True)
    def _cleanup(self, request):
        yield
        # 清理测试创建的 teacher 用户/角色
        if hasattr(self, "_db"):
            from edu_system.models import User

            self._db.query(User).filter_by(username="teacher").delete()
            self._db.commit()
            self._db.close()

        # 等待后台统计 worker 线程结束，避免遗留线程持有 DB 锁污染后续测试
        from edu_system.api.routes.stats import get_worker

        worker = get_worker()
        for _ in range(50):
            if worker._thread is None or not worker._thread.isRunning():
                break
            import time

            time.sleep(0.1)
        if worker._thread is not None and worker._thread.isRunning():
            worker.cancel()

    def test_full_recompute_trigger(self):
        """全量重算手动触发：返回任务启动确认"""
        resp = self.client.post("/api/stats/recompute/full", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "全量重算已在后台启动"
        assert data["task"] == "full_recompute"

    def test_incremental_recompute_trigger(self):
        """增量重算手动触发：返回脏实体计数"""
        dirty = [
            {"entity_type": "student", "entity_id": 1, "exam_id": None},
            {"entity_type": "class", "entity_id": 2, "exam_id": None},
        ]
        resp = self.client.post(
            "/api/stats/recompute/incremental",
            json=dirty,
            headers=self.headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "增量重算已启动"
        assert data["count"] == 2

    def test_recompute_trigger_idempotent(self):
        """幂等：连续两次触发全量重算均返回 200，不重复报错"""
        r1 = self.client.post("/api/stats/recompute/full", headers=self.headers)
        r2 = self.client.post("/api/stats/recompute/full", headers=self.headers)
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_recompute_requires_admin(self):
        """权限：普通用户（teacher）触发返回 403"""
        r = self.client.post("/api/stats/recompute/full", headers=self._teacher_headers)
        assert r.status_code == 403

    def test_worker_status_query(self):
        """worker 状态接口可查询（不报错）"""
        resp = self.client.get("/api/stats/recompute/worker/status", headers=self.headers)
        assert resp.status_code == 200
