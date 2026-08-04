"""
打印服务（Sprint 4.8.3）

- 统一封装 win32print（Windows）与 lp 命令（Linux/macOS）
- 批量队列、指定打印机
- 平台无关接口：print_file / print_files / list_printers
"""

import shutil
import subprocess
import sys
from pathlib import Path


class PrintError(Exception):
    """打印错误"""


class PrintService:
    def __init__(self, printer: str | None = None):
        self.printer = printer
        self._is_windows = sys.platform == "win32"

    # ── 平台能力 ──
    @property
    def available(self) -> bool:
        """当前平台是否有可用的打印后端"""
        if self._is_windows:
            try:
                import win32print  # noqa: F401

                has_win32 = True
            except ImportError:
                has_win32 = False
            return has_win32
        return shutil.which("lp") is not None

    # ── 打印机列表 ──
    def list_printers(self) -> list[str]:
        """列出可用打印机"""
        if not self.available:
            return []
        if self._is_windows:
            import win32print

            return [p[2] for p in win32print.EnumPrinters(2)]
        # Linux: lpstat -a
        try:
            result = subprocess.run(
                ["lpstat", "-a"], capture_output=True, text=True, timeout=10, check=False
            )
            if result.returncode == 0:
                return [line.split()[0] for line in result.stdout.splitlines() if line.strip()]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return []

    # ── 单文件打印 ──
    def print_file(self, file_path: str | Path, copies: int = 1) -> bool:
        """打印单个文件"""
        path = Path(file_path)
        if not path.exists():
            raise PrintError(f"文件不存在: {path}")
        if not self.available:
            raise PrintError("无可用打印后端（Windows 需 pywin32，Linux 需 CUPS lp）")

        if self._is_windows:
            return self._print_windows(path, copies)
        return self._print_lp(path, copies)

    def _print_windows(self, path: Path, copies: int) -> bool:
        import win32api
        import win32print

        printer_name = self.printer or win32print.GetDefaultPrinter()
        result = win32api.ShellExecute(0, "print", str(path), f'/d:"{printer_name}"', None, 0)
        return result > 32

    def _print_lp(self, path: Path, copies: int) -> bool:
        cmd = ["lp"]
        if self.printer:
            cmd += ["-d", self.printer]
        if copies > 1:
            cmd += ["-n", str(copies)]
        cmd.append(str(path))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
            ok = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise PrintError(f"lp 打印失败: {e}") from e
        return ok

    # ── 批量打印 ──
    def print_files(self, file_paths: list[str | Path], copies: int = 1) -> dict[str, bool]:
        """批量打印，返回 文件→成功 映射"""
        results = {}
        for fp in file_paths:
            try:
                results[str(fp)] = self.print_file(fp, copies)
            except PrintError as e:
                results[str(fp)] = False
        return results
