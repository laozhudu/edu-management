"""
GUI 视图 — 数据维护 (M5-F1)
功能：备份/还原、数据清理、审计日志查看、数据库维护
"""

import threading
import os
import shutil
from pathlib import Path
from datetime import datetime

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from edu_system.gui.theme import C, font
from edu_system.gui.views.base import BaseView
from edu_system.database import get_session


def _btn(txt, color, w=None):
    b = QPushButton(txt)
    b.setStyleSheet(
        f"""QPushButton {{ background: {color}; color: white; border: none;
        border-radius: 3px; padding: 6px 12px; font-size: 9pt; }}
        QPushButton:hover {{ background: #34495E; }}"""
    )
    b.setCursor(Qt.PointingHandCursor)
    b.setMinimumHeight(28)
    if w:
        b.setFixedWidth(w)
    return b


class BackupWorker(QThread):
    """备份工作线程"""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int, str)

    def __init__(self, backup_type: str, target_path: str):
        super().__init__()
        self.backup_type = backup_type  # "full" / "incremental"
        self.target_path = target_path

    def run(self):
        try:
            self.progress.emit(10, "准备备份...")
            
            # 这里实现实际备份逻辑
            # 简化版：复制数据库文件
            import shutil
            from edu_system.config import settings
            
            db_path = settings.DATABASE_URL.replace("sqlite:///", "")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{self.backup_type}_{timestamp}.db"
            backup_full_path = os.path.join(self.target_path, backup_name)
            
            self.progress.emit(50, "正在复制数据库...")
            shutil.copy2(db_path, backup_full_path)
            
            self.progress.emit(100, "备份完成")
            self.finished.emit(True, backup_full_path)
        except Exception as e:
            self.finished.emit(False, str(e))


class RestoreWorker(QThread):
    """还原工作线程"""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int, str)

    def __init__(self, backup_file: str):
        super().__init__()
        self.backup_file = backup_file

    def run(self):
        try:
            self.progress.emit(10, "准备还原...")
            
            import shutil
            from edu_system.config import settings
            
            db_path = settings.DATABASE_URL.replace("sqlite:///", "")
            
            self.progress.emit(50, "正在还原数据库...")
            shutil.copy2(self.backup_file, db_path)
            
            self.progress.emit(100, "还原完成")
            self.finished.emit(True, "还原成功，请重启应用")
        except Exception as e:
            self.finished.emit(False, str(e))


