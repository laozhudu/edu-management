"""
DeptManagerView — 部门管理视图（B5：对齐若依 sys_dept 树形）

树形展示 + 新增/编辑/删除，含下级部门与停用状态。
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from edu_system.gui.theme import C, font
from edu_system.models import Department


def _btn(txt, color):
    b = QPushButton(txt)
    b.setStyleSheet(
        f"QPushButton {{ background:{color}; color:white; border:none; border-radius:3px; "
        f"padding:3px 12px; font-size:9pt; }} QPushButton:hover {{ background:#2C3E50; }}"
    )
    return b


class DeptManagerView(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self._build_ui()
        self.refresh()

    def refresh(self):
        self._load_tree()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(6)

        tb = QHBoxLayout()
        tb.addWidget(QLabel("部门管理"))
        tb.addStretch()
        b_add = _btn("新增部门", C["accent_green"])
        b_add.clicked.connect(lambda: self._add())
        tb.addWidget(b_add)
        b_ref = _btn("刷新", "#95A5A6")
        b_ref.clicked.connect(self._load_tree)
        tb.addWidget(b_ref)
        lay.addLayout(tb)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["部门名称", "负责人", "电话", "状态"])
        self._tree.setFont(font(9))
        self._tree.setStyleSheet(
            f"QTreeWidget {{ font-size:9pt; border:1px solid {C['table_border']}; background:white; }}"
        )
        self._tree.itemDoubleClicked.connect(lambda i, c: self._edit(i))
        lay.addWidget(self._tree)

    def _build_nodes(self, depts, parent_item=None, parent_id=None):
        for d in depts:
            if d.parent_id != parent_id:
                continue
            item = QTreeWidgetItem(parent_item or self._tree)
            item.setText(0, d.dept_name)
            item.setText(1, d.leader or "")
            item.setText(2, d.phone or "")
            item.setText(3, "正常" if d.status == "0" else "停用")
            item.setData(0, 0x0100, d.id)
            self._build_nodes(depts, item, d.id)

    def _load_tree(self):
        self._tree.clear()
        depts = self.session.query(Department).order_by(Department.order_num).all()
        self._build_nodes(depts)

    def _selected_dept(self, item=None):
        item = item or self._tree.currentItem()
        if not item:
            return None
        return self.session.get(Department, item.data(0, 0x0100))

    def _add(self, parent_item=None):
        parent = self._selected_dept(parent_item)
        dlg = QDialog(self)
        dlg.setWindowTitle("新增部门")
        dlg.setMinimumWidth(340)
        form = QFormLayout(dlg)
        ed_name = QLineEdit()
        ed_leader = QLineEdit()
        ed_phone = QLineEdit()
        ed_order = QSpinBox()
        ed_order.setRange(0, 999)
        form.addRow("部门名称", ed_name)
        form.addRow("负责人", ed_leader)
        form.addRow("电话", ed_phone)
        form.addRow("显示顺序", ed_order)
        row = QHBoxLayout()
        b_ok = _btn("保存", C["accent_green"])

        def do():
            if not ed_name.text().strip():
                QMessageBox.warning(dlg, "提示", "部门名称不能为空")
                return
            self.session.add(
                Department(
                    dept_name=ed_name.text().strip(),
                    parent_id=parent.id if parent else None,
                    leader=ed_leader.text(),
                    phone=ed_phone.text(),
                    order_num=ed_order.value(),
                )
            )
            self.session.commit()
            dlg.accept()
            self._load_tree()

        b_ok.clicked.connect(do)
        b_no = _btn("取消", "#95A5A6")
        b_no.clicked.connect(dlg.reject)
        row.addWidget(b_ok)
        row.addWidget(b_no)
        form.addRow(row)
        dlg.exec_()

    def _edit(self, item=None):
        d = self._selected_dept(item)
        if not d:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("编辑部门")
        dlg.setMinimumWidth(340)
        form = QFormLayout(dlg)
        ed_name = QLineEdit(d.dept_name)
        ed_leader = QLineEdit(d.leader or "")
        ed_phone = QLineEdit(d.phone or "")
        ed_order = QSpinBox()
        ed_order.setRange(0, 999)
        ed_order.setValue(d.order_num or 0)
        form.addRow("部门名称", ed_name)
        form.addRow("负责人", ed_leader)
        form.addRow("电话", ed_phone)
        form.addRow("显示顺序", ed_order)
        row = QHBoxLayout()
        b_ok = _btn("保存", C["accent_green"])

        def do():
            d.dept_name = ed_name.text().strip() or d.dept_name
            d.leader = ed_leader.text()
            d.phone = ed_phone.text()
            d.order_num = ed_order.value()
            self.session.commit()
            dlg.accept()
            self._load_tree()

        b_ok.clicked.connect(do)
        b_no = _btn("取消", "#95A5A6")
        b_no.clicked.connect(dlg.reject)
        row.addWidget(b_ok)
        row.addWidget(b_no)
        form.addRow(row)
        dlg.exec_()

    def _delete(self, item=None):
        d = self._selected_dept(item)
        if not d:
            return
        if self.session.query(Department).filter(Department.parent_id == d.id).first():
            QMessageBox.warning(self, "提示", "存在下级部门，无法删除")
            return
        if (
            QMessageBox.question(self, "确认", f"确认删除部门「{d.dept_name}」？")
            == QMessageBox.Yes
        ):
            self.session.delete(d)
            self.session.commit()
            self._load_tree()
