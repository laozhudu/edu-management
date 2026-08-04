"""
学生数据模型 — 为 QTableView 提供虚拟数据源
只计算可见行，不创建对象，极致性能
"""

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant
from PyQt5.QtGui import QColor

from edu_system.gui.views.student import ALL_COLUMNS


class StudentTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []  # 当前显示的 Student 列表
        self._columns = []  # 当前显示的列 key 列表
        self._col_labels = {}  # key → 显示名
        self.total_rows = 0  # 总行数（用于状态栏显示）

    def set_columns(self, col_keys, col_labels):
        self.beginResetModel()
        self._columns = col_keys
        self._col_labels = {k: col_labels.get(k, k) for k in col_keys}
        self.endResetModel()

    def set_data(self, data, columns=None):
        self.beginResetModel()
        self._data = data
        if columns is not None:
            self._columns = columns
            self._col_labels = {k: ALL_COLUMNS.get(k, k) for k in columns}
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data) if not parent.isValid() else 0

    def columnCount(self, parent=QModelIndex()):
        return len(self._columns) if not parent.isValid() else 0

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section < len(self._columns):
                return self._col_labels.get(self._columns[section], "")
        return QVariant()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        row, col = index.row(), index.column()
        if row >= len(self._data) or col >= len(self._columns):
            return QVariant()

        s = self._data[row]
        key = self._columns[col]
        val = s.class_name if key == "class_name" else getattr(s, key, "")

        if role == Qt.DisplayRole:
            if key == "birth_date" and val:
                val = str(val)[:10]
            return str(val) if val else ""

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        if role == Qt.ForegroundRole:
            if s.status == "休学":
                return QColor("#999")
            if s.status in ("退学", "转学"):
                return QColor("#999")
            if s.status == "毕业":
                return QColor("#27AE60")

        if role == Qt.BackgroundRole:
            if s.status == "休学":
                return QColor("#F5F5F5")  # 灰
            if s.status in ("退学", "转学"):
                return QColor("#FFF0F0")  # 浅红
            if s.status == "毕业":
                return QColor("#EBF5FB")  # 淡蓝

        return QVariant()

    def get_student(self, row):
        if 0 <= row < len(self._data):
            return self._data[row]
        return None
