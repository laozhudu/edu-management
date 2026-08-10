"""
系统配置视图 - 连接嵌入式 FastAPI 后端 API
包含：服务管理、定时任务、存储管理、网络设置
"""

import requests
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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

from edu_system.gui.theme import C
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
        title.setStyleSheet(f"color: {C['antd_title']}; margin-bottom: 8px;")
        layout.addWidget(title)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{ border: 1px solid {C["antd_border"]}; border-radius: 4px; }}
            QTabBar::tab {{ padding: 8px 16px; margin-right: 4px; }}
            QTabBar::tab:selected {{ background: {C["antd_blue"]}; color: white; }}
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

        # 5. 界面样式标签页（v3.7.0：菜单/字体/登录框零代码配置）
        self._create_appearance_tab()

        # 6. 操作审计标签页（v3.7.0：业务操作审计查询）
        self._create_audit_tab()

        layout.addWidget(self.tabs)

        # 设置标签页最小尺寸，防止切换时界面跳动
        self.tabs.setMinimumSize(800, 550)
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("保存配置")
        self.btn_save.setStyleSheet(
            f"""
            QPushButton {{ background: {C["antd_blue"]}; color: white; padding: 8px 24px; 
                          border-radius: 4px; font-weight: 500; }}
            QPushButton:hover {{ background: {C["antd_blue_hover"]}; }}
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
            value_lbl.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {C['antd_blue']};")
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
        btn_cleanup.setStyleSheet(f"background: {C['antd_warn']}; color: white;")
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
        self.lbl_lan_url.setStyleSheet(
            f"font-family: monospace; font-size: 14px; color: {C['antd_blue']};"
        )
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
        self.btn_start.setStyleSheet(
            f"background: {C['antd_green']}; color: white; padding: 8px 24px;"
        )
        self.btn_start.clicked.connect(self._start_service)

        self.btn_stop = QPushButton("停止服务")
        self.btn_stop.setStyleSheet(
            f"background: {C['antd_red']}; color: white; padding: 8px 24px;"
        )
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
        self.lbl_service_status.setStyleSheet(f"color: {C['antd_red']}; font-weight: bold;")
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
                self.lbl_service_status.setStyleSheet(
                    f"color: {C['antd_green']}; font-weight: bold;"
                )
                self.btn_start.setEnabled(False)
                self.btn_stop.setEnabled(True)
            else:
                self.lbl_service_status.setText("服务状态: 未启动")
                self.lbl_service_status.setStyleSheet(f"color: {C['antd_red']}; font-weight: bold;")
                self.btn_start.setEnabled(True)
                self.btn_stop.setEnabled(False)

    def _on_server_started(self, host: str, port: int):
        local_ip = self.server_thread._get_local_ip() if self.server_thread else "127.0.0.1"
        url = f"http://{local_ip}:{port}"
        self.lbl_lan_url.setText(url)
        self._generate_qr_code(url)
        self.lbl_service_status.setText(f"服务状态: 运行中 ({url})")
        self.lbl_service_status.setStyleSheet(f"color: {C['antd_green']}; font-weight: bold;")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def _on_server_stopped(self):
        self.lbl_lan_url.setText("服务未运行")
        self.lbl_qr.clear()
        self.lbl_service_status.setText("服务状态: 未启动")
        self.lbl_service_status.setStyleSheet(f"color: {C['antd_red']}; font-weight: bold;")
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

    # ═══════════════════════════════════
    #  Tab 5: 界面样式（v3.7.0 可配置化）
    # ═══════════════════════════════════

    def _create_appearance_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        info = QLabel("界面样式零代码配置：修改后点击「保存样式」立即生效（双端同步）。")
        info.setFont(QFont("Microsoft YaHei", 9))
        info.setStyleSheet(f"color: {C['text_light']};")
        lay.addWidget(info)

        # 外观主题
        theme_grp = QGroupBox("外观主题")
        theme_grp.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        tg = QGridLayout(theme_grp)
        tg.setSpacing(8)

        tg.addWidget(QLabel("强调色:"), 0, 0)
        self._cfg_accent = QLineEdit()
        self._cfg_accent.setFont(QFont("Microsoft YaHei", 9))
        tg.addWidget(self._cfg_accent, 0, 1)

        tg.addWidget(QLabel("侧栏背景:"), 0, 2)
        self._cfg_sidebar = QLineEdit()
        self._cfg_sidebar.setFont(QFont("Microsoft YaHei", 9))
        tg.addWidget(self._cfg_sidebar, 0, 3)

        tg.addWidget(QLabel("内容背景:"), 1, 0)
        self._cfg_content = QLineEdit()
        self._cfg_content.setFont(QFont("Microsoft YaHei", 9))
        tg.addWidget(self._cfg_content, 1, 1)

        tg.addWidget(QLabel("密度:"), 1, 2)
        self._cfg_density = QComboBox()
        self._cfg_density.addItems(["compact", "comfortable"])
        self._cfg_density.setFont(QFont("Microsoft YaHei", 9))
        tg.addWidget(self._cfg_density, 1, 3)
        lay.addWidget(theme_grp)

        # 登录框
        login_grp = QGroupBox("登录框")
        login_grp.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        lg = QGridLayout(login_grp)
        lg.setSpacing(8)
        lg.addWidget(QLabel("窗口宽:"), 0, 0)
        self._cfg_lg_width = QSpinBox()
        self._cfg_lg_width.setRange(300, 600)
        self._cfg_lg_width.setFont(QFont("Microsoft YaHei", 9))
        lg.addWidget(self._cfg_lg_width, 0, 1)
        lg.addWidget(QLabel("窗口高:"), 0, 2)
        self._cfg_lg_height = QSpinBox()
        self._cfg_lg_height.setRange(300, 600)
        self._cfg_lg_height.setFont(QFont("Microsoft YaHei", 9))
        lg.addWidget(self._cfg_lg_height, 0, 3)
        lg.addWidget(QLabel("标题字号:"), 1, 0)
        self._cfg_lg_title = QSpinBox()
        self._cfg_lg_title.setRange(10, 24)
        self._cfg_lg_title.setFont(QFont("Microsoft YaHei", 9))
        lg.addWidget(self._cfg_lg_title, 1, 1)
        lg.addWidget(QLabel("副标题字号:"), 1, 2)
        self._cfg_lg_sub = QSpinBox()
        self._cfg_lg_sub.setRange(8, 16)
        self._cfg_lg_sub.setFont(QFont("Microsoft YaHei", 9))
        lg.addWidget(self._cfg_lg_sub, 1, 3)
        lg.addWidget(QLabel("输入框圆角:"), 2, 0)
        self._cfg_lg_radius = QSpinBox()
        self._cfg_lg_radius.setRange(0, 20)
        self._cfg_lg_radius.setFont(QFont("Microsoft YaHei", 9))
        lg.addWidget(self._cfg_lg_radius, 2, 1)
        lg.addWidget(QLabel("品牌区:"), 2, 2)
        self._cfg_lg_brand = QCheckBox("启用品牌区")
        self._cfg_lg_brand.setFont(QFont("Microsoft YaHei", 9))
        lg.addWidget(self._cfg_lg_brand, 2, 3)
        lay.addWidget(login_grp)

        # 顶部栏
        top_grp = QGroupBox("顶部栏")
        top_grp.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        tl = QHBoxLayout(top_grp)
        tl.setSpacing(16)
        self._cfg_tb_sem = QCheckBox("学期切换")
        self._cfg_tb_sem.setFont(QFont("Microsoft YaHei", 9))
        tl.addWidget(self._cfg_tb_sem)
        self._cfg_tb_search = QCheckBox("搜索框")
        self._cfg_tb_search.setFont(QFont("Microsoft YaHei", 9))
        tl.addWidget(self._cfg_tb_search)
        self._cfg_tb_palette = QCheckBox("命令面板")
        self._cfg_tb_palette.setFont(QFont("Microsoft YaHei", 9))
        tl.addWidget(self._cfg_tb_palette)
        tl.addStretch()
        lay.addWidget(top_grp)

        # 保存按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        b_save = QPushButton("保存样式")
        b_save.setStyleSheet(
            f"QPushButton {{ background:{C['antd_blue']}; color:white; padding:6px 20px; "
            f"border-radius:4px; font-weight:500; }}"
        )
        b_save.clicked.connect(self._save_appearance)
        btn_row.addWidget(b_save)
        lay.addLayout(btn_row)
        lay.addStretch()

        self.tabs.addTab(tab, "界面样式")

    def _load_appearance_values(self):
        """从当前配置填充样式表单（_load_config 中调用）"""
        try:
            from edu_system.config.ui_config import get_config

            cfg = get_config()
            self._cfg_accent.setText(getattr(cfg.theme, "accent_color", ""))
            self._cfg_sidebar.setText(getattr(cfg.theme, "sidebar_bg", ""))
            self._cfg_content.setText(getattr(cfg.theme, "content_bg", ""))
            idx = self._cfg_density.findText(getattr(cfg.theme, "density", "compact"))
            self._cfg_density.setCurrentIndex(max(idx, 0))
            self._cfg_lg_width.setValue(getattr(cfg.login, "window_width", 400))
            self._cfg_lg_height.setValue(getattr(cfg.login, "window_height", 400))
            self._cfg_lg_title.setValue(getattr(cfg.login, "brand_title_font_size", 16))
            self._cfg_lg_sub.setValue(getattr(cfg.login, "brand_subtitle_font_size", 10))
            self._cfg_lg_radius.setValue(getattr(cfg.login, "input_radius", 6))
            self._cfg_lg_brand.setChecked(getattr(cfg.login, "brand_enabled", True))
            self._cfg_tb_sem.setChecked(getattr(cfg.topbar, "show_semester_switcher", True))
            self._cfg_tb_search.setChecked(getattr(cfg.topbar, "show_search", True))
            self._cfg_tb_palette.setChecked(getattr(cfg.topbar, "show_command_palette", True))
        except Exception as e:
            print(f"[样式] 加载配置失败: {e}")

    def _save_appearance(self):
        """保存界面样式（调 /api/config/save-ui 写回 + reload）"""
        import json
        import urllib.request

        payload = {
            "theme": {
                "accent_color": self._cfg_accent.text().strip(),
                "sidebar_bg": self._cfg_sidebar.text().strip(),
                "content_bg": self._cfg_content.text().strip(),
                "density": self._cfg_density.currentText(),
            },
            "login": {
                "window_width": self._cfg_lg_width.value(),
                "window_height": self._cfg_lg_height.value(),
                "brand_title_font_size": self._cfg_lg_title.value(),
                "brand_subtitle_font_size": self._cfg_lg_sub.value(),
                "input_radius": self._cfg_lg_radius.value(),
                "brand_enabled": self._cfg_lg_brand.isChecked(),
            },
            "topbar": {
                "show_semester_switcher": self._cfg_tb_sem.isChecked(),
                "show_search": self._cfg_tb_search.isChecked(),
                "show_command_palette": self._cfg_tb_palette.isChecked(),
            },
        }
        try:
            req = urllib.request.Request(
                f"{self.api_base}/api/config/save-ui",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data.get("success"):
                QMessageBox.information(self, "完成", data.get("message", "样式已保存并生效"))
                # 同步最新配置到表单
                from edu_system.config.ui_config import reload_config

                reload_config()
            else:
                QMessageBox.warning(self, "提示", str(data))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {e}")

    # ═══════════════════════════════════
    #  Tab 6: 操作审计（v3.7.0）
    # ═══════════════════════════════════

    def _create_audit_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        # 工具栏：过滤 + 刷新
        tb = QHBoxLayout()
        tb.setSpacing(8)
        tb.addWidget(QLabel("表:"))
        self._audit_table_cb = QComboBox()
        self._audit_table_cb.addItems(
            ["全部", "students", "teachers", "classes", "exams", "scores", "semesters", "subjects"]
        )
        self._audit_table_cb.setFont(QFont("Microsoft YaHei", 9))
        tb.addWidget(self._audit_table_cb)
        tb.addWidget(QLabel("操作:"))
        self._audit_action_cb = QComboBox()
        self._audit_action_cb.addItems(["全部", "INSERT", "UPDATE", "DELETE"])
        self._audit_action_cb.setFont(QFont("Microsoft YaHei", 9))
        tb.addWidget(self._audit_action_cb)
        tb.addWidget(QLabel("操作者:"))
        self._audit_operator = QLineEdit()
        self._audit_operator.setFont(QFont("Microsoft YaHei", 9))
        self._audit_operator.setFixedWidth(120)
        tb.addWidget(self._audit_operator)
        tb.addStretch()
        b_refresh = QPushButton("查询")
        b_refresh.setStyleSheet(
            f"QPushButton {{ background:{C['antd_blue']}; color:white; padding:4px 16px; "
            f"border-radius:4px; }}"
        )
        b_refresh.clicked.connect(self._load_audit_ops)
        tb.addWidget(b_refresh)
        lay.addLayout(tb)

        # 审计日志表
        self._audit_table = QTableWidget(0, 7)
        self._audit_table.setHorizontalHeaderLabels(
            ["时间", "操作者", "表", "记录ID", "动作", "IP", "变更详情"]
        )
        self._audit_table.setFont(QFont("Microsoft YaHei", 9))
        self._audit_table.verticalHeader().hide()
        self._audit_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._audit_table.horizontalHeader().setStretchLastSection(True)
        self._audit_table.setStyleSheet(
            f"QTableWidget {{ font-size:9pt; border:1px solid {C['table_border']}; background:white; }}"
        )
        lay.addWidget(self._audit_table)

        self.tabs.addTab(tab, "操作审计")
        self._load_audit_ops()

    def _load_audit_ops(self):
        """查询业务操作审计（/api/audit/operations）"""
        import json
        import urllib.parse
        import urllib.request

        params = {}
        table = self._audit_table_cb.currentText()
        if table != "全部":
            params["table_name"] = table
        action = self._audit_action_cb.currentText()
        if action != "全部":
            params["action"] = action
        if self._audit_operator.text().strip():
            params["operator"] = self._audit_operator.text().strip()

        try:
            qs = urllib.parse.urlencode(params)
            url = f"{self.api_base}/api/audit/operations"
            if qs:
                url += "?" + qs
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            items = data.get("items", [])
            self._audit_table.setRowCount(len(items))
            _ACTION_CN = {"INSERT": "新增", "UPDATE": "修改", "DELETE": "删除"}
            for i, it in enumerate(items):
                self._audit_table.setItem(
                    i, 0, QTableWidgetItem(str(it.get("created_at", ""))[:19])
                )
                self._audit_table.setItem(i, 1, QTableWidgetItem(str(it.get("operator", ""))))
                self._audit_table.setItem(i, 2, QTableWidgetItem(str(it.get("table_name", ""))))
                self._audit_table.setItem(i, 3, QTableWidgetItem(str(it.get("record_id", ""))))
                act = it.get("action", "")
                self._audit_table.setItem(i, 4, QTableWidgetItem(_ACTION_CN.get(act, act)))
                self._audit_table.setItem(i, 5, QTableWidgetItem(str(it.get("ip") or "")))
                nv = it.get("new_values") or {}
                if isinstance(nv, dict):
                    changed = ",".join(f"{k}={v}" for k, v in list(nv.items())[:5])
                else:
                    changed = str(nv)[:120]
                self._audit_table.setItem(i, 6, QTableWidgetItem(changed))
        except Exception as e:
            print(f"[审计] 查询失败: {e}")

    def _load_config(self):
        self._load_appearance_values()
