"""
GUI 视图 — 初始化系统 (PyQt5)
完整清空数据库并重建，含配置向导
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from edu_system.config import DB_PATH
from edu_system.gui.theme import C


def _btn(txt, color):
    b = QPushButton(txt)
    b.setStyleSheet(
        f"""QPushButton {{ background: {color}; color: white; border: none;
        border-radius: 4px; padding: 8px 16px; font-size: 10pt; }}
        QPushButton:hover {{ background: #34495E; }}"""
    )
    b.setCursor(Qt.PointingHandCursor)
    b.setMinimumHeight(32)
    return b


class InitView(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self._build_ui()

    def refresh(self):
        pass

    def _build_ui(self):
        if self.layout():
            QWidget().setLayout(self.layout())
        self.setLayout(QVBoxLayout())
        lay = self.layout()
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        # 设置最小尺寸，防止界面跳动
        self.setMinimumSize(800, 550)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 工具栏
        tb = QHBoxLayout()
        tb.setSpacing(4)
        tb.addWidget(QLabel("初始化系统"))
        tb.addStretch()
        lay.addLayout(tb)

        # 当前数据概览
        info = QFrame()
        info.setFrameShape(QFrame.StyledPanel)
        info.setStyleSheet(
            "background: white; border: 1px solid #DDD; border-radius: 4px; padding: 10px;"
        )
        il = QVBoxLayout(info)
        inspector = inspect(self.session.bind)
        tables = sorted(inspector.get_table_names())
        lines = ["当前数据库状态:"]
        for tbl in tables:
            cnt = self.session.execute(text(f"SELECT COUNT(*) FROM [{tbl}]")).fetchone()[0]
            if cnt > 0:
                lines.append(f"  {tbl}: {cnt} 条")
        il.addWidget(QLabel("\n".join(lines) if len(lines) > 1 else "数据库为空"))
        lay.addWidget(info)

        # 操作区
        warn = QFrame()
        warn.setFrameShape(QFrame.StyledPanel)
        warn.setStyleSheet(
            "background: #FFF3CD; border: 2px solid #FFC107; border-radius: 6px; padding: 12px;"
        )
        wl = QVBoxLayout(warn)
        wl.setSpacing(8)
        wl.addWidget(QLabel("⚠ 以下操作将清空全部数据，不可恢复！"))
        wl.addWidget(QLabel("包括: 学生、教师、考试、成绩、学期、任课分配、学籍变动记录"))
        wl.addWidget(QLabel("保留: 年级定义、科目定义、系统设置"))

        row = QHBoxLayout()
        row.setSpacing(8)
        for txt, clr, cb in [
            ("清空并重建数据库", C["accent_red"], self._full_reset),
            ("仅清空业务数据", C["accent_orange"], self._reset_business),
        ]:
            b = _btn(txt, clr)
            b.clicked.connect(cb)
            row.addWidget(b)
        row.addStretch()
        wl.addLayout(row)
        lay.addWidget(warn)

        # 导入配置
        cfg = QFrame()
        cfg.setFrameShape(QFrame.StyledPanel)
        cfg.setStyleSheet(
            "background: white; border: 1px solid #DDD; border-radius: 4px; padding: 10px;"
        )
        cl = QVBoxLayout(cfg)
        cl.setSpacing(6)
        cl.addWidget(QLabel("数据库重建后将自动初始化: 年级(3) / 科目(10)"))
        b = _btn("批量导入全部数据", C["accent_green"])
        b.clicked.connect(self._batch_import)
        cl.addWidget(b)
        lay.addWidget(cfg)

        lay.addStretch()

    def _full_reset(self):
        """完整清空：删除DB文件重建"""
        if (
            QMessageBox.question(
                self,
                "最终确认",
                "此操作将删除数据库文件并重建！\n"
                "所有数据（学生/成绩/教师/学期/任课）将永久丢失。\n\n"
                "请确认要执行此操作。",
            )
            != QMessageBox.Yes
        ):
            return

        ans = QInputDialog.getText(self, "确认", "请输入 'RESET' 确认:")
        if ans[0] != "RESET":
            QMessageBox.information(self, "取消", "操作已取消")
            return

        try:
            self.session.close()
            import os

            os.remove(DB_PATH)
            from edu_system.database import get_session, init_db_with_defaults

            init_db_with_defaults()
            self.session = get_session()
            QMessageBox.information(
                self,
                "完成",
                "数据库已重建。\n年级(3)和科目(10)已初始化。\n请在数据维护中创建初始学期。",
            )
            # 通知主窗口更新
            m = self.window()
            if hasattr(m, "_update_semester_display"):
                m.session = self.session
                m._update_semester_display()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _reset_business(self):
        """清空业务数据，保留系统表"""
        if (
            QMessageBox.question(self, "确认", "清空所有业务数据？\n(保留年级/科目/学期/设置)")
            != QMessageBox.Yes
        ):
            return

        inspector = inspect(self.session.bind)
        protected = {"grades", "subjects", "semesters", "settings"}
        cleared = []
        for tbl in inspector.get_table_names():
            if tbl not in protected:
                cnt = self.session.execute(text(f"SELECT COUNT(*) FROM [{tbl}]")).fetchone()[0]
                if cnt > 0:
                    self.session.execute(text(f"DELETE FROM [{tbl}]"))
                    cleared.append(f"{tbl}({cnt})")
        self.session.commit()
        QMessageBox.information(
            self, "完成", f"已清空: {', '.join(cleared) if cleared else '无需清空'}"
        )

    def _batch_import(self):
        """批量导入所有共享文件夹中的数据"""
        import os

        share = os.path.expanduser("~/share")
        if not os.path.exists(share):
            QMessageBox.warning(self, "错误", f"共享文件夹不存在: {share}")
            return

        msg = "将从共享文件夹导入:\n"
        files = []
        for f in os.listdir(share):
            if f.endswith(".xlsx") or f.endswith(".xls"):
                if "名单" in f or "学籍" in f or "在校生" in f or "教师" in f or "技术" in f:
                    msg += f"  • {f}\n"
                    files.append(os.path.join(share, f))

        if not files:
            QMessageBox.information(self, "提示", "未找到可导入的文件")
            return

        if (
            QMessageBox.question(self, "确认导入", msg + f"\n共 {len(files)} 个文件")
            != QMessageBox.Yes
        ):
            return

        results = []
        from edu_system.services.importer import ImportService

        for f in files:
            result = ImportService(self.session).import_students_from_excel(f)
            results.append(f"{os.path.basename(f)}: {result.summary}")

        self.session.commit()
        QMessageBox.information(self, "导入完成", "\n".join(results[:10]))
