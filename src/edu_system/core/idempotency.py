"""
幂等性中间件
- 仅拦截写请求 (POST/PUT/PATCH/DELETE)
- 基于 Idempotency-Key 请求头
- SQLite 唯一索引表 + TTL 1 天自动清理
"""

import json
from datetime import datetime, timedelta

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from edu_system.database import get_session
from edu_system.models import IdempotencyKey


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 仅拦截写请求
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)

        key = request.headers.get("Idempotency-Key")
        if not key:
            return await call_next(request)

        session = get_session()
        try:
            # 查找现有键
            existing = session.query(IdempotencyKey).filter_by(key=key).first()
            now = datetime.utcnow()

            if existing:
                if existing.expires_at > now:
                    # 返回缓存响应
                    headers = {}
                    if existing.response_headers:
                        headers = json.loads(existing.response_headers)
                    return Response(
                        content=existing.response_body,
                        status_code=existing.status_code,
                        headers=headers,
                        media_type=headers.get("content-type", "application/json"),
                    )
                else:
                    # 过期删除
                    session.delete(existing)
                    session.commit()

            # 执行请求并捕获响应
            response = await call_next(request)

            # 读取响应体
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            # 存储幂等键
            headers_dict = dict(response.headers)
            new_key = IdempotencyKey(
                key=key,
                response_body=body.decode("utf-8", errors="ignore"),
                status_code=response.status_code,
                response_headers=json.dumps(headers_dict, ensure_ascii=False),
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
            session.add(new_key)
            session.commit()

            # 重建响应
            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers_dict,
                media_type=headers_dict.get("content-type", "application/json"),
            )
        finally:
            session.close()


# 便捷函数：手动检查/存储（用于非 HTTP 场景）
def check_idempotency(key: str) -> tuple[bool, Response | None]:
    """检查幂等键，返回 (是否存在, 缓存响应)"""
    session = get_session()
    try:
        existing = session.query(IdempotencyKey).filter_by(key=key).first()
        if existing and existing.expires_at > datetime.utcnow():
            headers = json.loads(existing.response_headers) if existing.response_headers else {}
            return True, Response(
                content=existing.response_body,
                status_code=existing.status_code,
                headers=headers,
                media_type=headers.get("content-type", "application/json"),
            )
        return False, None
    finally:
        session.close()


def store_idempotency(key: str, response: Response):
    """存储幂等键（已废弃：请使用中间件自动处理）"""
    # 中间件自动完成存储，此函数保留仅为兼容旧调用
    session = get_session()
    try:
        existing = session.query(IdempotencyKey).filter_by(key=key).first()
        if existing:
            session.delete(existing)
        new_key = IdempotencyKey(
            key=key,
            response_body="",
            status_code=response.status_code,
            response_headers="{}",
            expires_at=datetime.utcnow() + timedelta(days=1),
        )
        session.add(new_key)
        session.commit()
    finally:
        session.close()


def cleanup_expired_keys() -> int:
    """清理过期键（APScheduler 定时调用）"""
    session = get_session()
    try:
        deleted = (
            session.query(IdempotencyKey)
            .filter(IdempotencyKey.expires_at <= datetime.utcnow())
            .delete()
        )
        session.commit()
        return int(deleted)
    finally:
        session.close()
