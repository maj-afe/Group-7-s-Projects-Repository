# app/ui/learn_dialog.py
"""
Self-learning voice alias training dialog.

Shown automatically when the user says an unrecognized phrase
3 times in a row. Lets the user map the phrase to any known command
and saves the mapping permanently to data/learned_aliases.json.

Also includes a "My Commands" view to review and delete trained aliases.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit,
    QPushButton, QFrame, QListWidget,
    QListWidgetItem, QStackedWidget, QWidget,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from app.voice.command_handler import CommandHandler

# ─────────────────────────────────────────────────────────
# STYLE CONSTANTS
# ─────────────────────────────────────────────────────────
_BG        = "#0F1117"
_PANEL     = "#1A1D2E"
_ACCENT    = "#6366F1"        # indigo
_ACCENT2   = "#10B981"        # green
_DANGER    = "#EF4444"        # red
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
QComboBox {{
    background: {_PANEL};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    min-height: 32px;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background: {_PANEL};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    selection-background-color: {_ACCENT};
    outline: none;
}}
QLineEdit {{
    background: {_PANEL};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    min-height: 32px;
}}
QPushButton {{
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
    min-width: 90px;
}}
QPushButton#btn_save {{
    background: {_ACCENT};
    color: white;
    border: none;
}}
QPushButton#btn_save:hover {{
    background: #7C3AED;
}}
QPushButton#btn_ignore {{
    background: transparent;
    color: {_MUTED};
    border: 1px solid {_BORDER};
}}
QPushButton#btn_ignore:hover {{
    color: {_TEXT};
    border-color: {_MUTED};
}}
QPushButton#btn_delete {{
    background: {_DANGER};
    color: white;
    border: none;
    min-width: 70px;
    padding: 5px 12px;
    font-size: 12px;
}}
QPushButton#btn_delete:hover {{
    background: #DC2626;
}}
QPushButton#btn_view {{
    background: transparent;
    color: {_ACCENT};
    border: none;
    font-size: 12px;
    padding: 2px 6px;
    min-width: 0;
    text-decoration: underline;
}}
QPushButton#btn_view:hover {{
    color: #818CF8;
}}
QListWidget {{
    background: {_PANEL};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 4px;
    font-size: 12px;
}}
QListWidget::item {{
    padding: 4px 6px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background: {_ACCENT};
}}
QFrame#divider {{
    background: {_BORDER};
    max-height: 1px;
}}
"""