class DataMaintenanceView(QWidget):
    """数据维护视图"""

    def __init__(self, session):
        super().__init__()
        self.session = session
        self._build_ui()

    def _build_ui(self):
        if self.layout():
            QWidget().setLayout(self.layout())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 标题
        title = QLabel("数据维护")
        title.setFont(font(16, True))
        title.setStyleSheet("color: #1a1a2e; margin-bottom: 8px;")
        layout.addWidget(title)

        # 标签页
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: 备份/还原
        self._create_backup_tab()
        
        # Tab 2: 数据清理
        self._create_cleanup_tab()
        
        # Tab 3: 审计日志
        self._create_audit_tab()

        # Tab 4: 数据库维护
        self._create_db_maintenance_tab()

    def _create_backup_tab(self):
        """备份/还原标签页"""
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(12)

        # 备份区域
        grp_backup = QGroupBox("数据库备份")
        grp_backup.setFont(font(10, True))
        gbl = QVBoxLayout(grp_backup)
        gbl.setSpacing(8)

        # 备份类型选择
        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        type_row.addWidget(QLabel("备份类型:"))
        
        self.backup_type_group = QButtonGroup()
        self.rb_full = QRadioButton("完整备份 (包含所有数据)")
        self.rb_full.setChecked(True)
        self.rb_inc = QRadioButton("增量备份 (仅变更数据)")
        self.backup_type_group.addButton(self.rb_full)
        self.backup_type_group.addButton(self.rb_inc)
        type_row.addWidget(self.rb_full)
        type_row.addWidget(self.rb_inc)
        type_row.addStretch()
        gbl.addLayout(type_row)

        # 目标路径
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        path_row.addWidget(QLabel("保存位置:"))
        self.backup_path_edit = QLineEdit()
        self.backup_path_edit.setPlaceholderText("选择备份保存目录...")
        self.backup_path_edit.setReadOnly(True)
        self.backup_path_edit.setText(str(Path.home() / "edu_management_backups"))
        path_row.addWidget(self.backup_path_edit)
        btn_browse = QPushButton("浏览...")
        btn_browse.setStyleSheet("padding: 4px 12px; font-size: 9pt;")
        btn_browse.clicked.connect(self._browse_backup_path)
        path_row.addWidget(btn_browse)
        gbl.addLayout(path_row)

        # 执行备份按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_backup = QPushButton("开始备份")
        btn_backup.setStyleSheet(
            f"background: {C['accent_green']}; color: white; "
            "border: none; border-radius: 4px; padding: 8px 24px; font-weight: bold;"
        )
        btn_backup.setCursor(Qt.PointingHandCursor)
        btn_backup.clicked.connect(self._do_backup)
        btn_row.addWidget(btn_backup)
        btn_row.addStretch()
        gbl.addLayout(btn_row)

        # 进度条
        self.backup_progress = QProgressBar()
        self.backup_progress.setVisible(False)
        self.backup_progress.setStyleSheet("height: 20px;")
        gbl.addWidget(self.backup_progress)
        self.backup_status = QLabel("")
        self.backup_status.setStyleSheet("color: #666; font-size: 9pt;")
        gbl.addWidget(self.backup_status)

        l.addWidget(grp_backup)

        # 还原区域
        grp_restore = QGroupBox("数据库还原")
        grp_restore.setFont(font(10, True))
        grl = QVBoxLayout(grp_restore)
        grl.setSpacing(8)

        # 选择备份文件
        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        file_row.addWidget(QLabel("备份文件:"))
        self.restore_file_edit = QLineEdit()
        self.restore_file_edit.setPlaceholderText("选择要还原的备份文件 (.db)...")
        self.restore_file_edit.setReadOnly(True)
        file_row.addWidget(self.restore_file_edit)
        btn_browse_restore = QPushButton("浏览...")
        btn_browse_restore.setStyleSheet("padding: 4px 12px; font-size: 9pt;")
        btn_browse_restore.clicked.connect(self._browse_restore_file)
        file_row.addWidget(btn_browse_restore)
        grl.addLayout(file_row)

        # 执行还原按钮
        btn_restore_row = QHBoxLayout()
        btn_restore_row.setSpacing(8)
        btn_restore = QPushButton("执行还原")
        btn_restore.setStyleSheet(
            f"background: {C['accent_orange']}; color: white; "
            "border: none; border-radius: 4px; padding: 8px 24px; font-weight: bold;"
        )
        btn_restore.setCursor(Qt.PointingHandCursor)
        btn_restore.clicked.connect(self._do_restore)
        btn_restore_row.addWidget(btn_restore)
        btn_restore_row.addStretch()
        grl.addLayout(btn_restore_row)

        # 进度条
        self.restore_progress = QProgressBar()
        self.restore_progress.setVisible(False)
        self.restore_progress.setStyleSheet("height: 20px;")
        grl.addWidget(self.restore_progress)
        self.restore_status = QLabel("")
        self.restore_status.setStyleSheet("color: #666; font-size: 9pt;")
        grl.addWidget(self.restore_status)

        l.addWidget(grp_restore)
        l.addStretch()

        # 添加到标签页
        from PyQt5.QtWidgets import QLineEdit
        from edu_system.gui.theme import C, font
        
        self.backup_path_edit = QLineEdit()
        self.restore_file_edit = QLineEdit()
        
        self.tabs.addTab(tab, "备份/还原")

    def _browse_backup_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择备份保存目录", self.backup_path_edit.text())
        if path:
            self.backup_path_edit.setText(path)

    def _browse_restore_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择备份文件", "", "数据库文件 (*.db *.sqlite *.sqlite3)")
        if path:
            self.restore_file_edit.setText(path)

    def _do_backup(self):
        backup_type = "full" if self.rb_full.isChecked() else "incremental"
        target_path = self.backup_path_edit.text().strip()
        if not target_path:
            QMessageBox.warning(self, "提示", "请选择备份保存目录")
            return
        
        Path(target_path).mkdir(parents=True, exist_ok=True)
        
        self.backup_progress.setVisible(True)
        self.backup_progress.setValue(0)
        self.backup_status.setText("正在备份...")
        
        self.backup_worker = BackupWorker(backup_type, target_path)
        self.backup_worker.progress.connect(self._on_backup_progress)
        self.backup_worker.finished.connect(self._on_backup_finished)
        self.backup_worker.start()

    def _on_backup_progress(self, value: int, msg: str):
        self.backup_progress.setValue(value)
        self.backup_status.setText(msg)

    def _on_backup_finished(self, success: bool, msg: str):
        self.backup_progress.setVisible(False)
        if success:
            self.backup_status.setText(f"✅ 备份成功: {msg}")
            QMessageBox.information(self, "完成", f"备份成功完成！\n文件: {msg}")
        else:
            self.backup_status.setText(f"❌ 备份失败: {msg}")
            QMessageBox.warning(self, "失败", f"备份失败: {msg}")

    def _do_restore(self):
        backup_file = self.restore_file_edit.text().strip()
        if not backup_file or not os.path.exists(backup_file):
            QMessageBox.warning(self, "提示", "请选择有效的备份文件")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认还原",
            "⚠️ 警告：还原将覆盖当前所有数据，且不可撤销！\n建议先做一次当前数据的备份。\n\n确定要继续还原吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        self.restore_progress.setVisible(True)
        self.restore_progress.setValue(0)
        self.restore_status.setText("正在还原...")
        
        self.restore_worker = RestoreWorker(self.restore_file_edit.text())
        self.restore_worker.progress.connect(self._on_restore_progress)
        self.restore_worker.finished.connect(self._on_restore_finished)
        self.restore_worker.start()

    def _on_restore_progress(self, value: int, msg: str):
        self.restore_progress.setValue(value)
        self.restore_status.setText(msg)

    def _on_restore_finished(self, success: bool, msg: str):
        self.restore_progress.setVisible(False)
        if success:
            self.restore_status.setText(f"✅ {msg}")
            QMessageBox.information(self, "完成", f"{msg}\n\n请重启应用以使更改生效。")
        else:
            self.restore_status.setText(f"❌ 还原失败: {msg}")
            QMessageBox.warning(self, "失败", f"还原失败: {msg}")

    # ===== Tab 2: 数据清理 =====
    def _create_cleanup_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(12)

        grp = QGroupBox("数据清理")
        grp.setFont(font(10, True))
        gl = QVBoxLayout(grp)
        gl.setSpacing(12)

        # 清理选项
        self.chk_orphans = QCheckBox("清理孤儿文件 (storage中无数据库引用的文件)")
        self.chk_orphans.setChecked(True)
        gl.addWidget(self.chk_orphans)

        self.chk_audit = QCheckBox("清理旧审计日志 (保留最近 N 个月)")
        self.chk_audit.setChecked(False)
        gl.addWidget(self.chk_audit)
        
        audit_row = QHBoxLayout()
        audit_row.addWidget(QLabel("保留月数:"))
        self.spin_audit_months = QSpinBox()
        self.spin_audit_months.setRange(1, 60)
        self.spin_audit_months.setValue(12)
        self.spin_audit_months.setEnabled(False)
        self.chk_audit.toggled.connect(self.spin_audit_months.setEnabled)
        audit_row.addWidget(self.spin_audit_months)
        audit_row.addStretch()
        gl.addLayout(audit_row)

        self.chk_temp = QCheckBox("清理临时文件 (cache/tmp 目录)")
        self.chk_temp.setChecked(True)
        gl.addWidget(self.chk_temp)

        self.chk_logs = QCheckBox("清理旧日志文件 (保留最近 N 个月)")
        self.chk_logs.setChecked(False)
        gl.addWidget(self.chk_logs)
        
        logs_row = QHBoxLayout()
        logs_row.addWidget(QLabel("保留月数:"))
        self.spin_logs_months = QSpinBox()
        self.spin_logs_months.setRange(1, 60)
        self.spin_logs_months.setValue(6)
        self.spin_logs_months.setEnabled(False)
        self.chk_logs.toggled.connect(self.spin_logs_months.setEnabled)
        logs_row.addWidget(self.spin_logs_months)
        logs_row.addStretch()
        gl.addLayout(logs_row)

        # 执行按钮
        btn_row = QHBoxLayout()
        btn_cleanup = QPushButton("执行清理")
        btn_cleanup.setStyleSheet(
            f"background: {C['accent_orange']}; color: white; "
            "border: none; border-radius: 4px; padding: 10px 24px; font-weight: bold;"
        )
        btn_cleanup.setCursor(Qt.PointingHandCursor)
        btn_cleanup.clicked.connect(self._do_cleanup)
        btn_row.addWidget(btn_cleanup)
        btn_row.addStretch()
        gl.addLayout(btn_row)

        # 进度/结果
        self.cleanup_progress = QProgressBar()
        self.cleanup_progress.setVisible(False)
        gl.addWidget(self.cleanup_progress)
        self.cleanup_status = QLabel("")
        self.cleanup_status.setStyleSheet("color: #666; font-size: 9pt;")
        gl.addWidget(self.cleanup_status)

        l.addWidget(grp)
        l.addStretch()

        self.tabs.addTab(tab, "数据清理")

    def _do_cleanup(self):
        # 检查至少选了一项
        if not (self.chk_orphans.isChecked() or self.chk_audit.isChecked() 
                or self.chk_temp.isChecked() or self.chk_logs.isChecked()):
            QMessageBox.warning(self, "提示", "请至少选择一项清理内容")
            return
        
        reply = QMessageBox.question(
            self, "确认清理",
            "清理操作不可撤销，建议先备份数据库。\n确定要执行选中的清理操作吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        self.cleanup_progress.setVisible(True)
        self.cleanup_progress.setValue(0)
        self.cleanup_status.setText("正在清理...")

        # 这里简化实现，实际应调用后端 API
        try:
            from edu_system.services.storage import get_storage_service
            from edu_system.database import get_session
            from edu_system.models import AuditLog
            from sqlalchemy import func
            from datetime import datetime, timedelta

            total_ops = sum([
                self.chk_orphans.isChecked(),
                self.chk_audit.isChecked(),
                self.chk_temp.isChecked(),
                self.chk_logs.isChecked(),
            ])
            current = 0

            def update_progress(op_name):
                nonlocal current
                current += 1
                self.cleanup_progress.setValue(int(current * 100 / total_ops))
                self.cleanup_status.setText(f"正在 {op_name}...")

            if self.chk_orphans.isChecked():
                update_progress("清理孤儿文件")
                storage = get_storage_service()
                # 这里需要实现孤儿文件清理逻辑
                # storage.cleanup_orphans()
                pass

            if self.chk_audit.isChecked():
                update_progress("清理旧审计日志")
                months = self.spin_audit_months.value()
                cutoff = datetime.now() - timedelta(days=months * 30)
                with get_session() as s:
                    s.query(AuditLog).filter(AuditLog.created_at < cutoff).delete()
                    s.commit()

            if self.chk_temp.isChecked():
                update_progress("清理临时文件")
                import tempfile
                import shutil
                temp_dirs = ["/tmp/edu_management", os.path.expanduser("~/.cache/edu_management")]
                for d in temp_dirs:
                    if os.path.exists(d):
                        shutil.rmtree(d, ignore_errors=True)

            if self.chk_logs.isChecked():
                update_progress("清理旧日志文件")
                months = self.spin_logs_months.value()
                cutoff = datetime.now() - timedelta(days=months * 30)
                log_dirs = ["/var/log/edu_management", os.path.expanduser("~/.local/share/edu_management/logs")]
                for d in log_dirs:
                    if os.path.exists(d):
                        for f in os.listdir(d):
                            fpath = os.path.join(d, f)
                            if os.path.isfile(fpath):
                                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                                if mtime < cutoff:
                                    os.remove(fpath)

            self.cleanup_progress.setValue(100)
            QMessageBox.information(self, "完成", "数据清理完成！")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"清理失败: {e}")

    # ===== Tab 3: 审计日志 =====
    def _create_audit_tab(self):
        from PyQt5.QtWidgets import QLineEdit, QComboBox, QSpinBox, QDateEdit
        
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setContentsMargins(12, 12, 12, 12)
        l.setSpacing(8)

        # 搜索/筛选区
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        filter_row.addWidget(QLabel("服务:"))
        self.audit_service_cb = QComboBox()
        self.audit_service_cb.addItem("全部", "")
        # TODO: 从 API 获取服务列表
        filter_row.addWidget(self.audit_service_cb)
        
        filter_row.addWidget(QLabel("方法:"))
        self.audit_method_cb = QComboBox()
        self.audit_method_cb.addItem("全部", "")
        for m in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            self.audit_method_cb.addItem(m, m)
        filter_row.addWidget(self.audit_method_cb)
        
        filter_row.addWidget(QLabel("关键词:"))
        self.audit_keyword = QLineEdit()
        self.audit_keyword.setPlaceholderText("路径/用户/IP/错误信息...")
        self.audit_keyword.setMinimumWidth(200)
        filter_row.addWidget(self.audit_keyword)
        
        filter_row.addWidget(QLabel("时间范围:"))
        self.audit_date_from = QDateEdit()
        self.audit_date_from.setCalendarPopup(True)
        self.audit_date_from.setDate(self._get_default_start_date())
        filter_row.addWidget(self.audit_date_from)
        
        filter_row.addWidget(QLabel("至"))
        self.audit_date_to = QDateEdit()
        self.audit_date_to.setCalendarPopup(True)
        self.audit_date_to.setDate(datetime.now().date())
        filter_row.addWidget(self.audit_date_to)
        
        filter_row.addStretch()
        btn_search = QPushButton("搜索")
        btn_search.setStyleSheet(f"background: {C['accent_blue']}; color: white; padding: 4px 12px;")
        btn_search.clicked.connect(self._search_audit_logs)
        filter_row.addWidget(btn_search)
        l.addLayout(filter_row)

        # 日志表格
        self.audit_table = QTableWidget(0, 7)
        self.audit_table.setHorizontalHeaderLabels([
            "时间", "方法", "路径", "状态码", "耗时(ms)", "用户", "错误信息"
        ])
        self.audit_table.setAlternatingRowColors(True)
        self.audit_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.audit_table.horizontalHeader().setStretchLastSection(True)
        self.audit_table.verticalHeader().hide()
        self.audit_table.setStyleSheet("""
            QTableWidget { font-size:9pt; border:1px solid #DDD; background:white; }
            QHeaderView::section { background:#D9E1F2; font-weight:bold; padding:4px; border:1px solid #CCC; }
        """)
        l.addWidget(self.audit_table)

        # 分页/统计
        page_row = QHBoxLayout()
        self.audit_status = QLabel("就绪")
        self.audit_status.setStyleSheet("color: #666;")
        page_row.addWidget(self.audit_status)
        page_row.addStretch()
        l.addLayout(page_row)

        self.tabs.addTab(tab, "审计日志")

    def _get_default_start_date(self):
        from datetime import datetime, timedelta
        return (datetime.now() - timedelta(days=7)).date()

    def _search_audit_logs(self):
        # TODO: 调用 API /api/audit/logs
        self.audit_status.setText("搜索中...")
        # 这里简化实现
        from datetime import datetime
        self.audit_status.setText(f"搜索完成 - {datetime.now().strftime('%H:%M:%S')}")

    # ===== Tab 4: 数据库维护 =====
    def _create_db_maintenance_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(12)

        grp = QGroupBox("数据库维护工具")
        grp.setFont(font(10, True))
        gl = QVBoxLayout(grp)
        gl.setSpacing(12)

        # VACUUM
        btn_vacuum = QPushButton("执行 VACUUM (整理数据库、回收空间)")
        btn_vacuum.setStyleSheet("padding: 12px; font-size: 10pt;")
        btn_vacuum.clicked.connect(self._run_vacuum)
        gl.addWidget(btn_vacuum)

        # REINDEX
        btn_reindex = QPushButton("执行 REINDEX (重建索引)")
        btn_reindex.setStyleSheet("padding: 12px; font-size: 10pt;")
        btn_reindex.clicked.connect(self._run_reindex)
        gl.addWidget(btn_reindex)

        # ANALYZE
        btn_analyze = QPushButton("执行 ANALYZE (更新统计信息)")
        btn_analyze.setStyleSheet("padding: 12px; font-size: 10pt;")
        btn_analyze.clicked.connect(self._run_analyze)
        gl.addWidget(btn_analyze)

        # 完整性检查
        btn_integrity = QPushButton("完整性检查 (PRAGMA integrity_check)")
        btn_integrity.setStyleSheet("padding: 12px; font-size: 10pt;")
        btn_integrity.clicked.connect(self._run_integrity_check)
        gl.addWidget(btn_integrity)

        # 结果显示
        self.db_maint_log = QTextEdit()
        self.db_maint_log.setReadOnly(True)
        self.db_maint_log.setFont(font(9))
        self.db_maint_log.setMaximumHeight(200)
        self.db_maint_log.setStyleSheet("border:1px solid #DDD; background:#FAFAFA;")
        gl.addWidget(self.db_maint_log)

        l.addWidget(grp)
        l.addStretch()

        self.tabs.addTab(tab, "数据库维护")

    def _run_vacuum(self):
        self.db_maint_log.append("正在执行 VACUUM...")
        try:
            self.session.execute(text("VACUUM"))
            self.session.commit()
            self.db_maint_log.append("✅ VACUUM 完成")
        except Exception as e:
            self.db_maint_log.append(f"❌ VACUUM 失败: {e}")

    def _run_reindex(self):
        self.db_maint_log.append("正在执行 REINDEX...")
        try:
            self.session.execute(text("REINDEX"))
            self.session.commit()
            self.db_maint_log.append("✅ REINDEX 完成")
        except Exception as e:
            self.db_maint_log.append(f"❌ REINDEX 失败: {e}")

    def _run_analyze(self):
        self.db_maint_log.append("正在执行 ANALYZE...")
        try:
            self.session.execute(text("ANALYZE"))
            self.session.commit()
            self.db_maint_log.append("✅ ANALYZE 完成")
        except Exception as e:
            self.db_maint_log.append(f"❌ ANALYZE 失败: {e}")

    def _run_integrity_check(self):
        self.db_maint_log.append("正在执行完整性检查...")
        try:
            from sqlalchemy import text
            result = self.session.execute(text("PRAGMA integrity_check")).fetchall()
            for row in result:
                self.db_maint_log.append(f"  {row[0]}")
            if all(row[0] == "ok" for row in result):
                self.db_maint_log.append("✅ 完整性检查通过")
            else:
                self.db_maint_log.append("❌ 发现完整性问题")
        except Exception as e:
            self.db_maint_log.append(f"❌ 检查失败: {e}")


# 需要导入的模块
from PyQt5.QtWidgets import QLineEdit, QRadioButton, QButtonGroup, QTextEdit
import os
from pathlib import Path
from datetime import datetime
import threading