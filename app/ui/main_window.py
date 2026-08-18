
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame, QScrollArea
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QColor, QPalette

from app.ui.dashboard import DashboardWidget

class SidebarButton(QPushButton):
    def __init__(self, text, icon_name=None, active=False):
        super().__init__(text)
        self.setMinimumHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#1A1A2E' if active else 'transparent'};
                color: {'#FFFFFF' if active else '#9CA3AF'};
                border: none;
                border-radius: 8px;
                text-align: left;
                padding-left: 16px;
                font-weight: {'bold' if active else 'normal'};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #1A1A2E;
                color: #FFFFFF;
            }}
        """)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BUG - Hands-Free Browsing Assistant")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #000000;")
        
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #0B0B14;
                border-right: 1px solid #1F1F33;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(8)
        
        # Logo
        logo_label = QLabel("BUG")
        logo_label.setStyleSheet("color: #FFFFFF; font-size: 24px; font-weight: bold; padding-left: 16px; margin-bottom: 24px;")
        sidebar_layout.addWidget(logo_label)
        
        # Navigation
        nav_items = [
            ("Home", True),
            ("Control Center", False),
            ("Voice Center", False),
            ("My Study", False),
            ("AI Assistant", False),
            ("History", False),
            ("Settings", False)
        ]
        
        for text, active in nav_items:
            btn = SidebarButton(text, active=active)
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch()
        
        # User profile
        profile_btn = QPushButton("User\nFree Plan")
        profile_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #FFFFFF;
                border: none;
                text-align: left;
                padding: 12px;
                border-top: 1px solid #1F1F33;
            }
        """)
        sidebar_layout.addWidget(profile_btn)
        
        main_layout.addWidget(sidebar)
        
        # Dashboard Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #0B0B14; }")
        
        self.dashboard = DashboardWidget()
        scroll_area.setWidget(self.dashboard)
        
        main_layout.addWidget(scroll_area)
