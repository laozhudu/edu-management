"""
DictManagerView — 字典管理视图（M1）

类型列表 + 数据管理（对齐若依 #6 字典）：
- 左侧字典类型列表（增删改）+ 右侧该类型的数据编辑
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from edu_system.gui.theme import C, font
from edu_system.models import DictData, DictType


def _btn(txt, color):
    b = QPushButton(txt)
    b.setStyleSheet(
        f"QPushButton {{ background:{color}; color:white; border:none; border-radius:3px; "
        f"padding:3px 12px; font-size:9pt; }} QPushButton:hover {{ background:#2C3E50; }}"
    )
    return b


class DictManagerView(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self._build_ui()
        self._reload_types()

    def refresh(self):
        self._reload_types()
        self._reload_params()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(6)

        self._tabs = QTabWidget()
        self._tabs.setFont(font(9))
        self._tabs.addTab(self._build_dict_tab(), "字典管理")
        self._tabs.addTab(self._build_params_tab(), "参数管理")
        lay.addWidget(self._tabs)

    def _build_dict_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(6)

        tb = QHBoxLayout()
        tb.addWidget(QLabel("字典管理"))
        tb.addStretch()
        b_add = _btn("新增类型", C["accent_green"])
        b_add.clicked.connect(self._add_type)
        tb.addWidget(b_add)
        lay.addLayout(tb)

        splitter = QSplitter()
        # 左侧类型表
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self._type_table = QTableWidget(0, 2)
        self._type_table.setHorizontalHeaderLabels(["类型编码", "名称"])
        self._type_table.setFont(font(9))
        self._type_table.verticalHeader().hide()
        self._type_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._type_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._type_table.setStyleSheet(
            f"QTableWidget {{ font-size:9pt; border:1px solid {C['table_border']}; background:white; }}"
        )
        self._type_table.itemSelectionChanged.connect(self._on_type_selected)
        ll.addWidget(self._type_table)
        # 类型操作
        tl = QHBoxLayout()
        b_edit = _btn("编辑类型", "#3498DB")
        b_edit.clicked.connect(self._edit_type)
        tl.addWidget(b_edit)
        b_del = _btn("删除类型", "#E74C3C")
        b_del.clicked.connect(self._delete_type)
        tl.addWidget(b_del)
        ll.addLayout(tl)
        splitter.addWidget(left)

        # 右侧数据表
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self._data_title = QLabel("选择左侧类型查看数据")
        self._data_title.setFont(font(10, True))
        rl.addWidget(self._data_title)
        self._data_table = QTableWidget(0, 4)
        self._data_table.setHorizontalHeaderLabels(["标签", "值", "排序", "状态"])
        self._data_table.setFont(font(9))
        self._data_table.verticalHeader().hide()
        self._data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._data_table.setStyleSheet(
            f"QTableWidget {{ font-size:9pt; border:1px solid {C['table_border']}; background:white; }}"
        )
        rl.addWidget(self._data_table)
        dl = QHBoxLayout()
        b_dadd = _btn("新增数据", C["accent_green"])
        b_dadd.clicked.connect(self._add_data)
        dl.addWidget(b_dadd)
        b_dedit = _btn("编辑数据", "#3498DB")
        b_dedit.clicked.connect(self._edit_data)
        dl.addWidget(b_dedit)
        b_ddel = _btn("删除数据", "#E74C3C")
        b_ddel.clicked.connect(self._delete_data)
        dl.addWidget(b_ddel)
        dl.addStretch()
        rl.addLayout(dl)
        splitter.addWidget(right)
        splitter.setSizes([300, 600])
        lay.addWidget(splitter)
        return tab

    def _build_params_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(6)

        tb = QHBoxLayout()
        tb.addWidget(QLabel("参数管理"))
        tb.addStretch()
        b_add = _btn("新增参数", C["accent_green"])
        b_add.clicked.connect(self._add_param)
        tb.addWidget(b_add)
        lay.addLayout(tb)

        self._param_table = QTableWidget(0, 4)
        self._param_table.setHorizontalHeaderLabels(["键", "值", "说明", "操作"])
        self._param_table.setFont(font(9))
        self._param_table.verticalHeader().hide()
        self._param_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._param_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._param_table.horizontalHeader().setStretchLastSection(True)
        self._param_table.setStyleSheet(
            f"QTableWidget {{ font-size:9pt; border:1px solid {C['table_border']}; background:white; }}"
        )
        lay.addWidget(self._param_table)
        return tab

    def _reload_types(self):
        self._type_table.blockSignals(True)
        self._type_table.setRowCount(0)
        types = self.session.query(DictType).order_by(DictType.id).all()
        self._type_table.setRowCount(len(types))
        for i, t in enumerate(types):
            it0 = QTableWidgetItem(t.dict_type)
            it0.setData(0x0100, t.id)
            self._type_table.setItem(i, 0, it0)
            self._type_table.setItem(i, 1, QTableWidgetItem(t.dict_name))
        self._type_table.blockSignals(False)
        if types:
            self._type_table.selectRow(0)
            self._on_type_selected()

    def _selected_type_id(self):
        row = self._type_table.currentRow()
        if row < 0:
            return None
        return self._type_table.item(row, 0).data(0x0100)

    def _on_type_selected(self):
        tid = self._selected_type_id()
        if tid is None:
            self._data_table.setRowCount(0)
            return
        t = self.session.get(DictType, tid)
        if not t:
            return
        self._data_title.setText(f"{t.dict_name}（{t.dict_type}）数据")
        self._data_table.setRowCount(0)
        datas = (
            self.session.query(DictData)
            .filter(DictData.dict_type == t.dict_type)
            .order_by(DictData.sort_order, DictData.id)
            .all()
        )
        self._data_table.setRowCount(len(datas))
        for i, d in enumerate(datas):
            it0 = QTableWidgetItem(d.dict_label)
            it0.setData(0x0100, d.id)
            self._data_table.setItem(i, 0, it0)
            self._data_table.setItem(i, 1, QTableWidgetItem(d.dict_value))
            self._data_table.setItem(i, 2, QTableWidgetItem(str(d.sort_order)))
            self._data_table.setItem(i, 3, QTableWidgetItem("停用" if d.status == "1" else "正常"))

    # ── 类型 CRUD ──
    def _type_dialog(self, tid: int | None):
        t = self.session.get(DictType, tid) if tid else None
        dlg = QDialog(self)
        dlg.setWindowTitle("编辑字典类型" if t else "新增字典类型")
        form = QFormLayout(dlg)
        ed_code = QLineEdit(t.dict_type if t else "")
        ed_code.setFont(font(9))
        form.addRow("类型编码", ed_code)
        ed_name = QLineEdit(t.dict_name if t else "")
        ed_name.setFont(font(9))
        form.addRow("名称", ed_name)
        row = QHBoxLayout()
        b_ok = _btn("保存", C["accent_green"])

        def do():
            if not ed_code.text().strip() or not ed_name.text().strip():
                QMessageBox.warning(dlg, "提示", "编码和名称不能为空")
                return
            if t:
                t.dict_type = ed_code.text().strip()
                t.dict_name = ed_name.text().strip()
            else:
                dup = (
                    self.session.query(DictType)
                    .filter(DictType.dict_type == ed_code.text().strip())
                    .first()
                )
                if dup:
                    QMessageBox.warning(dlg, "提示", "类型已存在")
                    return
                self.session.add(
                    DictType(dict_type=ed_code.text().strip(), dict_name=ed_name.text().strip())
                )
            self.session.commit()
            dlg.accept()
            self._reload_types()

        b_ok.clicked.connect(do)
        b_no = _btn("取消", "#95A5A6")
        b_no.clicked.connect(dlg.reject)
        row.addWidget(b_ok)
        row.addWidget(b_no)
        form.addRow(row)
        dlg.exec_()

    def _add_type(self):
        self._type_dialog(None)

    def _edit_type(self):
        tid = self._selected_type_id()
        if tid is not None:
            self._type_dialog(tid)

    def _delete_type(self):
        tid = self._selected_type_id()
        if tid is None:
            return
        t = self.session.get(DictType, tid)
        if not t:
            return
        if (
            QMessageBox.question(self, "确认", f"删除字典类型「{t.dict_name}」及其全部数据？")
            == QMessageBox.Yes
        ):
            self.session.query(DictData).filter(DictData.dict_type == t.dict_type).delete()
            self.session.delete(t)
            self.session.commit()
            self._reload_types()

    # ── 数据 CRUD ──
    def _current_dict_type(self):
        tid = self._selected_type_id()
        t = self.session.get(DictType, tid) if tid else None
        return t.dict_type if t else None

    def _add_data(self):
        dt = self._current_dict_type()
        if not dt:
            QMessageBox.warning(self, "提示", "请先选择字典类型")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"新增数据 — {dt}")
        form = QFormLayout(dlg)
        ed_label = QLineEdit()
        ed_label.setFont(font(9))
        form.addRow("标签", ed_label)
        ed_value = QLineEdit()
        ed_value.setFont(font(9))
        form.addRow("值", ed_value)
        ed_sort = QLineEdit("0")
        ed_sort.setFont(font(9))
        form.addRow("排序", ed_sort)
        row = QHBoxLayout()
        b_ok = _btn("保存", C["accent_green"])

        def do():
            if not ed_label.text().strip():
                QMessageBox.warning(dlg, "提示", "标签不能为空")
                return
            try:
                sort = int(ed_sort.text() or "0")
            except ValueError:
                sort = 0
            self.session.add(
                DictData(
                    dict_type=dt,
                    dict_label=ed_label.text().strip(),
                    dict_value=ed_value.text().strip() or ed_label.text().strip(),
                    sort_order=sort,
                )
            )
            self.session.commit()
            dlg.accept()
            self._on_type_selected()

        b_ok.clicked.connect(do)
        b_no = _btn("取消", "#95A5A6")
        b_no.clicked.connect(dlg.reject)
        row.addWidget(b_ok)
        row.addWidget(b_no)
        form.addRow(row)
        dlg.exec_()

    def _edit_data(self):
        row = self._data_table.currentRow()
        if row < 0:
            return
        did = self._data_table.item(row, 0).data(0x0100)
        d = self.session.get(DictData, did)
        if not d:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("编辑数据")
        form = QFormLayout(dlg)
        ed_label = QLineEdit(d.dict_label)
        ed_label.setFont(font(9))
        form.addRow("标签", ed_label)
        ed_value = QLineEdit(d.dict_value)
        ed_value.setFont(font(9))
        form.addRow("值", ed_value)
        ed_sort = QLineEdit(str(d.sort_order))
        ed_sort.setFont(font(9))
        form.addRow("排序", ed_sort)
        row_btn = QHBoxLayout()
        b_ok = _btn("保存", C["accent_green"])

        def do():
            d.dict_label = ed_label.text().strip() or d.dict_label
            d.dict_value = ed_value.text().strip() or d.dict_label
            try:
                d.sort_order = int(ed_sort.text() or "0")
            except ValueError:
                pass
            self.session.commit()
            dlg.accept()
            self._on_type_selected()

        b_ok.clicked.connect(do)
        b_no = _btn("取消", "#95A5A6")
        b_no.clicked.connect(dlg.reject)
        row_btn.addWidget(b_ok)
        row_btn.addWidget(b_no)
        form.addRow(row_btn)
        dlg.exec_()

    def _delete_data(self):
        row = self._data_table.currentRow()
        if row < 0:
            return
        did = self._data_table.item(row, 0).data(0x0100)
        d = self.session.get(DictData, did)
        if not d:
            return
        if (
            QMessageBox.question(self, "确认", f"删除字典数据「{d.dict_label}」？")
            == QMessageBox.Yes
        ):
            self.session.delete(d)
            self.session.commit()
            self._on_type_selected()

    # ── 参数管理（M1：GlobalSetting） ──

    def _reload_params(self):
        if not hasattr(self, "_param_table"):
            return
        from edu_system.models import GlobalSetting

        self._param_table.setRowCount(0)
        params = self.session.query(GlobalSetting).order_by(GlobalSetting.key).all()
        self._param_table.setRowCount(len(params))
        for i, p in enumerate(params):
            it0 = QTableWidgetItem(p.key)
            it0.setData(0x0100, p.key)
            self._param_table.setItem(i, 0, it0)
            self._param_table.setItem(i, 1, QTableWidgetItem(p.value or ""))
            self._param_table.setItem(i, 2, QTableWidgetItem(p.description or ""))
            w = QWidget()
            bl = QHBoxLayout(w)
            bl.setContentsMargins(2, 0, 2, 0)
            bl.setSpacing(2)
            b_e = _btn("编辑", "#3498DB")
            b_e.clicked.connect(lambda _, k=p.key: self._edit_param(k))
            bl.addWidget(b_e)
            b_d = _btn("删除", "#E74C3C")
            b_d.clicked.connect(lambda _, k=p.key: self._delete_param(k))
            bl.addWidget(b_d)
            self._param_table.setCellWidget(i, 3, w)

    def _param_dialog(self, key: str | None):
        from edu_system.models import GlobalSetting

        p = (
            self.session.query(GlobalSetting).filter(GlobalSetting.key == key).first()
            if key
            else None
        )
        dlg = QDialog(self)
        dlg.setWindowTitle("编辑参数" if p else "新增参数")
        form = QFormLayout(dlg)
        ed_key = QLineEdit(p.key if p else "")
        ed_key.setFont(font(9))
        ed_key.setReadOnly(bool(p))
        form.addRow("键", ed_key)
        ed_val = QLineEdit(p.value or "" if p else "")
        ed_val.setFont(font(9))
        form.addRow("值", ed_val)
        ed_desc = QLineEdit(p.description or "" if p else "")
        ed_desc.setFont(font(9))
        form.addRow("说明", ed_desc)
        row = QHBoxLayout()
        b_ok = _btn("保存", C["accent_green"])

        def do():
            if not ed_key.text().strip():
                QMessageBox.warning(dlg, "提示", "键不能为空")
                return
            if p:
                p.value = ed_val.text()
                p.description = ed_desc.text()
            else:
                dup = (
                    self.session.query(GlobalSetting)
                    .filter(GlobalSetting.key == ed_key.text().strip())
                    .first()
                )
                if dup:
                    QMessageBox.warning(dlg, "提示", "参数已存在")
                    return
                self.session.add(
                    GlobalSetting(
                        key=ed_key.text().strip(), value=ed_val.text(), description=ed_desc.text()
                    )
                )
            self.session.commit()
            dlg.accept()
            self._reload_params()

        b_ok.clicked.connect(do)
        b_no = _btn("取消", "#95A5A6")
        b_no.clicked.connect(dlg.reject)
        row.addWidget(b_ok)
        row.addWidget(b_no)
        form.addRow(row)
        dlg.exec_()

    def _add_param(self):
        self._param_dialog(None)

    def _edit_param(self, key: str):
        self._param_dialog(key)

    def _delete_param(self, key: str):
        from edu_system.models import GlobalSetting

        p = self.session.query(GlobalSetting).filter(GlobalSetting.key == key).first()
        if not p:
            return
        if QMessageBox.question(self, "确认", f"删除参数「{key}」？") == QMessageBox.Yes:
            self.session.delete(p)
            self.session.commit()
            self._reload_params()
