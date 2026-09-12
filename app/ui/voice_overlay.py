# app/ui/voice_overlay.py
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation

class VoiceOverlay(QWidget):
    def __init__(self):
        super().__init__()
        
        # Make it a borderless, always-on-top window that doesn't steal focus
        self.setWindowFlags(
            Qt.WindowType.Tool | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Label
        self.label = QLabel("")
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(20, 20, 20, 230);
                color: #10B981;
                border: 1px solid #374151;
                border-radius: 12px;
                padding: 15px 25px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        # Timer for starting fade out
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.start_fade_out)
        
        # Animation for fade out
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(500)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.finished.connect(self.hide)
        
    def show_message(self, text, duration=3000):
        # Stop any ongoing animation
        self.fade_anim.stop()
        
        self.label.setText(f'🎤 "{text}"')
        self.label.adjustSize()
        self.adjustSize()
        
        # Position in bottom-right corner of the primary screen
        screen = QApplication.primaryScreen().geometry()
        margin = 30
        taskbar_approx_height = 60
        x = screen.width() - self.width() - margin
        y = screen.height() - self.height() - margin - taskbar_approx_height
        self.move(x, y)
        
        self.setWindowOpacity(1.0)
        self.show()
        
        # Restart timer
        self.hide_timer.start(duration)
        
    def start_fade_out(self):
        self.fade_anim.start()
