"""Web 模板 API 端点一致性校验

用法（服务运行在 8080）：
    python scripts/check_api_alignment.py [base_url]

目的：扫描 templates/*.html 中 fetch 的 /api/ 端点，逐一探测 HTTP 状态，
    标记真实 404（缺失端点）。返回码 0=无缺失，1=有缺失（供 CI 拦截）。

判定规则：
- 200/401/403/422/405 = 端点存在（认证/参数校验属正常）
- 404 = 端点缺失 → 视为错误
- 排除明显带路径参数的模板变量拼接（如 /api/stats/semester/{id}）
"""

import re
import sys
from pathlib import Path

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"

tpl_dir = Path(__file__).resolve().parent.parent / "src" / "edu_system" / "templates"


def collect_refs() -> set[str]:
    refs = set()
    for f in tpl_dir.glob("*.html"):
        text = f.read_text(encoding="utf-8")
        for m in re.finditer(r"['\"]\s*(/api/[A-Za-z0-9_/{}.$+-]+)", text):
            ep = m.group(1).split("${")[0].split("{")[0]
            # 跳过以 / 结尾的（前端变量拼接片段，如 /api/stats/semester/' + id + '/summary）
            if ep.rstrip("/") != ep:
                continue
            # 跳过含路径参数模板变量的（前端会拼 ID，非完整端点）
            if "{" in ep or "$" in ep:
                continue
            refs.add(ep.rstrip("/"))
    return refs


def main() -> int:
    # 登录获取 token
    try:
        r = requests.post(
            BASE + "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=5,
        )
        token = r.json()["access_token"]
    except Exception as e:
        print(f"[FAIL] 无法登录验证: {e}")
        return 1
    headers = {"Authorization": f"Bearer {token}"}

    refs = collect_refs()
    missing = []
    for ep in sorted(refs):
        try:
            resp = requests.get(BASE + ep, headers=headers, timeout=5)
            if resp.status_code == 404:
                missing.append(ep)
        except Exception as e:
            print(f"[ERR] {ep}: {str(e)[:60]}")
            missing.append(ep)

    if missing:
        print("=== 缺失端点 (404) ===")
        for ep in missing:
            print(f"  {ep}")
        return 1
    print(f"✅ 全部 {len(refs)} 个端点存在（200/401/403/422/405 均视为存在）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
