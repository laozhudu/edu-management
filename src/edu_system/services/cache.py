"""
缓存服务层
基于 diskcache + 版本控制 + HTTP 304 支持
"""

import hashlib
import json
from datetime import date, datetime
from functools import wraps
from typing import Any

import diskcache
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from edu_system.database import get_active_school, get_active_semester


class SafeJSONDisk(diskcache.JSONDisk):
    """JSON 序列化磁盘存储（规避 diskcache 默认 pickle 反序列化漏洞 CVE-2025-69872）

    除 JSON 外额外支持 datetime/date 序列化（转 ISO 字符串）。
    若值含非 JSON 类型(如任意对象)则回退 pickle 存储以保功能——此类数据不应进安全缓存。
    """

    @staticmethod
    def _default(obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def store(self, value, read, key=diskcache.UNKNOWN):  # type: ignore[override]
        if not read:
            json_bytes = json.dumps(value, default=self._default).encode("utf-8")
            import zlib

            value = zlib.compress(json_bytes, self.compress_level)
        return super(diskcache.JSONDisk, self).store(value, read, key=key)  # type: ignore[override]


# 全局缓存实例
_stats_cache = None
_http_cache = None


def get_stats_cache() -> diskcache.Cache:
    """获取统计数据缓存实例（持久化到磁盘）"""
    global _stats_cache
    if _stats_cache is None:
        import os

        # 使用相对路径，兼容 CI 环境
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(project_root, "data", "cache", "stats")
        os.makedirs(cache_dir, exist_ok=True)
        _stats_cache = diskcache.Cache(
            directory=cache_dir,
            timeout=30,
            size_limit=2**30,  # 1GB
            disk_min_file_size=0,
            disk=SafeJSONDisk,
            disk_pickle_protocol=4,
        )
    return _stats_cache


def get_http_cache() -> diskcache.Cache:
    """获取 HTTP 响应缓存实例"""
    global _http_cache
    if _http_cache is None:
        import os

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(project_root, "data", "cache", "http")
        os.makedirs(cache_dir, exist_ok=True)
        _http_cache = diskcache.Cache(
            directory=cache_dir,
            timeout=30,
            size_limit=512 * 1024 * 1024,  # 512MB
            disk=SafeJSONDisk,
        )
    return _http_cache


class CacheService:
    """统计数据缓存服务：内存级读取 + 版本控制 + 标签失效"""

    def __init__(self):
        self.cache = get_stats_cache()
        self._version_key = "stats:version"
        self._tag_index = "stats:tag_index"  # tag -> [keys]

    def _make_key(self, entity_type: str, entity_id: int, metric_key: str, semester_id: int) -> str:
        """生成缓存键"""
        return f"stats:{semester_id}:{entity_type}:{entity_id}:{metric_key}"

    def _make_tag(self, *tags: str) -> str:
        return ":".join(sorted(tags))

    def get(
        self, entity_type: str, entity_id: int, metric_key: str, semester_id: int = None
    ) -> dict | None:
        """读取缓存，自动校验版本"""
        if semester_id is None:
            semester_id = get_active_semester()

        key = self._make_key(entity_type, entity_id, metric_key, semester_id)
        data = self.cache.get(key)

        if data is None:
            return None

        # 校验版本
        current_version = self.get_version()
        if data.get("version") != current_version:
            self.cache.delete(key)
            return None

        return data

    def get_multi(self, keys: list[tuple]) -> dict[str, Any]:
        """批量读取"""
        result = {}
        for entity_type, entity_id, metric_key in keys:
            semester_id = get_active_semester()
            key = f"stats:{get_active_semester()}:{entity_type}:{entity_id}:{metric_key}"
            data = self.cache.get(key)
            if data and data.get("version") == self.get_version():
                result[f"{entity_type}:{entity_id}:{metric_key}"] = data
        return result

    def set(
        self,
        entity_type: str,
        entity_id: int,
        metric_key: str,
        value: float,
        semester_id: int = None,
        tags: list[str] = None,
        ttl: int = None,
    ) -> bool:
        """写入缓存，自动关联标签和版本"""
        if semester_id is None:
            semester_id = get_active_semester()

        key = self._make_key(entity_type, entity_id, metric_key, semester_id)
        version = self.get_version()

        data = {
            "value": value,
            "version": version,
            "computed_at": datetime.now().isoformat(),
            "tags": tags or [],
        }

        # 写入主键
        self.cache.set(key, data, expire=None)  # 不自动过期，靠版本失效

        # 更新标签索引
        if tags:
            for tag in tags:
                tag_key = f"tag:{semester_id}:{tag}"
                existing = self.cache.get(tag_key) or []
                if key not in existing:
                    existing.append(key)
                    self.cache.set(tag_key, existing)

        return True

    def set_multi(self, items: list[dict]) -> int:
        """批量写入"""
        count = 0
        for item in items:
            self.set(
                entity_type=item["entity_type"],
                entity_id=item["entity_id"],
                metric_key=item["metric_key"],
                value=item["value"],
                semester_id=item.get("semester_id"),
                tags=item.get("tags"),
            )
            count += 1
        return count

    def get_version(self) -> int:
        """获取当前缓存版本号"""
        return self.cache.get(self._version_key, 1)

    def bump_version(self) -> int:
        """递增版本号，使所有旧缓存失效"""
        new_version = self.get_version() + 1
        self.cache.set(self._version_key, new_version)
        return new_version

    def invalidate_by_tag(self, semester_id: int, tag: str) -> int:
        """按标签批量失效"""
        tag_key = f"tag:{semester_id}:{tag}"
        keys = self.cache.get(tag_key) or []
        count = 0
        for key in keys:
            self.cache.delete(key)
            count += 1
        self.cache.delete(tag_key)
        return count

    def invalidate_semester(self, semester_id: int) -> int:
        """失效某学期所有缓存"""
        # 删除该学期的所有统计键
        prefix = f"stats:{semester_id}:"
        count = 0
        for key in self.cache.iterkeys():
            if key.startswith(prefix):
                self.cache.delete(key)
                count += 1
        return count

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            "version": self.get_version(),
            "entry_count": len(list(self.cache.iterkeys())),
            "size_bytes": self.cache.volume(),
            "directory": self.cache.directory,
        }


