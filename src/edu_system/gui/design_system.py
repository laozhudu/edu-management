"""
UI 设计系统 - 设计令牌、主题、命令面板、键盘快捷键
基于 PyQt-Fluent-Widgets 扩展
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QKeySequence, QPalette
from PyQt5.QtWidgets import (
    QFrame,
    QListWidgetItem,
    QShortcut,
    QStyle,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import ElevatedCardWidget, LineEdit, ListWidget, Theme, setTheme

# ===== 设计令牌 =====


class ColorRole(Enum):
    """语义化颜色角色"""

    PRIMARY = "primary"
    PRIMARY_HOVER = "primary_hover"
    PRIMARY_PRESSED = "primary_pressed"
    SECONDARY = "secondary"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    BACKGROUND = "background"
    SURFACE = "surface"
    SURFACE_VARIANT = "surface_variant"
    ON_PRIMARY = "on_primary"
    ON_SECONDARY = "on_secondary"
    ON_SURFACE = "on_surface"
    ON_BACKGROUND = "on_background"
    OUTLINE = "outline"
    OUTLINE_VARIANT = "outline_variant"


class Spacing(Enum):
    """间距刻度"""

    NONE = 0
    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32
    XXL = 48


class Radius(Enum):
    """圆角刻度"""

    NONE = 0
    SM = 4
    MD = 8
    LG = 12
    XL = 16
    FULL = 9999


class Typography(Enum):
    """字体刻度"""

    DISPLAY_LARGE = ("display_large", 57, QFont.Normal)
    DISPLAY_MEDIUM = ("display_medium", 45, QFont.Normal)
    DISPLAY_SMALL = ("display_small", 36, QFont.Normal)
    HEADLINE_LARGE = ("headline_large", 32, QFont.Normal)
    HEADLINE_MEDIUM = ("headline_medium", 28, QFont.Normal)
    HEADLINE_SMALL = ("headline_small", 24, QFont.Normal)
    TITLE_LARGE = ("title_large", 22, QFont.Medium)
    TITLE_MEDIUM = ("title_medium", 16, QFont.Medium)
    TITLE_SMALL = ("title_small", 14, QFont.Medium)
    LABEL_LARGE = ("label_large", 14, QFont.Medium)
    LABEL_MEDIUM = ("label_medium", 12, QFont.Medium)
    LABEL_SMALL = ("label_small", 11, QFont.Medium)
    BODY_LARGE = ("body_large", 16, QFont.Normal)
    BODY_MEDIUM = ("body_medium", 14, QFont.Normal)
    BODY_SMALL = ("body_small", 12, QFont.Normal)

    def __init__(self, name: str, size: int, weight: QFont.Weight):
        self.size = size
        self.weight = weight


# 浅色/深色主题色值
LIGHT_COLORS = {
    ColorRole.PRIMARY: "#0078D4",
    ColorRole.PRIMARY_HOVER: "#106EBE",
    ColorRole.PRIMARY_PRESSED: "#005A9E",
    ColorRole.SECONDARY: "#505050",
    ColorRole.SUCCESS: "#107C10",
    ColorRole.WARNING: "#FF8C00",
    ColorRole.ERROR: "#D13438",
    ColorRole.INFO: "#0078D4",
    ColorRole.BACKGROUND: "#F3F3F3",
    ColorRole.SURFACE: "#FFFFFF",
    ColorRole.SURFACE_VARIANT: "#F3F3F3",
    ColorRole.ON_PRIMARY: "#FFFFFF",
    ColorRole.ON_SECONDARY: "#FFFFFF",
    ColorRole.ON_SURFACE: "#1A1A1A",
    ColorRole.ON_BACKGROUND: "#1A1A1A",
    ColorRole.OUTLINE: "#8A888A",
    ColorRole.OUTLINE_VARIANT: "#C8C6C8",
}

DARK_COLORS = {
    ColorRole.PRIMARY: "#0078D4",
    ColorRole.PRIMARY_HOVER: "#3D9CFF",
    ColorRole.PRIMARY_PRESSED: "#0066CC",
    ColorRole.SECONDARY: "#808080",
    ColorRole.SUCCESS: "#16C60C",
    ColorRole.WARNING: "#FFB900",
    ColorRole.ERROR: "#E81123",
    ColorRole.INFO: "#0078D4",
    ColorRole.BACKGROUND: "#1F1F1F",
    ColorRole.SURFACE: "#2D2D2D",
    ColorRole.SURFACE_VARIANT: "#3D3D3D",
    ColorRole.ON_PRIMARY: "#FFFFFF",
    ColorRole.ON_SECONDARY: "#FFFFFF",
    ColorRole.ON_SURFACE: "#FFFFFF",
    ColorRole.ON_BACKGROUND: "#FFFFFF",
    ColorRole.OUTLINE: "#8A888A",
    ColorRole.OUTLINE_VARIANT: "#484648",
}


class DesignTokens:
    """设计令牌管理器"""

    _instance = None
    _theme = Theme.LIGHT
    _custom_colors: dict[ColorRole, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def set_theme(cls, theme: Theme):
        cls._theme = theme
        setTheme(theme)

    @classmethod
    def get_color(cls, role: ColorRole) -> str:
        if role in cls._custom_colors:
            return cls._custom_colors[role]

        colors = DARK_COLORS if cls._theme == Theme.DARK else LIGHT_COLORS
        return colors.get(role, "#000000")

    @classmethod
    def set_custom_color(cls, role: ColorRole, color: str):
        cls._custom_colors[role] = color

    @classmethod
    def get_spacing(cls, spacing: Spacing) -> int:
        return spacing.value

    @classmethod
    def get_radius(cls, radius: Radius) -> int:
        return radius.value

    @classmethod
    def get_font(cls, typography: Typography) -> QFont:
        font = QFont("Microsoft YaHei UI")
        font.setPointSize(typography.size)
        font.setWeight(typography.weight)
        return font

    @classmethod
    def apply_to_widget(cls, widget: QWidget, role: ColorRole = ColorRole.SURFACE):
        """将设计令牌应用到控件"""
        color = cls.get_color(role)
        widget.setStyleSheet(f"background-color: {color};")

    @classmethod
    def get_palette(cls) -> QPalette:
        """获取主题调色板"""
        palette = QPalette()
        colors = DARK_COLORS if cls._theme == Theme.DARK else LIGHT_COLORS

        palette.setColor(QPalette.Window, QColor(colors[ColorRole.BACKGROUND]))
        palette.setColor(QPalette.WindowText, QColor(colors[ColorRole.ON_BACKGROUND]))
        palette.setColor(QPalette.Base, QColor(colors[ColorRole.SURFACE]))
        palette.setColor(QPalette.AlternateBase, QColor(colors[ColorRole.SURFACE_VARIANT]))
        palette.setColor(QPalette.Text, QColor(colors[ColorRole.ON_SURFACE]))
        palette.setColor(QPalette.Button, QColor(colors[ColorRole.PRIMARY]))
        palette.setColor(QPalette.ButtonText, QColor(colors[ColorRole.ON_PRIMARY]))
        palette.setColor(QPalette.Highlight, QColor(colors[ColorRole.PRIMARY]))
        palette.setColor(QPalette.HighlightedText, QColor(colors[ColorRole.ON_PRIMARY]))

        return palette


# ===== 命令面板 =====


@dataclass
class Command:
    """命令定义"""

    id: str
    title: str
    description: str = ""
    icon: Any = None
    shortcut: str = ""
    category: str = "通用"
    action: Callable = None
    keywords: list[str] = field(default_factory=list)
    enabled: bool = True


class CommandPalette(QWidget):
    """命令面板 - Ctrl+K 快速调用"""

    command_executed = pyqtSignal(str)  # command_id

    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Popup | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(self.windowFlags() | Qt.Tool)

        self._commands: dict[str, Command] = {}
        self._filtered_commands: list[Command] = []
        self._selected_index = 0

        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 容器卡片
        self.container = ElevatedCardWidget()
        self.container.setFixedWidth(640)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 搜索框
        self.search_input = LineEdit()
        self.search_input.setPlaceholderText("输入命令或按 Ctrl+K 打开...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setFixedHeight(48)
        container_layout.addWidget(self.search_input)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"color: {DesignTokens.get_color(ColorRole.OUTLINE_VARIANT)};")
        container_layout.addWidget(separator)

        # 结果列表
        self.result_list = ListWidget()
        self.result_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.result_list.setItemDelegate(CommandItemDelegate())
        container_layout.addWidget(self.result_list)

        layout.addWidget(self.container)

    def _setup_shortcuts(self):
        # ESC 关闭
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.hide)
        # Enter 执行
        QShortcut(QKeySequence(Qt.Key_Return), self, self._execute_selected)
        QShortcut(QKeySequence(Qt.Key_Enter), self, self._execute_selected)
        # 上下选择
        QShortcut(QKeySequence(Qt.Key_Up), self, self._select_previous)
        QShortcut(QKeySequence(Qt.Key_Down), self, self._select_next)

    def register_command(self, command: Command):
        """注册命令"""
        self._commands[command.id] = command

    def unregister_command(self, command_id: str):
        """注销命令"""
        self._commands.pop(command_id, None)

    def show_at_center(self):
        """在屏幕中央显示"""
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.container.width()) // 2
            y = parent_rect.y() + 80
            self.move(x, y)

        self.search_input.clear()
        self.search_input.setFocus()
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_search_changed(self, text: str):
        """搜索过滤"""
        self._filtered_commands = []
        text_lower = text.lower()

        for cmd in self._commands.values():
            if not cmd.enabled:
                continue

            # 匹配标题、描述、关键词、快捷键
            searchable = (
                f"{cmd.title} {cmd.description} {cmd.shortcut} {' '.join(cmd.keywords)}".lower()
            )
            if not text_lower or text_lower in searchable:
                self._filtered_commands.append(cmd)

        # 按类别分组排序
        self._filtered_commands.sort(key=lambda c: (c.category, c.title))

        self._update_list()
        self._selected_index = 0
        self._update_selection()

    def _update_list(self):
        """更新列表显示"""
        self.result_list.clear()

        current_category = ""
        for cmd in self._filtered_commands:
            # 添加分类标题
            if cmd.category != current_category:
                current_category = cmd.category
                category_item = QListWidgetItem(f"── {current_category} ──")
                category_item.setFlags(Qt.NoItemFlags)
                category_item.setData(Qt.UserRole, {"is_category": True})
                font = DesignTokens.get_font(Typography.LABEL_SMALL)
                font.setBold(True)
                category_item.setFont(font)
                self.result_list.addItem(category_item)

            item = QListWidgetItem()
            item.setData(Qt.UserRole, {"command": cmd, "is_category": False})
            self.result_list.addItem(item)

        if self._filtered_commands:
            self.result_list.setCurrentRow(0)

    def _update_selection(self):
        """更新选中状态"""
        for i in range(self.result_list.count()):
            item = self.result_list.item(i)
            data = item.data(Qt.UserRole)
            if data and not data.get("is_category"):
                item.setSelected(i == self._selected_index)

    def _select_previous(self):
        """选择上一个"""
        if self._selected_index > 0:
            self._selected_index -= 1
            self._update_selection()
            self.result_list.scrollToItem(self.result_list.item(self._selected_index))

    def _select_next(self):
        """选择下一个"""
        if self._selected_index < len(self._filtered_commands) - 1:
            self._selected_index += 1
            self._update_selection()
            self.result_list.scrollToItem(self.result_list.item(self._selected_index))

    def _execute_selected(self):
        """执行选中命令"""
        if 0 <= self._selected_index < len(self._filtered_commands):
            cmd = self._filtered_commands[self._selected_index]
            if cmd.action:
                try:
                    cmd.action()
                except Exception as e:
                    print(f"命令执行失败 {cmd.id}: {e}")
            self.command_executed.emit(cmd.id)
            self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)


class CommandItemDelegate(QStyledItemDelegate):
    """命令列表项渲染代理"""

    def paint(self, painter, option, index):
        data = index.data(Qt.UserRole)
        if not data or data.get("is_category"):
            super().paint(painter, option, index)
            return

        cmd = data["command"]

        # 背景
        if option.state & QStyle.State_Selected:
            painter.fillRect(
                option.rect, QColor(DesignTokens.get_color(ColorRole.PRIMARY)).lighter(180)
            )
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(option.rect, QColor(DesignTokens.get_color(ColorRole.SURFACE_VARIANT)))
        else:
            painter.fillRect(option.rect, QColor(DesignTokens.get_color(ColorRole.SURFACE)))

        # 文本
        rect = option.rect.adjusted(16, 8, -16, -8)

        # 标题
        title_font = DesignTokens.get_font(Typography.BODY_MEDIUM)
        painter.setFont(title_font)
        painter.setPen(QColor(DesignTokens.get_color(ColorRole.ON_SURFACE)))
        painter.drawText(rect, Qt.AlignLeft | Qt.AlignTop, cmd.title)

        # 描述
        if cmd.description:
            desc_rect = rect.adjusted(0, 22, 0, 0)
            desc_font = DesignTokens.get_font(Typography.BODY_SMALL)
            painter.setFont(desc_font)
            painter.setPen(QColor(DesignTokens.get_color(ColorRole.OUTLINE)))
            painter.drawText(desc_rect, Qt.AlignLeft | Qt.AlignTop, cmd.description)

        # 快捷键
        if cmd.shortcut:
            shortcut_font = DesignTokens.get_font(Typography.LABEL_SMALL)
            painter.setFont(shortcut_font)
            painter.setPen(QColor(DesignTokens.get_color(ColorRole.OUTLINE_VARIANT)))
            shortcut_rect = option.rect.adjusted(-12, 8, -16, -8)
            painter.drawText(shortcut_rect, Qt.AlignRight | Qt.AlignTop, cmd.shortcut)

        # 图标
        if cmd.icon:
            icon_rect = option.rect.adjusted(16, 12, 0, 0).adjusted(0, 0, -48, -48)
            # 这里可以绘制 FluentIcon

    def sizeHint(self, option, index):
        data = index.data(Qt.UserRole)
        if data and data.get("is_category"):
            return QSize(640, 32)
        return QSize(640, 56)


# ===== 键盘快捷键管理器 =====


class ShortcutManager(QObject):
    """全局键盘快捷键管理器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shortcuts: dict[str, QShortcut] = {}
        self._command_palette: CommandPalette | None = None

    def set_command_palette(self, palette: CommandPalette):
        self._command_palette = palette

    def register_shortcut(
        self, key_sequence: str, callback: Callable, context=Qt.WindowShortcut
    ) -> QShortcut:
        """注册快捷键"""
        shortcut = QShortcut(QKeySequence(key_sequence), self.parent(), callback, context=context)
        self._shortcuts[key_sequence] = shortcut
        return shortcut

    def unregister_shortcut(self, key_sequence: str):
        """注销快捷键"""
        if key_sequence in self._shortcuts:
            self._shortcuts[key_sequence].deleteLater()
            del self._shortcuts[key_sequence]

    def setup_default_shortcuts(self):
        """设置默认快捷键"""
        # Ctrl+K 打开命令面板
        self.register_shortcut("Ctrl+K", self._open_command_palette)
        # Ctrl+/ 也可以打开命令面板
        self.register_shortcut("Ctrl+/", self._open_command_palette)
        # F1 帮助
        self.register_shortcut("F1", self._show_help)
        # Ctrl+S 保存
        self.register_shortcut("Ctrl+S", self._save_current)
        # Ctrl+N 新建
        self.register_shortcut("Ctrl+N", self._new_item)
        # Ctrl+F 搜索
        self.register_shortcut("Ctrl+F", self._focus_search)
        # Escape 关闭弹窗/取消
        self.register_shortcut("Esc", self._escape_pressed)

    def _open_command_palette(self):
        if self._command_palette:
            self._command_palette.show_at_center()

    def _show_help(self):
        print("Help requested")

    def _save_current(self):
        print("Save requested")

    def _new_item(self):
        print("New item requested")

    def _focus_search(self):
        print("Focus search")

    def _escape_pressed(self):
        print("Escape pressed")


