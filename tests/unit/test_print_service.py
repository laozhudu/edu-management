"""
PrintService 测试（Sprint 4.8.3）
覆盖：文件不存在、无后端、批量映射、lp 调用（mock）
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from edu_system.services.print_service import PrintError, PrintService


@pytest.fixture
def pdf_file(tmp_path):
    p = tmp_path / "test.pdf"
    p.write_bytes(b"%PDF-1.4 test")
    return p


class TestAvailability:
    def test_backend_detection(self):
        """Linux 平台 lp 存在则 available"""
        svc = PrintService()
        # 不强制断言（CI 可能无 CUPS），只验证不抛异常
        assert isinstance(svc.available, bool)


class TestPrintFile:
    def test_missing_file(self):
        svc = PrintService()
        with pytest.raises(PrintError, match="不存在"):
            svc.print_file("/nonexistent/file.pdf")

    def test_no_backend(self, monkeypatch, pdf_file):
        """无 lp 时抛无后端错误"""
        svc = PrintService()
        monkeypatch.setattr(PrintService, "available", False)
        with pytest.raises(PrintError, match="无可用打印后端"):
            svc.print_file(pdf_file)

    def test_lp_invocation(self, monkeypatch, pdf_file):
        """lp 命令调用（mock subprocess）"""
        svc = PrintService()
        monkeypatch.setattr(PrintService, "available", True)
        calls = {}

        def fake_run(cmd, capture_output, text, timeout, check):
            calls["cmd"] = cmd
            import types

            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr("edu_system.services.print_service.subprocess.run", fake_run)
        assert svc.print_file(pdf_file) is True
        assert calls["cmd"][0] == "lp"
        assert str(pdf_file) in calls["cmd"]

    def test_lp_with_printer_and_copies(self, monkeypatch, pdf_file):
        svc = PrintService(printer="HP_1010")
        monkeypatch.setattr(PrintService, "available", True)
        calls = {}

        def fake_run(cmd, capture_output, text, timeout, check):
            calls["cmd"] = cmd
            import types

            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr("edu_system.services.print_service.subprocess.run", fake_run)
        svc.print_file(pdf_file, copies=3)
        assert "-d" in calls["cmd"]
        assert "HP_1010" in calls["cmd"]
        assert "-n" in calls["cmd"]
        assert "3" in calls["cmd"]

    def test_lp_failure(self, monkeypatch, pdf_file):
        svc = PrintService()
        monkeypatch.setattr(PrintService, "available", True)

        def fake_run(cmd, capture_output, text, timeout, check):
            import types

            return types.SimpleNamespace(returncode=1, stdout="", stderr="error")

        monkeypatch.setattr("edu_system.services.print_service.subprocess.run", fake_run)
        assert svc.print_file(pdf_file) is False


class TestBatch:
    def test_print_files_mapping(self, monkeypatch, tmp_path):
        svc = PrintService()
        monkeypatch.setattr(PrintService, "available", True)

        def fake_run(cmd, capture_output, text, timeout, check):
            import types

            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr("edu_system.services.print_service.subprocess.run", fake_run)
        f1 = tmp_path / "a.pdf"
        f1.write_bytes(b"%PDF-1.4")
        results = svc.print_files([f1, "/missing.pdf"])
        assert results[str(f1)] is True
        assert results["/missing.pdf"] is False