class HttpCacheMiddleware(BaseHTTPMiddleware):
    """HTTP 响应缓存中间件：支持 ETag / Last-Modified / 304"""

    def __init__(self, app, cache_dir: str | None = None):
        super().__init__(app)
        if cache_dir is None:
            import os

            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(project_root, "data", "cache", "http")
        self.cache = diskcache.Cache(
            directory=cache_dir, size_limit=512 * 1024 * 1024, disk=SafeJSONDisk
        )
        self._enabled_paths = ["/api/stats/", "/api/classes/", "/api/students/", "/api/exams/"]

    def _should_cache(self, request: Request) -> bool:
        """判断是否需要缓存"""
        if request.method != "GET":
            return False
        path = request.url.path
        return any(path.startswith(p) for p in self._enabled_paths)

    def _make_cache_key(self, request: Request) -> str:
        """生成缓存键：路径 + 查询参数 + 学期 + 校区"""
        semester_id = get_active_semester()
        school_id = get_active_school()
        query = str(request.query_params)
        return f"http:{semester_id}:{school_id}:{request.url.path}:{query}"

    def _compute_etag(self, content: bytes) -> str:
        """计算 ETag（非安全用途，仅缓存一致性校验）"""
        return hashlib.md5(content, usedforsecurity=False).hexdigest()

    async def dispatch(self, request: Request, call_next):
        if not self._should_cache(request):
            return await call_next(request)

        cache_key = self._make_cache_key(request)

        # 检查 If-None-Match / If-Modified-Since
        if_none_match = request.headers.get("If-None-Match")
        if_modified_since = request.headers.get("If-Modified-Since")

        cached = self.cache.get(cache_key)

        if cached:
            # 检查条件请求
            if if_none_match and if_none_match == cached.get("etag"):
                return StarletteResponse(status_code=304, headers={"ETag": cached["etag"]})

            if if_modified_since:
                try:
                    modified = datetime.fromisoformat(cached["modified"].replace("Z", "+00:00"))
                    if_modified = datetime.strptime(if_modified_since, "%a, %d %b %Y %H:%M:%S %Z")
                    if modified <= if_modified:
                        return StarletteResponse(status_code=304)
                except:
                    pass

            # 返回缓存响应
            content = cached["content"]
            headers = cached.get("headers", {})
            headers["ETag"] = cached["etag"]
            headers["Last-Modified"] = cached["modified"]
            headers["X-Cache"] = "HIT"
            return StarletteResponse(content=content, headers=headers)

        # 执行请求
        response = await call_next(request)

        # 缓存响应
        if response.status_code == 200:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            etag = self._compute_etag(body)
            modified = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

            self.cache.set(
                cache_key,
                {
                    "content": body,
                    "etag": etag,
                    "modified": modified,
                    "headers": dict(response.headers),
                },
                expire=3600,
            )  # 1小时过期

            # 重新构建响应
            headers = dict(response.headers)
            headers["ETag"] = etag
            headers["Last-Modified"] = modified
            headers["X-Cache"] = "MISS"

            return StarletteResponse(
                content=body, status_code=response.status_code, headers=headers
            )

        return response


# 全局缓存服务实例
cache_service = CacheService()


def cache_stats(
    entity_type: str,
    entity_id: int,
    metric_key: str,
    semester_id: int = None,
    tags: list[str] = None,
    ttl: int = None,
):
    """装饰器：自动缓存统计计算结果"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_svc = cache_service
            sem_id = semester_id or get_active_semester()
            entity_id = kwargs.get("entity_id") or (args[0] if args else None)

            # 尝试读取缓存
            cached = cache_svc.get("custom", entity_id or 0, metric_key, semester_id)
            if cached:
                return cached["value"]

            # 执行计算
            result = func(*args, **kwargs)

            # 写入缓存
            tags = ["stats", metric_key]
            cache_svc.set(
                "custom", entity_id or 0, metric_key, result, semester_id=semester_id, tags=tags
            )
            return result

        return wrapper

    return decorator


def invalidate_stats_cache(semester_id: int = None, tags: list[str] = None):
    """失效统计缓存"""
    cache_svc = cache_service
    sem_id = semester_id or get_active_semester()

    if tags:
        for tag in tags:
            cache_svc.invalidate_by_tag(sem_id, tag)
    else:
        cache_svc.invalidate_semester(sem_id)

    # 递增版本号，使所有缓存失效
    cache_svc.bump_version()


# ===== 便捷函数 =====


def get_cached_stat(
    entity_type: str, entity_id: int, metric_key: str, semester_id: int = None
) -> float | None:
    """快速获取单个统计指标"""
    data = cache_service.get(entity_type, entity_id, metric_key, semester_id)
    return data["value"] if data else None


def set_cached_stat(
    entity_type: str,
    entity_id: int,
    metric_key: str,
    value: float,
    semester_id: int = None,
    tags: list[str] = None,
):
    """快速设置单个统计指标"""
    cache_service.set(entity_type, entity_id, metric_key, value, semester_id, tags)


def bump_cache_version() -> int:
    """递增缓存版本"""
    return cache_service.bump_version()


def get_cache_stats() -> dict:
    """获取缓存统计"""
    return cache_service.get_stats()
