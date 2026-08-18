from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame, QScrollArea
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QColor, QPalette, QPixmap

from app.ui.dashboard import DashboardWidget
from app.voice.voice_assist import VoiceThread
from app.camera.face_cursor_windows_varient import CameraThread

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

        # Initialize Threads
        self.voice_thread = VoiceThread()
        self.camera_thread = CameraThread()

        # Connect Signals
        self.setup_connections()

    def setup_connections(self):
        # Quick Action Buttons
        self.dashboard.quick_actions_card.btn_start.clicked.connect(self.start_all)
        self.dashboard.quick_actions_card.btn_pause.clicked.connect(self.pause_all)
        self.dashboard.quick_actions_card.btn_voice.clicked.connect(self.toggle_voice)
        self.dashboard.quick_actions_card.btn_calibrate.clicked.connect(self.camera_thread.calibrate)

        # Voice Thread Signals
        self.voice_thread.status_update.connect(lambda s: self.dashboard.status_voice.set_status(s, "#10B981" if s == "Listening" else "#9CA3AF"))
        self.voice_thread.command_recognized.connect(self.update_voice_command)
        self.voice_thread.error_occurred.connect(lambda e: print(f"[Voice Error] {e}"))

        # Camera Thread Signals
        self.camera_thread.status_update.connect(lambda s: self.dashboard.status_camera.set_status(s, "#10B981" if s == "Active" else "#9CA3AF"))
        self.camera_thread.status_update.connect(lambda s: self.dashboard.status_head.set_status(s, "#10B981" if s == "Active" else "#9CA3AF"))
        self.camera_thread.frame_ready.connect(self.update_camera_frame)
        self.camera_thread.error_occurred.connect(lambda e: print(f"[Camera Error] {e}"))

    def start_all(self):
        if not self.camera_thread.isRunning():
            self.camera_thread.is_running = True
            self.camera_thread.start()
        if not self.voice_thread.isRunning():
            self.voice_thread.is_running = True
            self.voice_thread.start()
        self.camera_thread.set_cursor_control(True)
        self.dashboard.status_head.set_status("Active", "#10B981")

    def pause_all(self):
        self.camera_thread.set_cursor_control(False)
        self.dashboard.status_head.set_status("Paused", "#F59E0B")
        if self.voice_thread.isRunning():
            self.voice_thread.stop()

    def toggle_voice(self):
        if self.voice_thread.isRunning():
            self.voice_thread.stop()
        else:
            self.voice_thread.is_running = True
            self.voice_thread.start()

    def update_voice_command(self, text):
        self.dashboard.voice_command_lbl.setText(f"Recognized Command\n{text}")

    def update_camera_frame(self, q_img):
        # Scale image to fit the label width while maintaining aspect ratio
        label_width = self.dashboard.hands_free_card.camera_feed_label.width()
        scaled_img = q_img.scaledToWidth(label_width, Qt.SmoothTransformation)
        self.dashboard.hands_free_card.camera_feed_label.setPixmap(QPixmap.fromImage(scaled_img))
        self.dashboard.hands_free_card.live_label.setText("● LIVE")
        self.dashboard.hands_free_card.live_label.setStyleSheet("color: #10B981; font-weight: bold; font-size: 10px; background: transparent;")

    def closeEvent(self, event):
        # Ensure threads are stopped before exiting
        if self.camera_thread.isRunning():
            self.camera_thread.stop()
        if self.voice_thread.isRunning():
            self.voice_thread.stop()
        super().closeEvent(event)
