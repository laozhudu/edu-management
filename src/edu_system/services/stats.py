"""
统计工具库 — 纯函数，无状态
"""


def filter_valid(scores: list[float | None], absent_marks: set | None = None) -> list[float]:
    """过滤有效成绩"""
    absent = absent_marks or set()
    return [s for s in scores if s is not None and s not in absent]


def calc_pass_rate(
    scores: list[float | None], pass_line: float, absent_marks: set | None = None
) -> dict:
    """计算及格/良好/优秀/低分率"""
    valid = filter_valid(scores, absent_marks)
    vc = len(valid)
    if vc == 0:
        return {"avg": 0, "pass": 0, "good": 0, "excellent": 0, "low": 0}

    return {
        "avg": round(sum(valid) / vc, 2),
        "pass": round(sum(1 for s in valid if s >= pass_line) / vc * 100, 1),
        "good": round(sum(1 for s in valid if s >= pass_line * 1.2) / vc * 100, 1),
        "excellent": round(sum(1 for s in valid if s >= pass_line * 1.5) / vc * 100, 1),
        "low": round(sum(1 for s in valid if s < pass_line * 0.5) / vc * 100, 1),
    }


def calc_distribution(
    scores: list[float | None],
    segments: list[tuple[float, float, str]],
    absent_marks: set | None = None,
) -> list[dict]:
    """分数段分布"""
    valid = filter_valid(scores, absent_marks)
    total = len(valid) or 1
    return [
        {
            "label": label,
            "count": sum(1 for s in valid if lo <= s <= hi),
            "rate": round(sum(1 for s in valid if lo <= s <= hi) / total * 100, 1),
        }
        for lo, hi, label in segments
    ]
