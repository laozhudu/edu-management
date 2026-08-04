"""
幂等性中间件单元测试
验证：写请求拦截、重复请求缓存、过期清理
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from edu_system.core.idempotency import cleanup_expired_keys
from edu_system.models import IdempotencyKey


@pytest.fixture(scope="module")
def client():
    """创建带幂等中间件的测试应用"""
    app = FastAPI()

    from edu_system.core.idempotency import IdempotencyMiddleware

    app.add_middleware(IdempotencyMiddleware)

    @app.post("/test/write")
    def write_endpoint():
        return {"status": "ok", "data": "created"}

    @app.get("/test/read")
    def read_endpoint():
        return {"status": "ok", "data": "read"}

    return TestClient(app)


def test_write_request_with_idempotency_key(client):
    """写请求携带 Idempotency-Key 应正常执行并缓存"""
    resp = client.post("/test/write", headers={"Idempotency-Key": "test-key-1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_repeated_request_returns_cached_response(client):
    """相同 Idempotency-Key 的重复请求应返回缓存响应"""
    headers = {"Idempotency-Key": "test-key-dup"}
    first = client.post("/test/write", headers=headers)
    second = client.post("/test/write", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_write_request_without_key_not_cached(client):
    """无 Idempotency-Key 的写请求直接放行"""
    resp = client.post("/test/write")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_read_request_ignored(client):
    """GET 请求不受幂等中间件影响"""
    resp = client.get("/test/read")
    assert resp.status_code == 200


def test_cleanup_expired_keys(db_session):
    """过期键应被清理"""
    from datetime import datetime, timedelta

    expired = IdempotencyKey(
        key="expired-key",
        response_body="{}",
        status_code=200,
        response_headers="{}",
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )
    db_session.add(expired)
    db_session.commit()

    deleted = cleanup_expired_keys()
    assert deleted >= 1

    from edu_system.database import get_session

    session = get_session()
    try:
        remaining = session.query(IdempotencyKey).filter_by(key="expired-key").first()
        assert remaining is None
    finally:
        session.close()