# ===== 懒加载 TableView 模型 =====

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant, pyqtSignal
from PyQt5.QtWidgets import QTableView


class LazyTableModel(QAbstractTableModel):
    """懒加载表格模型 - 支持虚拟滚动、分页加载"""

    # 信号：请求加载更多数据
    load_more_requested = pyqtSignal(int, int)  # offset, limit
    # 信号：数据加载完成
    data_loaded = pyqtSignal()
    # 信号：加载错误
    load_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._headers: list[str] = []
        self._data: list[list[Any]] = []
        self._total_count = 0
        self._page_size = 100
        self._loaded_count = 0
        self._is_loading = False
        self._has_more = True
        self._fetch_func: Callable | None = None

    def set_headers(self, headers: list[str]):
        """设置表头"""
        self.beginResetModel()
        self._headers = headers
        self.endResetModel()

    def set_fetch_function(self, func: Callable[[int, int], list[list[Any]]]):
        """设置数据获取函数：func(offset, limit) -> rows"""
        self._fetch_func = func

    def set_page_size(self, size: int):
        self._page_size = size

    def set_total_count(self, count: int):
        self._total_count = count

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()

        row = index.row()
        col = index.column()

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if 0 <= row < len(self._data) and 0 <= col < len(self._data[row]):
                return str(self._data[row][col])
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter

        return QVariant()

    def canFetchMore(self, parent=QModelIndex()) -> bool:
        """是否可以加载更多（用于虚拟滚动）"""
        return self._has_more and not self._is_loading and self._loaded_count < self._total_count

    def fetchMore(self, parent=QModelIndex()):
        """加载更多数据（视图滚动时自动调用）"""
        if self._is_loading or not self._has_more or not self._fetch_func:
            return

        self._is_loading = True
        offset = len(self._data)

        # 在后台线程获取数据
        def load_data():
            try:
                rows = self._fetch_func(offset, self._page_size)
                return rows
            except Exception as e:
                return e

        # 这里简化处理，实际应该用 QThread
        try:
            rows = load_data()
            if isinstance(rows, Exception):
                self.load_error.emit(str(rows))
            else:
                self._append_rows(rows)
        finally:
            self._is_loading = False

    def _append_rows(self, rows: list[list[Any]]):
        """追加行数据"""
        if not rows:
            self._has_more = False
            return

        start = len(self._data)
        end = start + len(rows) - 1

        self.beginInsertRows(QModelIndex(), start, end)
        self._data.extend(rows)
        self._loaded_count += len(rows)
        self.endInsertRows()

        if len(rows) < self._page_size:
            self._has_more = False

        self.data_loaded.emit()

    def clear(self):
        """清空数据"""
        self.beginResetModel()
        self._data.clear()
        self._loaded_count = 0
        self._has_more = True
        self.endResetModel()

    def refresh(self):
        """刷新数据"""
        self.clear()
        if self._fetch_func:
            self.fetchMore()


