"""
MonitorView — 系统监控视图（M3：CPU/内存/磁盘/底座统计）

桌面端通过 API 拉取（与 Web 同源 /api/monitor）。
"""

from __future__ import annotations

import json

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from edu_system.gui.theme import font


def _btn(txt, color):
    from edu_system.gui.components import btn

    return btn(txt, color)

class MonitorView(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self._build_ui()
        self.refresh()

    def refresh(self):
        self._load()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(6)

        tb = QHBoxLayout()
        tb.addWidget(QLabel("系统监控"))
        tb.addStretch()
        b = _btn("刷新", "#3498DB")
        b.clicked.connect(self._load)
        tb.addWidget(b)
        lay.addLayout(tb)

        # CPU
        self._cpu_bar = QProgressBar()
        self._cpu_bar.setMaximum(100)
        self._cpu_lbl = QLabel("CPU: -")
        lay.addWidget(QLabel("CPU 使用率"))
        lay.addWidget(self._cpu_bar)
        lay.addWidget(self._cpu_lbl)
        # 内存
        self._mem_bar = QProgressBar()
        self._mem_bar.setMaximum(100)
        self._mem_lbl = QLabel("内存: -")
        lay.addWidget(QLabel("内存使用率"))
        lay.addWidget(self._mem_bar)
        lay.addWidget(self._mem_lbl)
        # 磁盘
        self._disk_bar = QProgressBar()
        self._disk_bar.setMaximum(100)
        self._disk_lbl = QLabel("磁盘: -")
        lay.addWidget(QLabel("磁盘使用率"))
        lay.addWidget(self._disk_bar)
        lay.addWidget(self._disk_lbl)

        # 系统信息
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["项目", "值"])
        self._info.setFont(font(9))
        self._info.verticalHeader().hide()
        self._info.horizontalHeader().setStretchLastSection(True)
        self._info.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self._info)
        lay.addStretch()

    def _load(self):
        try:
            import urllib.request

            req = urllib.request.Request("http://127.0.0.1:8081/api/monitor/server")
            with urllib.request.urlopen(req, timeout=5) as r:
                d = json.loads(r.read())
            self._cpu_bar.setValue(int(d["cpu"]["usage_percent"]))
            self._mem_bar.setValue(int(d["memory"]["usage_percent"]))
            self._disk_bar.setValue(int(d["disk"]["usage_percent"]))
            self._cpu_lbl.setText(
                f"CPU: {d['cpu']['usage_percent']}% ({d['cpu']['cores']}核 - {d['cpu']['model']})"
            )
            self._mem_lbl.setText(f"内存: {d['memory']['usage_percent']}%")
            self._disk_lbl.setText(f"磁盘: {d['disk']['usage_percent']}%")
            rows = [
                ("主机名", d["hostname"]),
                ("操作系统", d["os"]),
                ("进程数", str(d["processes"])),
            ]
            self._info.setRowCount(len(rows))
            for i, (k, v) in enumerate(rows):
                self._info.setItem(i, 0, QTableWidgetItem(k))
                self._info.setItem(i, 1, QTableWidgetItem(v))
        except Exception as e:
            self._cpu_lbl.setText(f"监控加载失败: {e}")
