"""
M5-F3 并发压测：20 设备并发写 SQLite WAL 无锁死

用法：PYTHONPATH=src ./venv/bin/python scripts/stress_test.py [并发数] [每并发写次数]

验收标准（F3）：
- 20 并发 × 每次写入，全部成功（无 database is locked）
- 无死锁（全部在 timeout 内完成）
"""

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text

from edu_system.database import init_db, get_session

CONCURRENCY = 20
WRITES_PER_THREAD = 10


def worker(thread_id: int, results: list, lock: threading.Lock):
    """每并发：多次写入 audit_logs（模拟并发 API 审计写入）"""
    try:
        session = get_session()
        for i in range(WRITES_PER_THREAD):
            session.execute(
                text(
                    "INSERT INTO audit_logs (table_name, record_id, action, old_values, "
                    "new_values, operator, ip, created_at) "
                    "VALUES ('stress_test', 0, 'STRESS', :old, :new, :op, :ip, datetime('now'))"
                ),
                {
                    "old": f'{{"t": {thread_id}, "i": {i}}}',
                    "new": '{"status": 200}',
                    "op": f"t{thread_id}",
                    "ip": "127.0.0.1",
                },
            )
            session.commit()
        session.close()
        with lock:
            results["ok"] += 1
    except Exception as e:  # noqa: BLE001
        with lock:
            results["fail"].append(f"t{thread_id}: {e}")


def main():
    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else CONCURRENCY
    n_writes = int(sys.argv[2]) if len(sys.argv) > 2 else WRITES_PER_THREAD

    init_db()
    results = {"ok": 0, "fail": []}
    rlock = threading.Lock()

    print(f"压测：{n_workers} 并发 × {n_writes} 次写入（SQLite WAL）...")
    start = time.time()

    threads = [threading.Thread(target=worker, args=(i, results, rlock)) for i in range(n_workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    elapsed = time.time() - start
    total = n_workers * n_writes

    print(f"完成：{elapsed:.2f}s，成功 {results['ok']}/{n_workers} 线程")
    if results["fail"]:
        print(f"失败 {len(results['fail'])} 条：")
        for f in results["fail"][:5]:
            print(f"  {f}")
        print("RESULT: FAIL")
        sys.exit(1)

    # 验证无锁死（全部线程完成 + 数据完整）
    # 注：audit_init 监听器会为每次写入额外记一条审计，故行数 ≥ total 即可
    session = get_session()
    count = session.execute(text("SELECT COUNT(*) FROM audit_logs WHERE action='STRESS'")).scalar()
    session.close()
    print(f"写入审计行数：{count}（期望 ≥ {total}）")
    if count < total:
        print("RESULT: FAIL (行数不匹配)")
        sys.exit(1)

    print(f"RESULT: PASS ({elapsed:.2f}s, {total} 写入, 无锁死)")


if __name__ == "__main__":
    main()
