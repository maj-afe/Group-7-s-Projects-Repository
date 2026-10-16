from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QGridLayout, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, Property
from PySide6.QtGui import QPainter, QColor, QFont


class ToggleSwitch(QWidget):
    """
    Animated iOS-style toggle switch.
    Emits toggled(bool) when state changes.
    """
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedSize(58, 30)
        self.setCursor(Qt.PointingHandCursor)
        self._checked = checked
        # _handle_x: left edge of the thumb circle (0 = OFF, 28 = ON)
        self._handle_x: float = 28.0 if checked else 0.0

        self._anim = QPropertyAnimation(self, b"handle_x", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)

    # ---- Qt Property so QPropertyAnimation can drive it ----
    def _get_hx(self) -> float:
        return self._handle_x

    def _set_hx(self, v: float) -> None:
        self._handle_x = v
        self.update()

    handle_x = Property(float, _get_hx, _set_hx)

    # ---- Public ----
    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, state: bool, silent: bool = False) -> None:
        """Set state programmatically. silent=True suppresses toggled signal."""
        if state == self._checked:
            return
        self._checked = state
        self._anim.stop()
        self._anim.setStartValue(self._handle_x)
        self._anim.setEndValue(28.0 if state else 0.0)
        self._anim.start()
        if not silent:
            self.toggled.emit(state)

    # ---- Interaction ----
    def mousePressEvent(self, event):
        self.set_checked(not self._checked)

    # ---- Painting ----
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Track
        track_color = QColor("#10B981") if self._checked else QColor("#374151")
        p.setBrush(track_color)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 4, 58, 22, 11, 11)

        # Thumb
        p.setBrush(QColor("#FFFFFF"))
        thumb_x = int(self._handle_x) + 3
        p.drawEllipse(thumb_x, 5, 20, 20)
        p.end()

class SystemStatusIndicator(QWidget):
    def __init__(self, name, status, color="#10B981"):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        layout.addWidget(self.dot)
        
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #E5E7EB; font-size: 16px; font-weight: bold;")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        self.status_label = QLabel(status)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.status_label)

    def set_status(self, status, color="#10B981"):
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")
        self.dot.setStyleSheet(f"color: {color}; font-size: 14px;")

class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0B0B14;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # --- HEADER ---
        header_layout = QHBoxLayout()
        title = QLabel("BUG Assistant: Accessibility Control Center")
        title.setStyleSheet("color: #FFFFFF; font-size: 28px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Startup toggle (right side of header)
        startup_row = QHBoxLayout()
        startup_row.setSpacing(10)
        startup_lbl = QLabel("Launch on Startup")
        startup_lbl.setStyleSheet("color: #9CA3AF; font-size: 14px;")
        self.startup_toggle = ToggleSwitch(checked=False)
        self.startup_toggle.setToolTip(
            "When ON, BUG will launch automatically every time Windows starts."
        )
        startup_row.addWidget(startup_lbl)
        startup_row.addWidget(self.startup_toggle)
        header_layout.addLayout(startup_row)

        main_layout.addLayout(header_layout)
        
        # --- STATUS PANEL ---
        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #13131F; border-radius: 12px; border: 1px solid #1F1F33;")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(30, 20, 30, 20)
        
        self.status_camera = SystemStatusIndicator("Camera", "Inactive", "#9CA3AF")
        self.status_head = SystemStatusIndicator("Head Tracking", "Inactive", "#9CA3AF")
        self.status_voice = SystemStatusIndicator("Voice Recognition", "Inactive", "#9CA3AF")
        
        status_layout.addWidget(self.status_camera)
        status_layout.addSpacing(40)
        status_layout.addWidget(self.status_head)
        status_layout.addSpacing(40)
        status_layout.addWidget(self.status_voice)
        main_layout.addWidget(status_frame)
        
        # --- CAMERA FEED ---
        self.camera_feed_label = QLabel("Click 'Start All Systems' to begin.")
        self.camera_feed_label.setAlignment(Qt.AlignCenter)
        self.camera_feed_label.setStyleSheet("background-color: #05050A; border-radius: 12px; border: 2px solid #1F1F33; color: #6B7280; font-size: 18px;")
        self.camera_feed_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.camera_feed_label.setMinimumHeight(400)
        main_layout.addWidget(self.camera_feed_label, stretch=1)
        
        # --- BOTTOM CONTROLS & VOICE LOG ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        
        # Buttons Frame
        btn_frame = QFrame()
        btn_layout = QGridLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(15)
        
        self.btn_start = self.create_large_btn("Start All Systems", "#10472D", "#10B981")
        self.btn_pause = self.create_large_btn("Pause Systems", "#472A1A", "#F59E0B")
        self.btn_calibrate = self.create_large_btn("Calibrate Center", "#1A2E47", "#3B82F6")
        self.btn_voice = self.create_large_btn("Toggle Voice Only", "#2E1A47", "#8B5CF6")
        
        btn_layout.addWidget(self.btn_start, 0, 0)
        btn_layout.addWidget(self.btn_pause, 0, 1)
        btn_layout.addWidget(self.btn_calibrate, 1, 0)
        btn_layout.addWidget(self.btn_voice, 1, 1)
        
        bottom_layout.addWidget(btn_frame, stretch=2)
        
        # Voice Log Frame
        voice_frame = QFrame()
        voice_frame.setStyleSheet("background-color: #13131F; border-radius: 12px; border: 1px solid #1F1F33;")
        voice_layout = QVBoxLayout(voice_frame)
        
        voice_title = QLabel("Last Voice Command:")
        voice_title.setStyleSheet("color: #9CA3AF; font-size: 16px; border: none;")
        self.voice_command_lbl = QLabel("None")
        self.voice_command_lbl.setStyleSheet("color: #FFFFFF; font-size: 32px; font-weight: bold; border: none;")
        self.voice_command_lbl.setAlignment(Qt.AlignCenter)
        self.voice_command_lbl.setWordWrap(True)
        
        voice_layout.addWidget(voice_title)
        voice_layout.addWidget(self.voice_command_lbl, stretch=1, alignment=Qt.AlignCenter)
        
        bottom_layout.addWidget(voice_frame, stretch=1)
        main_layout.addLayout(bottom_layout)

    def create_large_btn(self, text, bg_color, border_color):
        btn = QPushButton(text)
        btn.setMinimumHeight(80)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
                border: 2px solid {border_color};
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: {border_color};
            }}
        """)
        return btn