class LazyTableView(QTableView):
    """懒加载表格视图 - 支持虚拟滚动"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        # 启用虚拟滚动
        self.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.setHorizontalScrollMode(QTableView.ScrollPerPixel)

        # 表头设置
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # 选择模式
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)

        # 交替行颜色
        self.setAlternatingRowColors(True)

        # 无焦点矩形
        self.setFocusPolicy(Qt.NoFocus)

    def setModel(self, model: LazyTableModel):
        super().setModel(model)
        if isinstance(model, LazyTableModel):
            # 连接滚动信号
            self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def _on_scroll(self, value: int):
        """滚动时触发加载更多"""
        model = self.model()
        if isinstance(model, LazyTableModel):
            # 当滚动到接近底部时
            max_val = self.verticalScrollBar().maximum()
            if value > max_val * 0.8:
                model.fetchMore()


# ===== 全局实例 =====

design_tokens = DesignTokens()
command_palette = None  # 需在 MainWindow 中初始化
shortcut_manager = None  # 需在 MainWindow 中初始化


# ===== 便捷函数 =====


def register_global_shortcut(key: str, callback: Callable):
    """注册全局快捷键（需在 shortcut_manager 初始化后调用）"""
    global shortcut_manager
    if shortcut_manager:
        shortcut_manager.register_shortcut(key, callback)


def open_command_palette():
    """打开命令面板"""
    global command_palette
    if command_palette:
        command_palette.show_at_center()


def apply_theme(widget: QWidget, theme: Theme = Theme.LIGHT):
    """应用主题到控件"""
    DesignTokens.set_theme(theme)
    widget.setPalette(DesignTokens.get_palette())


def get_color(role: ColorRole) -> str:
    """获取语义化颜色"""
    return DesignTokens.get_color(role)


def get_spacing(spacing: Spacing) -> int:
    return DesignTokens.get_spacing(spacing)


def get_radius(radius: Radius) -> int:
    return DesignTokens.get_radius(radius)


def get_font(typography: Typography) -> QFont:
    return DesignTokens.get_font(typography)
