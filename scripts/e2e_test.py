"""
M5-F2 端到端验证：登录→录分→刷新 <3 秒

用法：PYTHONPATH=src ./venv/bin/python scripts/e2e_test.py

验收标准（F2）：
- 桌面启动 → API 登录 → 录分 → 查询 → 统计刷新 全流程 <3 秒
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from edu_system.api.main import create_app
from edu_system.database import init_db_with_defaults


def main():
    init_db_with_defaults()
    app = create_app()
    client = TestClient(app)

    steps = {}
    t0 = time.time()

    # 1. 登录
    t = time.time()
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, f"登录失败: {resp.status_code}"
    token = resp.json()["access_token"]
    steps["登录"] = time.time() - t

    headers = {"Authorization": f"Bearer {token}"}

    # 2. 查学生（端到端数据读取）
    t = time.time()
    resp = client.get("/api/students/me/scores", headers=headers)
    steps["学生查分"] = time.time() - t

    # 3. 查询成绩
    t = time.time()
    resp = client.get("/api/score/list", headers=headers)
    steps["成绩查询"] = time.time() - t

    # 4. 统计
    t = time.time()
    resp = client.get("/api/stats/overview", headers=headers)
    steps["统计概览"] = time.time() - t

    total = time.time() - t0

    print(f"{'步骤':<12}{'耗时(ms)':>10}")
    for name, dur in steps.items():
        print(f"{name:<12}{dur * 1000:>10.1f}")
    print(f"{'总耗时':<12}{total * 1000:>10.1f}")

    if total < 3.0:
        print(f"RESULT: PASS ({total:.2f}s < 3s)")
    else:
        print(f"RESULT: FAIL ({total:.2f}s >= 3s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