class LearnAliasDialog(QDialog):
    """
    Modal dialog that pops up when the user says an unrecognized
    phrase 3 times. Allows mapping the phrase to a command.

    Usage:
        dlg = LearnAliasDialog(phrase, command_handler, parent=self)
        dlg.exec()
    """

    alias_saved = Signal(str, str)   # (phrase, command_key)

    def __init__(
        self,
        phrase: str,
        voice_assistant,
        parent=None,
    ):
        super().__init__(parent)
        self._phrase  = phrase
        self._voice_assistant = voice_assistant
        self._handler = voice_assistant.command_handler
        self._is_listening = False

        self.setWindowTitle("BUG — Teach Me a New Command")
        self.setMinimumWidth(480)
        self.setStyleSheet(_STYLE)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowCloseButtonHint
        )

        self._build_ui()

    # ─────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Stack: page 0 = Learn, page 1 = My Commands
        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._stack.addWidget(self._build_learn_page())
        self._stack.addWidget(self._build_my_commands_page())

    def _section_label(self, text: str, size: int = 13) -> QLabel:
        lbl = QLabel(text)
        font = QFont("Segoe UI", size)
        lbl.setFont(font)
        lbl.setStyleSheet(f"color: {_MUTED};")
        return lbl

    def _divider(self):
        f = QFrame()
        f.setObjectName("divider")
        f.setFrameShape(QFrame.HLine)
        return f

    # ── PAGE 0: LEARN ────────────────────────────────────────

    def _build_learn_page(self) -> QWidget:
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setSpacing(16)
        lay.setContentsMargins(28, 28, 28, 24)

        # Header
        icon_lbl = QLabel("🎤")
        icon_lbl.setFont(QFont("Segoe UI", 26))
        icon_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon_lbl)

        title = QLabel("Teach Me a New Command")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {_TEXT};")
        lay.addWidget(title)

        lay.addWidget(self._divider())

        # Phrase display
        if self._phrase:
            lay.addWidget(self._section_label("You said this 3 times without a match:"))
            phrase_box = QLabel(f'"{self._phrase}"')
            phrase_box.setFont(QFont("Segoe UI Semibold", 14))
            phrase_box.setAlignment(Qt.AlignCenter)
            phrase_box.setStyleSheet(
                f"color: {_ACCENT};"
                f"background: {_PANEL};"
                f"border: 1px solid {_BORDER};"
                "border-radius: 8px;"
                "padding: 10px 16px;"
            )
            phrase_box.setWordWrap(True)
            lay.addWidget(phrase_box)
        else:
            lay.addWidget(self._section_label("Say the phrase you want to train (or type it):"))
            
            input_row = QHBoxLayout()
            self._phrase_input = QLineEdit()
            self._phrase_input.setPlaceholderText("e.g. 'open calendar'")
            self._phrase_input.setStyleSheet(
                f"color: {_ACCENT};"
                f"background: {_PANEL};"
                f"border: 1px solid {_BORDER};"
                "border-radius: 8px;"
                "padding: 10px 16px;"
                "font-size: 16px; font-weight: bold;"
            )
            
            self._btn_listen = QPushButton("🎤 Listen")
            self._btn_listen.setCheckable(True)
            self._btn_listen.setStyleSheet(
                "QPushButton { background: transparent; border: 1px solid " + _ACCENT + f"; color: {_ACCENT}; font-size: 13px; font-weight: bold; border-radius: 8px; padding: 10px 16px; }}"
                "QPushButton:checked { background: " + _DANGER + "; color: white; border: none; }"
            )
            self._btn_listen.clicked.connect(self._toggle_listen)
            
            input_row.addWidget(self._phrase_input, stretch=1)
            input_row.addWidget(self._btn_listen)
            lay.addLayout(input_row)

        # Command picker
        lay.addWidget(self._section_label("What should this phrase do?"))

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("🔍  Filter commands…")
        self._search_box.textChanged.connect(self._filter_commands)
        lay.addWidget(self._search_box)

        self._combo = QComboBox()
        self._combo.setMaxVisibleItems(12)
        self._populate_combo(CommandHandler.ALL_COMMANDS)
        lay.addWidget(self._combo)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_ignore = QPushButton("Ignore")
        btn_ignore.setObjectName("btn_ignore")
        btn_ignore.clicked.connect(self._on_ignore)
        btn_row.addWidget(btn_ignore)

        btn_row.addStretch()

        # Link to My Commands page
        btn_view = QPushButton("My Commands →")
        btn_view.setObjectName("btn_view")
        btn_view.clicked.connect(lambda: self._stack.setCurrentIndex(1))
        btn_row.addWidget(btn_view)

        btn_save = QPushButton("Save")
        btn_save.setObjectName("btn_save")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)

        lay.addLayout(btn_row)

        # Tip
        tip = QLabel("💡 After saving, this phrase will instantly trigger that command every time.")
        tip.setWordWrap(True)
        tip.setStyleSheet(f"color: {_MUTED}; font-size: 11px;")
        lay.addWidget(tip)

        return page

    # ── PAGE 1: MY COMMANDS ──────────────────────────────────

    def _build_my_commands_page(self) -> QWidget:
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setSpacing(12)
        lay.setContentsMargins(28, 24, 28, 24)

        # Header row
        hdr = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("btn_view")
        back_btn.clicked.connect(self._show_learn_page)
        hdr.addWidget(back_btn)

        hdr.addStretch()

        title = QLabel("My Trained Commands")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet(f"color: {_TEXT};")
        hdr.addWidget(title)

        hdr.addStretch()

        lay.addLayout(hdr)
        lay.addWidget(self._divider())

        empty_hint = QLabel("No trained commands yet. Save a phrase to see it here.")
        empty_hint.setStyleSheet(f"color: {_MUTED}; font-size: 12px;")
        empty_hint.setAlignment(Qt.AlignCenter)
        empty_hint.setWordWrap(True)
        lay.addWidget(empty_hint)
        self._empty_hint = empty_hint

        self._alias_list = QListWidget()
        self._alias_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self._alias_list)

        # Delete selected button
        del_row = QHBoxLayout()
        del_row.addStretch()
        self._btn_delete = QPushButton("Delete Selected")
        self._btn_delete.setObjectName("btn_delete")
        self._btn_delete.clicked.connect(self._on_delete)
        del_row.addWidget(self._btn_delete)
        lay.addLayout(del_row)

        return page

    # ─────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────

    def _populate_combo(self, commands):
        self._combo.clear()
        for cmd in sorted(commands):
            self._combo.addItem(cmd)

    def _filter_commands(self, text: str):
        text = text.lower().strip()
        filtered = [
            c for c in CommandHandler.ALL_COMMANDS
            if text in c
        ]
        self._populate_combo(filtered if filtered else CommandHandler.ALL_COMMANDS)

    def _show_learn_page(self):
        self._refresh_alias_list()
        self._stack.setCurrentIndex(0)

    def _refresh_alias_list(self):
        """Reload the My Commands list from the handler."""
        aliases = self._handler.get_learned_aliases()
        self._alias_list.clear()

        if not aliases:
            self._empty_hint.setVisible(True)
            self._btn_delete.setEnabled(False)
        else:
            self._empty_hint.setVisible(False)
            self._btn_delete.setEnabled(True)
            for phrase, cmd in sorted(aliases.items()):
                item = QListWidgetItem(f'"{phrase}"  →  {cmd}')
                item.setData(Qt.UserRole, phrase)
                self._alias_list.addItem(item)

    def showEvent(self, event):
        """Refresh alias list whenever the dialog becomes visible."""
        super().showEvent(event)
        self._refresh_alias_list()
        
    def hideEvent(self, event):
        """Ensure we stop listening if the dialog is closed."""
        if hasattr(self, "_is_listening") and self._is_listening:
            self._stop_listening()
        super().hideEvent(event)

    # ─────────────────────────────────────────────────────────
    # ACTIONS
    # ─────────────────────────────────────────────────────────

    def _toggle_listen(self):
        if self._btn_listen.isChecked():
            self._btn_listen.setText("Listening...")
            self._phrase_input.setPlaceholderText("Speak now...")
            self._phrase_input.clear()
            self._is_listening = True
            self._voice_assistant.set_training_mode(True)
            self._voice_assistant.raw_transcript_heard.connect(self._on_voice_heard)
        else:
            self._stop_listening()

    def _on_voice_heard(self, transcript: str):
        if not self._is_listening:
            return
        
        # We got a phrase! Fill it in and stop listening.
        self._phrase_input.setText(transcript)
        self._stop_listening()

    def _stop_listening(self):
        self._is_listening = False
        self._btn_listen.setChecked(False)
        self._btn_listen.setText("🎤 Listen")
        self._phrase_input.setPlaceholderText("e.g. 'open calendar'")
        self._voice_assistant.set_training_mode(False)
        try:
            self._voice_assistant.raw_transcript_heard.disconnect(self._on_voice_heard)
        except Exception:
            pass

    def _on_save(self):
        phrase = self._phrase
        if not phrase and hasattr(self, "_phrase_input"):
            phrase = self._phrase_input.text().strip()
            
        if not phrase:
            return
            
        command_key = self._combo.currentText()
        if not command_key:
            return
            
        self._handler.add_alias(phrase, command_key)
        self._voice_assistant.update_grammar()
        self.alias_saved.emit(phrase, command_key)
        self.accept()

    def _on_ignore(self):
        self._handler.ignore_phrase(self._phrase)
        self.reject()

    def _on_delete(self):
        item = self._alias_list.currentItem()
        if not item:
            return
        phrase = item.data(Qt.UserRole)
        self._handler.delete_alias(phrase)
        self._refresh_alias_list()
