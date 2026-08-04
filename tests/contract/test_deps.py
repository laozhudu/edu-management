"""
FastAPI 依赖注入契约测试（M5-A3）

测试 api/deps.py 中的学期上下文依赖：
- get_current_semester: 获取当前激活学期
- set_current_semester_dep: 设置当前学期（依赖注入版本）
- 双端复用：桌面端与 API 端共用同一套上下文管理
"""

import sys
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, Query
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

from edu_system.api.deps import get_current_semester, set_current_semester_dep
from edu_system.database import get_active_semester, set_active_semester


class TestSemesterDeps:
    """学期依赖注入契约测试"""

    @pytest.fixture(autouse=True)
    def _clean_semester(self):
        """每个测试前清理线程局部学期"""
        set_active_semester(0)
        yield
        set_active_semester(0)

    def test_get_current_semester_default_zero(self):
        """默认学期为 0"""
        assert get_current_semester() == 0
        # 与线程局部存储一致
        assert get_active_semester() == 0

    def test_set_current_semester_dep(self):
        """设置学期依赖注入"""
        result = set_current_semester_dep(5)
        assert result == 5
        assert get_active_semester() == 5
        assert get_current_semester() == 5

    def test_get_current_semester_after_set(self):
        """设置后获取当前学期"""
        set_active_semester(7)
        assert get_current_semester() == 7

    def test_fastapi_integration(self):
        """FastAPI 集成测试：依赖注入在请求中生效

        注意：TestClient 可能使用不同线程处理每个请求，
        线程局部存储不跨请求共享。真实部署中单线程/单进程下生效。
        """
        app = FastAPI()

        @app.get("/test-semester")
        def test_endpoint(semester_id: int = Depends(get_current_semester)):
            return {"semester_id": semester_id}

        # 使用 Query 参数而不是路径参数
        @app.post("/set-semester")
        def set_endpoint(
            semester_id: int = Query(...), sem_id: int = Depends(set_current_semester_dep)
        ):
            return {"set_semester_id": sem_id}

        client = TestClient(app)

        # 默认请求
        resp = client.get("/test-semester")
        assert resp.status_code == 200
        assert resp.json()["semester_id"] == 0

        # 设置学期（在同一请求中生效）
        resp = client.post("/set-semester?semester_id=10")
        assert resp.status_code == 200
        assert resp.json()["set_semester_id"] == 10

        # 跨请求不共享线程局部存储（TestClient 行为），这是预期的
        # 真实部署中需使用 ContextVar 或会话存储跨请求传递

    def test_context_isolation_thread_local(self):
        """线程隔离：不同线程学期上下文互不影响"""
        import threading

        set_active_semester(1)
        assert get_current_semester() == 1

        results = {}

        def worker():
            # 子线程默认看到 0
            results["before"] = get_current_semester()
            set_active_semester(99)
            results["after_set"] = get_current_semester()

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert results["before"] == 0  # 子线程看不到主线程的值
        assert results["after_set"] == 99
        assert get_current_semester() == 1  # 主线程不受子线程影响


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
