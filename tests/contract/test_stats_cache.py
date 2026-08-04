"""
统计缓存 API + 304 契约测试（M5-B5）

覆盖：
- HTTP 304：前端带 version 且一致时返回 304（ETag）
- 无实时聚合：查询返回的是缓存值（带 version/computed_at），非实时计算
- 版本变更后：旧 version 不再 304，返回 200 全量数据
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


class TestStatsCacheContract:
    """统计缓存 API 契约测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """登录获取 admin token + 初始化默认数据 + 查询首期得到 version"""
        # 初始化默认数据（semester/grade/subject 等），供统计查询
        from edu_system.database import init_db_with_defaults

        init_db_with_defaults()

        app = create_app()
        client = TestClient(app)
        self.client = client

        resp = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 200
        self.headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

        # 同步全量重算填充统计缓存（供"无实时聚合"验证）
        # 异步 QThread worker 在 TestClient 无 Qt 事件循环下不可靠，故用同步纯函数
        from edu_system.database import get_session, set_active_semester
        from edu_system.services.statistics import run_full_recompute

        set_active_semester(1)
        db = get_session()
        run_full_recompute(db)
        db.close()
        self.semester_id = 1

    def test_first_query_has_version(self):
        """首次查询返回缓存数据（含 version + computed_at），非实时聚合"""
        resp = self.client.get(
            f"/api/stats/semester/{self.semester_id}?entity_type=school&entity_id=0",
            headers=self.headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data
        assert "version" in data
        # 无实时聚合：数据带 version + computed_at（来自预计算缓存而非实时算）
        assert data["metrics"], "统计缓存应为空后由同步重算填充"
        for key, val in data["metrics"].items():
            assert "version" in val
            assert val["computed_at"] is not None, f"缓存 {key} 缺 computed_at"

    def test_304_when_version_matches(self):
        """前端带一致 version → 返回 304 + ETag"""
        # 先取当前 version
        resp = self.client.get(
            f"/api/stats/semester/{self.semester_id}?entity_type=school&entity_id=0",
            headers=self.headers,
        )
        version = resp.json()["version"]

        resp2 = self.client.get(
            f"/api/stats/semester/{self.semester_id}"
            f"?entity_type=school&entity_id=0&version={version}",
            headers=self.headers,
        )
        assert resp2.status_code == 304
        assert "etag" in resp2.headers
        assert f'"{version}"' in resp2.headers["etag"]

    def test_new_version_returns_200(self):
        """版本不一致（前端带非当前 version）→ 不 304，返回 200 全量数据"""
        # 取当前 version
        resp = self.client.get(
            f"/api/stats/semester/{self.semester_id}?entity_type=school&entity_id=0",
            headers=self.headers,
        )
        assert resp.status_code == 200
        current = resp.json()["version"]

        # 传一个不同的 version（当前+99），应不匹配当前版本 → 200 而非 304
        resp2 = self.client.get(
            f"/api/stats/semester/{self.semester_id}"
            f"?entity_type=school&entity_id=0&version={current + 99}",
            headers=self.headers,
        )
        assert resp2.status_code == 200
        assert "metrics" in resp2.json()


class TestCacheVersionEndpoint:
    """缓存版本接口"""

    @pytest.fixture(autouse=True)
    def setup(self):
        app = create_app()
        client = TestClient(app)
        self.client = client
        resp = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        self.headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def test_cache_version_query(self):
        """缓存版本可查询"""
        resp = self.client.get("/api/stats/cache/version", headers=self.headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["version"], int)
