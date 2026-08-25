# app/ui/wizard_dialog.py
"""
Guided Voice Setup Wizard.

Walks the user through a list of essential commands,
listens to how they say them, and maps the exact heard transcript
to the command automatically.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QWidget, QProgressBar, QComboBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from app.voice.command_handler import CommandHandler

# ─────────────────────────────────────────────────────────
# STYLE CONSTANTS (matching learn_dialog)
# ─────────────────────────────────────────────────────────
_BG        = "#0F1117"
_PANEL     = "#1A1D2E"
_ACCENT    = "#6366F1"        # indigo
_SUCCESS   = "#10B981"        # green
_TEXT      = "#F1F5F9"
_MUTED     = "#64748B"
_BORDER    = "#2D3148"

_STYLE = f"""
QDialog {{
    background: {_BG};
    color: {_TEXT};
    font-family: 'Segoe UI', sans-serif;
}}
QLabel {{
    color: {_TEXT};
    background: transparent;
}}
QPushButton {{
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton#btn_primary {{
    background: {_ACCENT};
    color: white;
    border: none;
}}
QPushButton#btn_primary:hover {{
    background: #7C3AED;
}}
QPushButton#btn_skip {{
    background: transparent;
    color: {_MUTED};
    border: 1px solid {_BORDER};
}}
QPushButton#btn_skip:hover {{
    color: {_TEXT};
    border-color: {_MUTED};
}}
QProgressBar {{
    background: {_PANEL};
    border: 1px solid {_BORDER};
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {_ACCENT};
    border-radius: 3px;
}}
QFrame#divider {{
    background: {_BORDER};
    max-height: 1px;
}}
"""


class VoiceSetupWizard(QDialog):
    """
    Guided wizard that iterates through a preset list of commands,
    listens to the user, and trains them.
    """

    # The sequence of commands to train
    STEPS = [
        # Mouse
        {"cmd": "click",          "display": "Click"},
        {"cmd": "double_click",   "display": "Double Click"},
        {"cmd": "right_click",    "display": "Right Click"},
        # Scrolling
        {"cmd": "scroll_down",    "display": "Scroll Down"},
        {"cmd": "scroll_up",      "display": "Scroll Up"},
        # Navigation
        {"cmd": "go_back",        "display": "Go Back"},
        {"cmd": "new_tab",        "display": "New Tab"},
        {"cmd": "close_tab",      "display": "Close Tab"},
        {"cmd": "switch_window",  "display": "Switch Window"},
        {"cmd": "close_window",   "display": "Close Window"},
        {"cmd": "minimize",       "display": "Minimize Window"},
        # Media
        {"cmd": "play_pause",     "display": "Play Pause"},
        {"cmd": "volume_up",      "display": "Volume Up"},
        {"cmd": "volume_down",    "display": "Volume Down"},
        # Dictation
        {"cmd": "start_typing",   "display": "Start Typing"},
        {"cmd": "stop_typing",    "display": "Stop Typing"},
        # Safety
        {"cmd": "emergency_stop", "display": "Emergency Stop"},
        {"cmd": "control_enabled","display": "Enable Control"},
    ]
    
    ADVANCED_STEPS = [
        {"cmd": "copy",           "display": "Copy"},
        {"cmd": "paste",          "display": "Paste"},
        {"cmd": "undo",           "display": "Undo"},
        {"cmd": "select_all",     "display": "Select All"},
        {"cmd": "mute",           "display": "Mute"},
        {"cmd": "unmute",         "display": "Unmute"},
        {"cmd": "save",           "display": "Save"},
        {"cmd": "new_file",       "display": "New File"},
        {"cmd": "open_file",      "display": "Open File"},
        {"cmd": "open_start_menu","display": "Open Start Menu"},
        {"cmd": "zoom_in",        "display": "Zoom In"},
        {"cmd": "zoom_out",       "display": "Zoom Out"},
        {"cmd": "refresh",        "display": "Refresh Page"},
        {"cmd": "open_youtube",   "display": "Open YouTube"},
        {"cmd": "open_google",    "display": "Open Google"},
    ]

    def __init__(self, voice_assistant, parent=None):
        super().__init__(parent)
        self._voice = voice_assistant
        self._handler = voice_assistant.command_handler
        self._current_step = 0
        self._is_listening = False

        self.setWindowTitle("BUG — Voice Setup Wizard")
        self.setFixedSize(500, 360)
        self.setStyleSheet(_STYLE)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        self._build_ui()
        self._load_step(0)

    # ─────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(15)

        # Header
        self._title = QLabel("Voice Training Wizard")
        self._title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self._title.setAlignment(Qt.AlignCenter)
        root.addWidget(self._title)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setMaximum(len(self.STEPS))
        self._progress.setValue(0)
        root.addWidget(self._progress)

        div = QFrame()
        div.setObjectName("divider")
        div.setFrameShape(QFrame.HLine)
        root.addWidget(div)

        # Main content area
        self._content_stack = QStackedWidget()
        root.addWidget(self._content_stack)

        # 1. Training Page
        self._page_train = QWidget()
        train_lay = QVBoxLayout(self._page_train)
        train_lay.setContentsMargins(0, 20, 0, 20)

        self._lbl_instruction = QLabel("Please say exactly:")
        self._lbl_instruction.setStyleSheet(f"color: {_MUTED}; font-size: 14px;")
        self._lbl_instruction.setAlignment(Qt.AlignCenter)
        train_lay.addWidget(self._lbl_instruction)

        self._lbl_target = QLabel('"Scroll Down"')
        self._lbl_target.setFont(QFont("Segoe UI Semibold", 22))
        self._lbl_target.setStyleSheet(f"color: {_ACCENT};")
        self._lbl_target.setAlignment(Qt.AlignCenter)
        train_lay.addWidget(self._lbl_target)

        train_lay.addStretch()

        self._lbl_status = QLabel("🎤 Listening...")
        self._lbl_status.setFont(QFont("Segoe UI", 14))
        self._lbl_status.setStyleSheet("color: #F87171;")  # red pulse color
        self._lbl_status.setAlignment(Qt.AlignCenter)
        train_lay.addWidget(self._lbl_status)
        
        train_lay.addSpacing(10)
        
        self._lbl_skip_hint = QLabel("💡 Tip: You can say 'skip step' to skip")
        self._lbl_skip_hint.setStyleSheet(f"color: {_MUTED}; font-size: 12px;")
        self._lbl_skip_hint.setAlignment(Qt.AlignCenter)
        train_lay.addWidget(self._lbl_skip_hint)
        
        self._content_stack.addWidget(self._page_train)

        # 2. Success Page (flashes briefly)
        self._page_success = QWidget()
        success_lay = QVBoxLayout(self._page_success)
        
        self._lbl_check = QLabel("✅")
        self._lbl_check.setFont(QFont("Segoe UI", 48))
        self._lbl_check.setAlignment(Qt.AlignCenter)
        success_lay.addWidget(self._lbl_check)
        
        self._lbl_captured = QLabel("Captured: 'sold out'")
        self._lbl_captured.setFont(QFont("Segoe UI Semibold", 16))
        self._lbl_captured.setStyleSheet(f"color: {_SUCCESS};")
        self._lbl_captured.setAlignment(Qt.AlignCenter)
        success_lay.addWidget(self._lbl_captured)
        
        self._content_stack.addWidget(self._page_success)

        # 3. Done Page
        self._page_done = QWidget()
        done_lay = QVBoxLayout(self._page_done)
        
        done_icon = QLabel("🎉")
        done_icon.setFont(QFont("Segoe UI", 48))
        done_icon.setAlignment(Qt.AlignCenter)
        done_lay.addWidget(done_icon)
        
        done_lbl = QLabel("Setup Complete!")
        done_lbl.setFont(QFont("Segoe UI Semibold", 18))
        done_lbl.setStyleSheet(f"color: {_TEXT};")
        done_lbl.setAlignment(Qt.AlignCenter)
        done_lay.addWidget(done_lbl)
        
        done_desc = QLabel("Your voice model is now personalized for you.")
        done_desc.setStyleSheet(f"color: {_MUTED}; font-size: 14px;")
        done_desc.setAlignment(Qt.AlignCenter)
        done_lay.addWidget(done_desc)
        
        done_lay.addSpacing(15)
        
        self._btn_train_more = QPushButton("Train Advanced Commands")
        self._btn_train_more.setObjectName("btn_primary")
        self._btn_train_more.clicked.connect(self._start_advanced_training)
        done_lay.addWidget(self._btn_train_more, alignment=Qt.AlignCenter)
        
        self._content_stack.addWidget(self._page_done)

        # Buttons
        btn_row = QHBoxLayout()
        self._btn_skip = QPushButton("Skip Word")
        self._btn_skip.setObjectName("btn_skip")
        self._btn_skip.clicked.connect(self._skip_step)
        
        self._btn_finish = QPushButton("Finish")
        self._btn_finish.setObjectName("btn_primary")
        self._btn_finish.clicked.connect(self.accept)
        self._btn_finish.setVisible(False)
        
        btn_row.addWidget(self._btn_skip)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_finish)
        
        root.addLayout(btn_row)

    # ─────────────────────────────────────────────────────────
    # LOGIC
    # ─────────────────────────────────────────────────────────

    def _load_step(self, index: int):
        self._current_step = index
        self._progress.setValue(index)

        if index >= len(self.STEPS):
            self._finish_wizard()
            return

        step_data = self.STEPS[index]
        self._lbl_target.setText(f'"{step_data["display"]}"')
        self._content_stack.setCurrentWidget(self._page_train)
        
        self._start_listening()

    def _start_listening(self):
        if self._is_listening:
            return
        self._is_listening = True
        self._lbl_status.setText("🎤 Listening...")
        self._lbl_status.setStyleSheet("color: #F87171;")
        
        self._voice.set_training_mode(True)
        # Connect strictly to the raw recognized command
        self._voice.raw_transcript_heard.connect(self._on_voice_heard)

    def _stop_listening(self):
        if not self._is_listening:
            return
        self._is_listening = False
        self._voice.set_training_mode(False)
        try:
            self._voice.raw_transcript_heard.disconnect(self._on_voice_heard)
        except Exception:
            pass

    def _on_voice_heard(self, transcript: str):
        if not self._is_listening:
            return
            
        # Ignore random 1-letter noise that might leak through
        if len(transcript) < 2:
            return

        # Hands-free navigation!
        if transcript == "skip step":
            self._skip_step()
            return

        self._stop_listening()
        
        # Save mapping
        target_cmd = self.STEPS[self._current_step]["cmd"]
        self._handler.add_alias(transcript, target_cmd)
        self._voice.update_grammar()
        
        # Flash success
        self._lbl_captured.setText(f"Heard: '{transcript}'")
        self._content_stack.setCurrentWidget(self._page_success)
        
        # Move to next step after 1.5s
        QTimer.singleShot(1500, lambda: self._load_step(self._current_step + 1))

    def _skip_step(self):
        self._stop_listening()
        self._load_step(self._current_step + 1)

    def _finish_wizard(self):
        self._stop_listening()
        self._progress.setValue(len(self.STEPS))
        self._content_stack.setCurrentWidget(self._page_done)
        self._btn_skip.setVisible(False)
        self._btn_finish.setVisible(True)

    def _start_advanced_training(self):
        """Append advanced steps to the list and seamlessly continue the wizard loop."""
        self._btn_train_more.setVisible(False)
        
        resume_index = len(self.STEPS)
        self.STEPS.extend(self.ADVANCED_STEPS)
        self._progress.setMaximum(len(self.STEPS))
        
        self._btn_skip.setVisible(True)
        self._btn_finish.setVisible(False)
        
        self._load_step(resume_index)

    def hideEvent(self, event):
        self._stop_listening()
        super().hideEvent(event)
