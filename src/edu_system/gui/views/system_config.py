"""
系统配置视图 - 连接嵌入式 FastAPI 后端 API
包含：服务管理、定时任务、存储管理、网络设置
"""

import requests
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from edu_system.gui.views.base import BaseView


class ApiWorker(QThread):
    """异步 API 调用工作线程"""

    finished = pyqtSignal(bool, dict, str)  # success, data, error_msg

    def __init__(
        self, base_url: str, method: str, path: str, data: dict = None, params: dict = None
    ):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.method = method.upper()
        self.path = path
        self.data = data
        self.params = params

    def run(self):
        try:
            url = f"{self.base_url}{self.path}"
            headers = {"Content-Type": "application/json"}

            if self.method == "GET":
                resp = requests.get(url, params=self.params, headers=headers, timeout=10)
            elif self.method == "POST":
                resp = requests.post(url, json=self.data, headers=headers, timeout=10)
            elif self.method == "PUT":
                resp = requests.put(url, json=self.data, headers=headers, timeout=10)
            elif self.method == "DELETE":
                resp = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {self.method}")

            if resp.status_code < 400:
                try:
                    data = resp.json()
                except:
                    data = {"text": resp.text}
                self.finished.emit(True, data, "")
            else:
                self.finished.emit(False, {}, f"HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            self.finished.emit(False, {}, str(e))


class SystemConfigView(BaseView):
    """系统配置视图"""

    def __init__(self, session):
        super().__init__(session)
        self.setWindowTitle("系统配置")
        self.setObjectName("systemConfigView")

        # API 基础地址（本地嵌入式服务）
        self.api_base = "http://127.0.0.1:8080"
        self.server_thread = None  # 将在主窗口中设置

        self._init_ui()
        self._load_config()

    def set_server_thread(self, server_thread):
        """设置服务器线程引用（由主窗口调用）"""
        self.server_thread = server_thread
        # 连接信号更新网络信息
        if server_thread:
            server_thread.signals.started.connect(self._on_server_started)
            server_thread.signals.stopped.connect(self._on_server_stopped)

            # 关键修复：如果服务已经在运行，立即同步界面状态
            # （因为服务可能在视图加载前就已启动，错过了 started 信号）
            if server_thread.isRunning():
                self._on_server_started(server_thread.host, server_thread._actual_port)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 标题
        title = QLabel("系统配置")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setStyleSheet("color: #1a1a2e; margin-bottom: 8px;")
        layout.addWidget(title)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            """
            QTabWidget::pane { border: 1px solid #d9d9d9; border-radius: 4px; }
            QTabBar::tab { padding: 8px 16px; margin-right: 4px; }
            QTabBar::tab:selected { background: #1890ff; color: white; }
        """
        )

        # 1. 服务管理标签页
        self._create_service_tab()

        # 2. 定时任务标签页
        self._create_scheduler_tab()

        # 3. 存储管理标签页
        self._create_storage_tab()

        # 4. 网络设置标签页
        self._create_network_tab()

        layout.addWidget(self.tabs)

        # 设置标签页最小尺寸，防止切换时界面跳动
        self.tabs.setMinimumSize(800, 550)
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("保存配置")
        self.btn_save.setStyleSheet(
            """
            QPushButton { background: #1890ff; color: white; padding: 8px 24px; 
                          border-radius: 4px; font-weight: 500; }
            QPushButton:hover { background: #40a9ff; }
        """
        )
        self.btn_save.clicked.connect(self._save_config)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    # ===== API 调用辅助方法 =====
    def _api_call(
        self,
        method: str,
        path: str,
        data: dict = None,
        params: dict = None,
        on_success=None,
        on_error=None,
    ):
        """异步调用 API"""
        worker = ApiWorker(self.api_base, method, path, data, params)
        if on_success:
            worker.finished.connect(
                lambda success, data, err: on_success(data) if success else on_error(err)
            )
        else:
            worker.finished.connect(
                lambda success, data, err: self._handle_api_result(success, data, err)
            )
        worker.start()
        return worker

    def _handle_api_result(self, success: bool, data: dict, error: str):
        """默认 API 结果处理"""
        if not success:
            QMessageBox.warning(self, "API 调用失败", error)

    def _api_call_sync(
        self, method: str, path: str, data: dict = None, params: dict = None
    ) -> tuple:
        """同步调用 API（阻塞，仅用于初始化加载）"""
        try:
            url = f"{self.api_base}{path}"
            headers = {"Content-Type": "application/json"}

            if method == "GET":
                resp = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == "POST":
                resp = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == "PUT":
                resp = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == "DELETE":
                resp = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if resp.status_code < 400:
                try:
                    return True, resp.json()
                except:
                    return True, {"text": resp.text}
            else:
                return False, f"HTTP {resp.status_code}: {resp.text}"
        except Exception as e:
            return False, str(e)

    # ===== 1. 服务管理标签页 =====
    def _create_service_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        desc = QLabel("管理各业务服务的启停、权限绑定、速率限制、访问日志查看。实时生效无需重启。")
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        layout.addWidget(desc)

        # 服务列表表格
        self.service_table = QTableWidget()
        self.service_table.setColumnCount(7)
        self.service_table.setHorizontalHeaderLabels(
            ["服务代码", "服务名称", "状态", "权限要求", "允许角色", "速率限制", "操作"]
        )
        self.service_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.service_table.setAlternatingRowColors(True)
        self.service_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.service_table)

        # 刷新按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_refresh = QPushButton("刷新服务列表")
        btn_refresh.clicked.connect(self._refresh_services)
        btn_layout.addWidget(btn_refresh)
        layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "服务管理")
        self._refresh_services()

    def _refresh_services(self):
        """刷新服务列表（同步调用）"""
        success, data = self._api_call_sync("GET", "/api/admin/scheduler/jobs")
        if not success:
            # 回退到本地注册表
            from edu_system.api.service_registry import service_registry

            services = service_registry.list_services()
        else:
            services = data

        self.service_table.setRowCount(len(services))

        for row, svc in enumerate(services):
            self.service_table.setItem(
                row, 0, QTableWidgetItem(svc.get("service_code", svc.get("id", "")))
            )
            self.service_table.setItem(row, 1, QTableWidgetItem(svc.get("name", "")))

            # 状态开关
            status_cb = QCheckBox()
            status_cb.setChecked(svc.get("enabled", True))
            status_cb.toggled.connect(
                lambda checked, code=svc.get("service_code", svc.get("id", "")): (
                    self._toggle_service(code, checked)
                )
            )
            self.service_table.setCellWidget(row, 2, status_cb)

            self.service_table.setItem(
                row, 3, QTableWidgetItem(", ".join(svc.get("required_permissions", [])))
            )
            self.service_table.setItem(
                row, 4, QTableWidgetItem(", ".join(svc.get("allowed_roles", [])))
            )
            self.service_table.setItem(
                row,
                5,
                QTableWidgetItem(str(svc.get("rate_limit", svc.get("rate_limit_window", "")))),
            )

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_logs = QPushButton("查看日志")
            btn_logs.setStyleSheet("padding: 2px 8px; font-size: 12px;")
            btn_logs.clicked.connect(
                lambda _, code=svc.get("service_code", svc.get("id", "")): self._view_service_logs(
                    code
                )
            )
            btn_layout.addWidget(btn_logs)
            self.service_table.setCellWidget(row, 6, btn_widget)

    def _toggle_service(self, service_code: str, enabled: bool):
        """切换服务启用状态"""
        self._api_call(
            "PUT",
            f"/api/admin/services/{service_code}",
            data={"enabled": enabled},
            on_success=lambda _: self._refresh_services(),
            on_error=lambda err: QMessageBox.warning(self, "失败", err),
        )

    def _view_service_logs(self, service_code: str):
        """查看服务访问日志（M5-F1：真实查询 audit_logs）"""
        success, data = self._api_call_sync(
            "GET",
            "/api/audit/logs",
            params={"service": service_code, "limit": 100},
        )
        if not success:
            QMessageBox.warning(self, "失败", str(data))
            return

        logs = data.get("logs", []) if isinstance(data, dict) else []
        dlg = QDialog(self)
        dlg.setWindowTitle(f"服务日志 — {service_code}（共 {data.get('total', len(logs))} 条）")
        dlg.resize(760, 480)
        layout = QVBoxLayout(dlg)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["时间", "方法", "路径", "状态", "耗时(ms)"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            created = (log.get("created_at") or "")[:19]
            items = [
                created,
                log.get("method", ""),
                log.get("path", ""),
                str(log.get("status", "")),
                str(log.get("duration_ms", "")),
            ]
            for col, val in enumerate(items):
                table.setItem(row, col, QTableWidgetItem(val))
        layout.addWidget(table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
        dlg.exec_()

    # ===== 2. 定时任务标签页 =====
    def _create_scheduler_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        desc = QLabel(
            "管理定时任务：统计刷新、自动锁分、自动归档、备份、审计清理。可视化增删改查、手动触发、执行历史。"
        )
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        layout.addWidget(desc)

        # 任务列表
        self.scheduler_table = QTableWidget()
        self.scheduler_table.setColumnCount(7)
        self.scheduler_table.setHorizontalHeaderLabels(
            ["任务ID", "任务名称", "触发方式", "下次运行", "状态", "上次运行", "操作"]
        )
        self.scheduler_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.scheduler_table.setAlternatingRowColors(True)
        layout.addWidget(self.scheduler_table)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("添加任务")
        btn_add.clicked.connect(self._add_scheduler_job)
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self._refresh_scheduler)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_refresh)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "定时任务")
        self._refresh_scheduler()

        # 定时刷新
        self.scheduler_timer = QTimer()
        self.scheduler_timer.timeout.connect(self._refresh_scheduler)
        self.scheduler_timer.start(30000)  # 30秒刷新

    def _refresh_scheduler(self):
        success, data = self._api_call_sync("GET", "/api/admin/scheduler/jobs")
        if not success:
            # 回退到本地调度器
            from edu_system.services.scheduler import get_scheduler

            scheduler = get_scheduler()
            jobs = scheduler.get_jobs()
        else:
            jobs = data

        self.scheduler_table.setRowCount(len(jobs))

        for row, job in enumerate(jobs):
            self.scheduler_table.setItem(row, 0, QTableWidgetItem(job.get("id", "")))
            self.scheduler_table.setItem(row, 1, QTableWidgetItem(job.get("name", "")))
            self.scheduler_table.setItem(row, 2, QTableWidgetItem(job.get("trigger", "")))
            self.scheduler_table.setItem(row, 3, QTableWidgetItem(job.get("next_run_time", "N/A")))

            status_item = QTableWidgetItem("运行中" if not job.get("paused") else "已暂停")
            if job.get("paused"):
                status_item.setBackground(Qt.yellow)
            self.scheduler_table.setItem(row, 4, status_item)

            self.scheduler_table.setItem(row, 5, QTableWidgetItem(job.get("last_run_time", "N/A")))

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)

            btn_toggle = QPushButton("暂停" if not job.get("paused") else "恢复")
            btn_toggle.setStyleSheet("padding: 2px 8px; font-size: 12px;")
            btn_toggle.clicked.connect(lambda _, jid=job.get("id", ""): self._toggle_job(jid))
            btn_layout.addWidget(btn_toggle)

            btn_trigger = QPushButton("立即执行")
            btn_trigger.setStyleSheet("padding: 2px 8px; font-size: 12px;")
            btn_trigger.clicked.connect(lambda _, jid=job.get("id", ""): self._trigger_job(jid))
            btn_layout.addWidget(btn_trigger)

            self.scheduler_table.setCellWidget(row, 6, btn_widget)

    def _add_scheduler_job(self):
        QMessageBox.information(self, "提示", "添加任务功能开发中...")

    def _toggle_job(self, job_id: str):
        action = "pause"
        self._api_call(
            "POST",
            f"/api/admin/scheduler/jobs/{job_id}/{action}",
            on_success=lambda _: self._refresh_scheduler(),
            on_error=lambda err: QMessageBox.warning(self, "失败", err),
        )

    def _trigger_job(self, job_id: str):
        self._api_call(
            "POST",
            f"/api/admin/scheduler/jobs/{job_id}/trigger",
            on_success=lambda _: self._refresh_scheduler(),
            on_error=lambda err: QMessageBox.warning(self, "失败", err),
        )

    # ===== 3. 存储管理标签页 =====
    def _create_storage_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        desc = QLabel("文件存储管理：查看存储统计、清理孤儿文件、配置存储策略。")
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        layout.addWidget(desc)

        # 统计卡片
        stats_layout = QHBoxLayout()
        self.storage_cards = {}
        for title, key in [
            ("总文件数", "total_files"),
            ("去重率", "dedup_rate_percent"),
            ("总大小", "total_size_mb"),
            ("文件类型数", "by_type"),
        ]:
            card = QFrame()
            card.setFrameStyle(QFrame.Box | QFrame.Raised)
            card.setStyleSheet("background: white; border-radius: 8px; padding: 16px;")
            card_layout = QVBoxLayout(card)
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet("color: #666; font-size: 14px;")
            value_lbl = QLabel("加载中...")
            value_lbl.setObjectName(f"card_{key}")
            value_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #1890ff;")
            card_layout.addWidget(title_lbl)
            card_layout.addWidget(value_lbl)
            self.storage_cards[key] = value_lbl
            stats_layout.addWidget(card)
        layout.addLayout(stats_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("刷新统计")
        btn_refresh.clicked.connect(self._refresh_storage_stats)
        btn_cleanup = QPushButton("清理孤儿文件")
        btn_cleanup.setStyleSheet("background: #faad14; color: white;")
        btn_cleanup.clicked.connect(self._cleanup_orphans)
        btn_layout.addWidget(btn_refresh)
        btn_layout.addWidget(btn_cleanup)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 按类型统计表格
        self.storage_type_table = QTableWidget()
        self.storage_type_table.setColumnCount(4)
        self.storage_type_table.setHorizontalHeaderLabels(
            ["文件类型", "数量", "大小(MB)", "去重率"]
        )
        self.storage_type_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.storage_type_table)

        self.tabs.addTab(tab, "存储管理")
        self._refresh_storage_stats()

    def _refresh_storage_stats(self):
        success, data = self._api_call_sync("GET", "/api/admin/storage/stats")
        if not success:
            # 回退到本地存储服务
            from edu_system.services.storage import get_storage_service

            storage = get_storage_service()
            stats = storage.get_storage_stats()
        else:
            stats = data

        # 更新卡片
        self.storage_cards["total_files"].setText(str(stats.get("total_files", 0)))
        self.storage_cards["dedup_rate_percent"].setText(f"{stats.get('dedup_rate_percent', 0)}%")
        self.storage_cards["total_size_mb"].setText(f"{stats.get('total_size_mb', 0)} MB")
        self.storage_cards["by_type"].setText(str(len(stats.get("by_type", {}))))

        # 更新表格
        by_type = stats.get("by_type", {})
        self.storage_type_table.setRowCount(len(by_type))
        for row, (ftype, info) in enumerate(by_type.items()):
            self.storage_type_table.setItem(row, 0, QTableWidgetItem(ftype))
            self.storage_type_table.setItem(row, 1, QTableWidgetItem(str(info.get("count", 0))))
            self.storage_type_table.setItem(row, 2, QTableWidgetItem(str(info.get("size_mb", 0))))
            self.storage_type_table.setItem(row, 3, QTableWidgetItem("N/A"))

    def _cleanup_orphans(self):
        self._api_call(
            "POST",
            "/api/admin/storage/cleanup",
            on_success=lambda data: (
                QMessageBox.information(self, "完成", f"已清理 {data.get('count', 0)} 个孤儿文件"),
                self._refresh_storage_stats(),
            ),
            on_error=lambda err: QMessageBox.warning(self, "失败", err),
        )

    # ===== 4. 网络设置标签页 =====
    def _create_network_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # 服务地址显示
        group = QGroupBox("服务地址")
        group_layout = QFormLayout(group)

        self.lbl_lan_url = QLabel("等待服务启动...")
        self.lbl_lan_url.setStyleSheet("font-family: monospace; font-size: 14px; color: #1890ff;")
        self.lbl_lan_url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        group_layout.addRow("局域网访问地址:", self.lbl_lan_url)

        self.lbl_local_url = QLabel("http://127.0.0.1:8080")
        self.lbl_local_url.setStyleSheet("font-family: monospace; font-size: 14px;")
        self.lbl_local_url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        group_layout.addRow("本地访问地址:", self.lbl_local_url)

        # 二维码
        self.lbl_qr = QLabel()
        self.lbl_qr.setAlignment(Qt.AlignCenter)
        self.lbl_qr.setMinimumSize(200, 200)
        group_layout.addRow("二维码:", self.lbl_qr)

        layout.addWidget(group)

        # 端口设置
        port_group = QGroupBox("端口设置")
        port_layout = QFormLayout(port_group)

        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(8080)
        self.spin_port.valueChanged.connect(self._on_port_changed)
        port_layout.addRow("服务端口:", self.spin_port)

        self.chk_auto_port = QCheckBox("端口冲突时自动重试")
        self.chk_auto_port.setChecked(True)
        port_layout.addRow("", self.chk_auto_port)

        layout.addWidget(port_group)

        # 服务开关
        service_group = QGroupBox("服务控制")
        svc_layout = QHBoxLayout(service_group)

        self.btn_start = QPushButton("启动服务")
        self.btn_start.setStyleSheet("background: #52c41a; color: white; padding: 8px 24px;")
        self.btn_start.clicked.connect(self._start_service)

        self.btn_stop = QPushButton("停止服务")
        self.btn_stop.setStyleSheet("background: #ff4d4f; color: white; padding: 8px 24px;")
        self.btn_stop.clicked.connect(self._stop_service)
        self.btn_stop.setEnabled(False)

        self.btn_restart = QPushButton("重启服务")
        self.btn_restart.clicked.connect(self._restart_service)

        svc_layout.addWidget(self.btn_start)
        svc_layout.addWidget(self.btn_stop)
        svc_layout.addWidget(self.btn_restart)

        layout.addWidget(service_group)

        # 状态显示
        self.lbl_service_status = QLabel("服务状态: 未启动")
        self.lbl_service_status.setStyleSheet("color: #ff4d4f; font-weight: bold;")
        layout.addWidget(self.lbl_service_status)

        self.tabs.addTab(tab, "网络设置")

        # 定时更新二维码和状态
        self.network_timer = QTimer()
        self.network_timer.timeout.connect(self._update_network_info)
        self.network_timer.start(5000)

    def _on_port_changed(self, value: int):
        self.lbl_local_url.setText(f"http://127.0.0.1:{value}")
        self.api_base = f"http://127.0.0.1:{value}"

    def _update_network_info(self):
        if self.server_thread:
            status = self.server_thread.get_status()
            if status.get("running"):
                local_ip = self.server_thread._get_local_ip()
                port = status.get("port", 8080)
                url = f"http://{local_ip}:{port}"
                self.lbl_lan_url.setText(url)
                self._generate_qr_code(url)
                self.lbl_service_status.setText(f"服务状态: 运行中 (http://{local_ip}:{port})")
                self.lbl_service_status.setStyleSheet("color: #52c41a; font-weight: bold;")
                self.btn_start.setEnabled(False)
                self.btn_stop.setEnabled(True)
            else:
                self.lbl_service_status.setText("服务状态: 未启动")
                self.lbl_service_status.setStyleSheet("color: #ff4d4f; font-weight: bold;")
                self.btn_start.setEnabled(True)
                self.btn_stop.setEnabled(False)

    def _on_server_started(self, host: str, port: int):
        local_ip = self.server_thread._get_local_ip() if self.server_thread else "127.0.0.1"
        url = f"http://{local_ip}:{port}"
        self.lbl_lan_url.setText(url)
        self._generate_qr_code(url)
        self.lbl_service_status.setText(f"服务状态: 运行中 ({url})")
        self.lbl_service_status.setStyleSheet("color: #52c41a; font-weight: bold;")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def _on_server_stopped(self):
        self.lbl_lan_url.setText("服务未运行")
        self.lbl_qr.clear()
        self.lbl_service_status.setText("服务状态: 未启动")
        self.lbl_service_status.setStyleSheet("color: #ff4d4f; font-weight: bold;")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _generate_qr_code(self, text: str):
        """生成二维码"""
        try:
            import qrcode

            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(text)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # 转为 QPixmap
            from io import BytesIO

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            self.lbl_qr.setPixmap(
                pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        except ImportError:
            self.lbl_qr.setText("安装 qrcode 库以显示二维码")
        except Exception as e:
            self.lbl_qr.setText(f"二维码生成失败: {e}")

    def _start_service(self):
        """启动服务（若线程已结束则新建实例，QThread 不能复用已结束的线程）"""
        from edu_system.gui.server_thread import create_server_thread

        if self.server_thread is None:
            self.server_thread = create_server_thread(
                host="0.0.0.0",
                port=self.spin_port.value(),
                app_module="edu_system.api.main:app",
            )
            self.server_thread.signals.started.connect(self._on_server_started)
            self.server_thread.signals.stopped.connect(self._on_server_stopped)
            self.server_thread.start()
            return

        if self.server_thread.isRunning():
            return  # 已在运行

        # 线程已结束（可能因端口冲突等失败退出）→ 必须新建实例
        self.server_thread = create_server_thread(
            host="0.0.0.0",
            port=self.spin_port.value(),
            app_module="edu_system.api.main:app",
        )
        self.server_thread.signals.started.connect(self._on_server_started)
        self.server_thread.signals.stopped.connect(self._on_server_stopped)
        self.server_thread.start()

    def _stop_service(self):
        if self.server_thread and self.server_thread.isRunning():
            self.server_thread.stop()

    def _restart_service(self):
        if self.server_thread:
            self.server_thread.stop()
            QTimer.singleShot(1000, self._start_service)

    def _save_config(self):
        QMessageBox.information(self, "提示", "配置保存功能开发中...")

    def _load_config(self):
        pass
