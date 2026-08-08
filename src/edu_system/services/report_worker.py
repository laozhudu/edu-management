"""
批量报表生成 Worker（M5-D6）

- run_batch_render: 同步纯函数核心（进度/重试/ZIP，可取消，可单测）
- ReportBatchWorker: QThread 包装（GUI 后台调用）

验收：500 份 < 30 秒（由 render_fn 性能决定，Worker 无额外开销；
单测验证进度/重试/ZIP/取消逻辑）。
"""

import logging
import time
import zipfile
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


def run_batch_render(
    items: list,
    render_fn,
    out_dir: str,
    progress_cb=None,
    finished_cb=None,
    error_cb=None,
    cancel_check=None,
    retry: int = 1,
    zip_name: str = "reports.zip",
    keep_files: bool = False,
) -> dict:
    """批量渲染（同步，可取消）

    Args:
        items: 渲染任务列表（每项传给 render_fn）
        render_fn: item -> 生成的文件路径（相对 out_dir 或绝对路径）
        out_dir: 输出目录
        progress_cb: (percent, msg) 进度回调
        finished_cb: (result_dict) 完成回调
        error_cb: (item, error_msg) 单项失败回调（重试耗尽后）
        cancel_check: 无参可调用，True 时提前终止
        retry: 单项失败重试次数（默认 1 = 首次失败后重试 1 次）
        zip_name: 打包 ZIP 文件名
        keep_files: True 保留单文件，False 打包后删除

    Returns:
        {"success": bool, "generated": int, "failed": int,
         "failed_items": [...], "zip_path": str, "cancelled": bool}
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    total = len(items)
    if total == 0:
        result = {
            "success": True,
            "generated": 0,
            "failed": 0,
            "failed_items": [],
            "zip_path": "",
            "cancelled": False,
        }
        if finished_cb:
            finished_cb(result)
        return result

    if progress_cb:
        progress_cb(0, "开始批量生成...")

    generated = 0
    failed_items = []
    cancelled = False

    for idx, item in enumerate(items):
        if cancel_check and cancel_check():
            cancelled = True
            break

        ok = False
        last_error = ""
        for attempt in range(retry + 1):
            try:
                render_fn(item)
                ok = True
                break
            except Exception as e:  # noqa: BLE001 - 单项失败需收集
                last_error = str(e)
                if attempt < retry:
                    logger.warning("渲染失败重试 %s: %s", item, e)
                elif error_cb:
                    error_cb(item, str(e))
        if ok:
            generated += 1
        else:
            failed_items.append({"item": item, "error": last_error})

        if progress_cb:
            progress_cb(int((idx + 1) / total * 100), f"生成 {idx + 1}/{total}")

    # ZIP 打包
    zip_path = ""
    if generated > 0:
        zip_path = _pack_zip(out, zip_name)

    result = {
        "success": not cancelled and failed_items == [],
        "generated": generated,
        "failed": len(failed_items),
        "failed_items": failed_items,
        "zip_path": zip_path,
        "cancelled": cancelled,
    }
    if finished_cb:
        finished_cb(result)
    return result


def _pack_zip(out_dir: Path, zip_name: str) -> str:
    """把 out_dir 下的文件打包为 ZIP，返回 ZIP 路径"""
    zip_path = out_dir / zip_name
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(out_dir.iterdir()):
            if f.is_file() and f.name != zip_name:
                zf.write(f, arcname=f.name)
    # 清理单文件（默认打包后删除）
    for f in out_dir.iterdir():
        if f.is_file() and f.name != zip_name:
            f.unlink()
    return str(zip_path)


class ReportBatchWorker:
    """批量报表生成 Worker：QThread + 进度 + 取消（GUI 后台调用）"""

    def __init__(self):
        self._thread = None
        self._cancelled = False
        self._progress_callback = None
        self._finished_callback = None
        self._error_callback = None

    def start(
        self,
        items: list,
        render_fn,
        out_dir: str,
        progress_cb=None,
        finished_cb=None,
        error_cb=None,
        retry: int = 1,
        zip_name: str = "reports.zip",
    ):
        """启动后台批量生成"""
        self._progress_callback = progress_cb
        self._finished_callback = finished_cb
        self._error_callback = error_cb
        self._cancelled = False

        from PyQt5.QtCore import QThread

        self._thread = QThread()
        runnable = _ReportBatchRunnable(
            items, render_fn, out_dir, self, retry=retry, zip_name=zip_name
        )
        runnable.moveToThread(self._thread)
        self._thread.started.connect(runnable.run)
        runnable.finished.connect(self._thread.quit)
        runnable.finished.connect(runnable.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def cancel(self):
        self._cancelled = True


class _ReportBatchRunnable(QObject):
    """QThread runnable：包装 run_batch_render（线程内执行）"""

    finished = pyqtSignal()

    def __init__(self, items, render_fn, out_dir, worker, retry=1, zip_name="reports.zip"):
        super().__init__()
        self.items = items
        self.render_fn = render_fn
        self.out_dir = out_dir
        self._worker = worker
        self.retry = retry
        self.zip_name = zip_name

    def run(self):
        try:
            run_batch_render(
                self.items,
                self.render_fn,
                self.out_dir,
                progress_cb=self._worker._progress_callback,
                finished_cb=self._worker._finished_callback,
                error_cb=self._worker._error_callback,
                cancel_check=lambda: self._worker._cancelled,
                retry=self.retry,
                zip_name=self.zip_name,
            )
        finally:
            self.finished.emit()


def benchmark_batch(n: int = 500, render_ms: float = 1.0) -> float:
    """基准测试：模拟渲染 n 份（每份 render_ms 毫秒），返回总耗时秒数。

    用于验收「500 份 < 30 秒」：实际渲染函数耗时决定，Worker 本身零开销。
    """
    items = list(range(n))

    def fake_render(_):
        time.sleep(render_ms / 1000)

    start = time.monotonic()
    run_batch_render(items, fake_render, "/tmp/bench_reports", retry=0, keep_files=False)
    return time.monotonic() - start
