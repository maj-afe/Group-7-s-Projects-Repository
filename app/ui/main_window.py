from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap

from app.ui.dashboard import DashboardWidget
from app.voice.voice_assist import VoiceAssistant
from app.camera.face_cursor_windows_varient import CameraThread


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "BUG - Hands-Free Browsing Assistant"
        )

        self.setMinimumSize(1000, 700)

        self.setStyleSheet(
            "background-color: #000000;"
        )

        # ==========================================
        # DASHBOARD
        # ==========================================

        self.dashboard = DashboardWidget()

        self.setCentralWidget(
            self.dashboard
        )

        # ==========================================
        # THREADS / CONTROLLERS
        # ==========================================

        self.voice_assistant = VoiceAssistant()

        self.camera_thread = CameraThread()

        # ==========================================
        # SIGNAL CONNECTIONS
        # ==========================================

        self.setup_connections()

    # ==================================================
    # SIGNAL CONNECTIONS
    # ==================================================

    def setup_connections(self):

        # ------------------------------------------
        # Dashboard buttons
        # ------------------------------------------

        self.dashboard.btn_start.clicked.connect(
            self.start_all
        )

        self.dashboard.btn_pause.clicked.connect(
            self.pause_all
        )

        self.dashboard.btn_voice.clicked.connect(
            self.toggle_voice
        )

        self.dashboard.btn_calibrate.clicked.connect(
            self.camera_thread.calibrate
        )

        # ------------------------------------------
        # Voice Assistant
        # ------------------------------------------

        self.voice_assistant.status_changed.connect(
            self.update_voice_status
        )

        self.voice_assistant.command_executed.connect(
            self.update_voice_command
        )

        self.voice_assistant.error_occurred.connect(
            self.update_voice_error
        )

        # ------------------------------------------
        # Camera
        # ------------------------------------------

        self.camera_thread.status_update.connect(
            self.update_camera_status
        )

        self.camera_thread.frame_ready.connect(
            self.update_camera_frame
        )

    # ==================================================
    # START ALL
    # ==================================================

    def start_all(self):

        # ------------------------------------------
        # Camera
        # ------------------------------------------

        if not self.camera_thread.isRunning():

            self.camera_thread.is_running = True

            self.camera_thread.start()

        self.camera_thread.set_cursor_control(
            True
        )

        # Auto-calibrate after 3 seconds
        QTimer.singleShot(3000, self.camera_thread.calibrate)

        # ------------------------------------------
        # Voice
        # ------------------------------------------

        if not self.voice_assistant.is_active():

            self.voice_assistant.start()

        # ------------------------------------------
        # Dashboard
        # ------------------------------------------

        self.dashboard.status_head.set_status(
            "Active",
            "#10B981"
        )

    # ==================================================
    # PAUSE ALL
    # ==================================================

    def pause_all(self):

        # Stop cursor movement
        self.camera_thread.set_cursor_control(
            False
        )

        self.dashboard.status_head.set_status(
            "Paused",
            "#F59E0B"
        )

        # Stop voice
        if self.voice_assistant.is_active():

            self.voice_assistant.stop()

    # ==================================================
    # VOICE ON / OFF
    # ==================================================

    def toggle_voice(self):

        if self.voice_assistant.is_active():

            self.voice_assistant.stop()

        else:

            self.voice_assistant.start()

    # ==================================================
    # VOICE STATUS
    # ==================================================

    def update_voice_status(self, status):

        if status == "Listening":

            self.dashboard.status_voice.set_status(
                "Listening",
                "#10B981"
            )

        elif status == "Inactive":

            self.dashboard.status_voice.set_status(
                "Inactive",
                "#9CA3AF"
            )

        elif "Loading" in status:

            self.dashboard.status_voice.set_status(
                "Loading",
                "#F59E0B"
            )

        else:

            self.dashboard.status_voice.set_status(
                status,
                "#9CA3AF"
            )

    # ==================================================
    # VOICE COMMAND
    # ==================================================

    def update_voice_command(
        self,
        transcript,
        command
    ):

        self.dashboard.voice_command_lbl.setText(
            f'"{transcript}"'
        )

        print(
            f"[Dashboard] Voice command: "
            f"{transcript} -> {command}"
        )

    # ==================================================
    # VOICE ERROR
    # ==================================================

    def update_voice_error(self, error):

        print(
            f"[Dashboard] Voice error: {error}"
        )

        self.dashboard.status_voice.set_status(
            "Error",
            "#EF4444"
        )

        self.dashboard.voice_command_lbl.setText(
            "Voice error"
        )

    # ==================================================
    # CAMERA STATUS
    # ==================================================

    def update_camera_status(self, status):

        if status == "Active":

            self.dashboard.status_camera.set_status(
                "Active",
                "#10B981"
            )

            self.dashboard.status_head.set_status(
                "Active",
                "#10B981"
            )

        elif status == "Inactive":

            self.dashboard.status_camera.set_status(
                "Inactive",
                "#9CA3AF"
            )

            self.dashboard.status_head.set_status(
                "Inactive",
                "#9CA3AF"
            )

        else:

            self.dashboard.status_camera.set_status(
                status,
                "#9CA3AF"
            )

    # ==================================================
    # CAMERA FRAME
    # ==================================================

    def update_camera_frame(self, q_img):

        label_width = (
            self.dashboard.camera_feed_label.width()
        )

        label_height = (
            self.dashboard.camera_feed_label.height()
        )

        scaled_img = q_img.scaled(
            label_width,
            label_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.dashboard.camera_feed_label.setPixmap(
            QPixmap.fromImage(scaled_img)
        )

    # ==================================================
    # CLOSE APPLICATION
    # ==================================================

    def closeEvent(self, event):

        print(
            "[MainWindow] Closing application..."
        )

        # Stop camera
        if self.camera_thread.isRunning():

            self.camera_thread.stop()

        # Stop voice
        if self.voice_assistant.is_active():

            self.voice_assistant.stop()

        super().closeEvent(event)