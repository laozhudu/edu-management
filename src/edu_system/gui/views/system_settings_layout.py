"""
系统设置视图统一布局基类
确保所有系统设置标签页保持一致的尺寸和布局
"""

from PyQt5.QtWidgets import QVBoxLayout, QWidget
from typing import List, Tuple, Callable, Optional
from edu_system.gui.theme import font

class SystemSettingsViewMixin:
    """系统设置视图混入类 - 提供统一布局参数"""
    
    # 统一的布局参数
    CONTENTS_MARGINS = (16, 12, 16, 12)  # left, top, right, bottom
    SPACING = 12
    TITLE_FONT_SIZE = 16
    TITLE_BOLD = True
    TITLE_COLOR = "#1a1a2e"
    TITLE_MARGIN_BOTTOM = "8px"
    
    def _create_standard_layout(self) -> QVBoxLayout:
        """创建标准布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*self.CONTENTS_MARGINS)
        layout.setSpacing(self.SPACING)
        return layout
    
    def _add_standard_title(self, layout: QVBoxLayout, title_text: str):
        """添加标准标题"""
        from PyQt5.QtWidgets import QLabel
        title = QLabel(title_text)
        title.setFont(font(self.TITLE_FONT_SIZE, self.TITLE_BOLD))
        title.setStyleSheet(f"color: {self.TITLE_COLOR}; margin-bottom: {self.TITLE_MARGIN_BOTTOM};")
        layout.addWidget(title)
        return title
    
    def _create_standard_tabs(self, layout: QVBoxLayout):
        """创建标准标签页容器"""
        from PyQt5.QtWidgets import QTabWidget
        tabs = QTabWidget()
        tabs.setStyleSheet(
            """
            QTabWidget::pane { border: 1px solid #d9d9d9; border-radius: 4px; }
            QTabBar::tab { padding: 8px 16px; margin-right: 4px; }
            QTabBar::tab:selected { background: #1890ff; color: white; }
            """
        )
        layout.addWidget(tabs, 1)  # stretch factor = 1 使标签页填满剩余空间
        return tabs
    
    def _add_standard_bottom_buttons(self, layout: QVBoxLayout, buttons: Optional[List] = None):
        """添加标准底部按钮区"""
        from PyQt5.QtWidgets import QHBoxLayout, QPushButton
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        if buttons:
            for btn_text, btn_color, btn_callback, btn_style in buttons:
                btn = QPushButton(btn_text)
                btn.setStyleSheet(btn_style)
                if btn_callback:
                    btn.clicked.connect(btn_callback)
                btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)


def setup_system_settings_view(view_instance: QWidget, title_text: str, tabs_config: List[Tuple[str, str]], bottom_buttons: Optional[List] = None):
    """
    统一配置系统设置视图
    
    Args:
        view_instance: 视图实例
        title_text: 标题文本
        tabs_config: [(tab_name, build_tab_method_name), ...]
        bottom_buttons: [(btn_text, btn_color, callback, style), ...]
    """
    from PyQt5.QtWidgets import QVBoxLayout, QTabWidget, QHBoxLayout, QPushButton, QLabel, QWidget, QSizePolicy
    from PyQt5.QtWidgets import QWidget
    from edu_system.gui.theme import C, font
    
    # 清除现有布局
    if view_instance.layout():
        QWidget().setLayout(view_instance.layout())
    
    layout = QVBoxLayout(view_instance)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(12)
    
    # 标题
    title = QLabel(title_text)
    title.setFont(font(16, True))
    title.setStyleSheet("color: #1a1a2e; margin-bottom: 8px;")
    layout.addWidget(title)
    
    # 标签页
    tabs = QTabWidget()
    tabs.setStyleSheet(
        """
        QTabWidget::pane { border: 1px solid #d9d9d9; border-radius: 4px; }
        QTabBar::tab { padding: 8px 16px; margin-right: 4px; }
        QTabBar::tab:selected { background: #1890ff; color: white; }
        """
    )
    
    for tab_name, build_method_name in tabs_config:
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(16, 16, 16, 16)
        tab_layout.setSpacing(12)
        
        # 调用构建方法
        build_method = getattr(view_instance, build_method_name)
        build_method(tab_widget, tab_layout)
        
        tabs.addTab(tab_widget, tab_name)
    
    layout.addWidget(tabs, 1)  # stretch=1
    
    # 设置标签页最小尺寸，防止切换时界面跳动
    tabs.setMinimumSize(800, 550)
    tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    
    # DEBUG: 打印标签页尺寸
    print(f"DEBUG: tabs minimumSize={tabs.minimumSize()}, sizeHint={tabs.sizeHint()}")
    
    # 底部按钮
    if bottom_buttons:
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        for btn_text, btn_color, callback, style in bottom_buttons:
            btn = QPushButton(btn_text)
            btn.setStyleSheet(style)
            if callback:
                btn.clicked.connect(callback)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)
    
    view_instance._tabs = tabs
    view_instance.setLayout(layout)