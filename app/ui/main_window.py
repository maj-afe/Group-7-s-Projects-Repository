from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from app.ui.dashboard import DashboardWidget
from app.voice.voice_assist import VoiceThread
from app.camera.face_cursor_windows_varient import CameraThread

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BUG - Hands-Free Browsing Assistant")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet("background-color: #000000;")
        
        self.dashboard = DashboardWidget()
        self.setCentralWidget(self.dashboard)

        # Initialize Threads
        self.voice_thread = VoiceThread()
        self.camera_thread = CameraThread()

        # Connect Signals
        self.setup_connections()

    def setup_connections(self):
        # Quick Action Buttons
        self.dashboard.btn_start.clicked.connect(self.start_all)
        self.dashboard.btn_pause.clicked.connect(self.pause_all)
        self.dashboard.btn_voice.clicked.connect(self.toggle_voice)
        self.dashboard.btn_calibrate.clicked.connect(self.camera_thread.calibrate)

        # Voice Thread Signals
        self.voice_thread.status_update.connect(lambda s: self.dashboard.status_voice.set_status(s, "#10B981" if s == "Listening" else "#9CA3AF"))
        self.voice_thread.command_recognized.connect(self.update_voice_command)

        # Camera Thread Signals
        self.camera_thread.status_update.connect(lambda s: self.dashboard.status_camera.set_status(s, "#10B981" if s == "Active" else "#9CA3AF"))
        self.camera_thread.status_update.connect(lambda s: self.dashboard.status_head.set_status(s, "#10B981" if s == "Active" else "#9CA3AF"))
        self.camera_thread.frame_ready.connect(self.update_camera_frame)

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
        self.dashboard.voice_command_lbl.setText(f'"{text}"')

    def update_camera_frame(self, q_img):
        # Scale image to fit the label width while maintaining aspect ratio
        label_width = self.dashboard.camera_feed_label.width()
        label_height = self.dashboard.camera_feed_label.height()
        scaled_img = q_img.scaled(label_width, label_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.dashboard.camera_feed_label.setPixmap(QPixmap.fromImage(scaled_img))

    def closeEvent(self, event):
        # Ensure threads are stopped before exiting
        if self.camera_thread.isRunning():
            self.camera_thread.stop()
        if self.voice_thread.isRunning():
            self.voice_thread.stop()
        super().closeEvent(event)
