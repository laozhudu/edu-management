"""
批量报表生成 Worker 测试（M5-D6）

覆盖 run_batch_render 同步核心：
- 进度回调递增（0→100，最后一步 100）
- 完成回调携带结果
- 单项失败重试（retry 后成功 / 重试耗尽收集失败）
- ZIP 打包（生成文件归档 + 单文件清理）
- 取消语义（cancel_check True 提前终止）
- 空列表安全
"""

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from edu_system.services.report_worker import run_batch_render


def _fake_render(out_dir):
    """生成一个假文件（模拟渲染产物）"""

    def _render(item):
        p = Path(out_dir) / f"report_{item}.txt"
        p.write_text(f"content {item}", encoding="utf-8")

    return _render


class TestBatchRender:
    def test_progress_increments(self, tmp_path):
        """进度回调 0→100 递增，最后一步 100"""
        out = tmp_path / "out"
        progress = []

        run_batch_render(
            [1, 2, 3, 4],
            _fake_render(str(out)),
            str(out),
            progress_cb=lambda p, msg: progress.append(p),
            retry=0,
        )

        assert progress[0] == 0
        assert progress[-1] == 100
        # 单调递增
        assert progress == sorted(progress)

    def test_finished_callback(self, tmp_path):
        """完成回调携带生成结果"""
        out = tmp_path / "out"
        results = []
        run_batch_render(
            [1, 2, 3],
            _fake_render(str(out)),
            str(out),
            finished_cb=results.append,
            retry=0,
        )
        assert len(results) == 1
        r = results[0]
        assert r["generated"] == 3
        assert r["failed"] == 0
        assert r["success"] is True

    def test_retry_success_after_failure(self, tmp_path):
        """首次失败重试后成功（retry=1）"""
        out = tmp_path / "out"
        calls = {"n": 0}

        def flaky_render(item):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("临时故障")
            (Path(out) / f"report_{item}.txt").write_text("ok", encoding="utf-8")

        r = run_batch_render([1], flaky_render, str(out), retry=1)
        assert r["generated"] == 1
        assert r["failed"] == 0
        assert calls["n"] == 2

    def test_retry_exhausted_reports_failure(self, tmp_path):
        """重试耗尽后收集失败项"""
        out = tmp_path / "out"
        errors = []

        def always_fail(item):
            raise RuntimeError("一直失败")

        r = run_batch_render(
            [1, 2],
            always_fail,
            str(out),
            error_cb=lambda item, err: errors.append((item, err)),
            retry=1,
        )
        assert r["generated"] == 0
        assert r["failed"] == 2
        assert len(errors) == 2
        assert all("一直失败" in e for _, e in errors)

    def test_zip_pack_and_cleanup(self, tmp_path):
        """生成文件打包为 ZIP 且单文件清理（keep_files 默认 False）"""
        out = tmp_path / "out"
        run_batch_render(
            [1, 2, 3],
            _fake_render(str(out)),
            str(out),
            retry=0,
            zip_name="reports.zip",
        )
        zip_path = out / "reports.zip"
        assert zip_path.exists(), "应生成 ZIP"
        with zipfile.ZipFile(zip_path) as zf:
            names = sorted(zf.namelist())
            assert names == ["report_1.txt", "report_2.txt", "report_3.txt"]
        # 单文件已清理
        singles = [f for f in out.iterdir() if f.name != "reports.zip"]
        assert singles == [], f"单文件应清理: {singles}"

    def test_cancel_stops_early(self, tmp_path):
        """cancel_check 提前终止，返回 cancelled"""
        out = tmp_path / "out"
        state = {"n": 0}

        def render_with_counter(item):
            state["n"] += 1
            (Path(out) / f"r_{item}.txt").write_text("x", encoding="utf-8")

        # 第 3 项时取消
        def cancel_check():
            return state["n"] >= 2

        r = run_batch_render(
            [1, 2, 3, 4, 5],
            render_with_counter,
            str(out),
            cancel_check=cancel_check,
            retry=0,
        )
        assert r["cancelled"] is True
        assert state["n"] == 2

    def test_empty_items_safe(self, tmp_path):
        """空列表安全返回"""
        out = tmp_path / "out"
        r = run_batch_render([], _fake_render(str(out)), str(out), retry=0)
        assert r["generated"] == 0
        assert r["success"] is True
