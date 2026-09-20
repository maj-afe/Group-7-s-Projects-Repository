# app/ui/perf_panel.py
"""
Real-time performance diagnostics panel.

Layout
------
┌─────────────────────────────────────────────────────────────────────┐
│  ⚡ Performance Monitor              [Reset Log]  [Copy Stats Log]  │
├──────────────────┬──────────────────┬──────────────────┬────────────┤
│  📷 Camera        │  🎙 Voice / VAD   │  🧠 Whisper       │  ⚡ Cmds   │
│  FPS: 28.4       │  Segments: 42    │  Last:  312 ms   │  Total: 7  │
│  Detect: 18 ms   │  Dropped: 3 (7%) │  Avg:   380 ms   │  Unknown:0 │
│  Cursor: 0.3 ms  │  Last seg: 980ms │                  │  Rate: 0%  │
├──────────────────┴──────────────────┴──────────────────┴────────────┤
│  🔁 End-to-End Voice Latency:  1420 ms   Dispatch: 0.4 ms           │
│  🔊 Audio Overflows: 0                   Log rows: 47               │
└─────────────────────────────────────────────────────────────────────┘

Color thresholds
----------------
Camera FPS:      ≥25 green, 15-25 yellow, <15 red
Face detect:     <20ms green, 20-50ms yellow, >50ms red
Whisper last:    <500ms green, 500-1000ms yellow, >1000ms red
E2E:             <2000ms green, 2000-3500ms yellow, >3500ms red
Unknown rate:    <10% green, 10-30% yellow, >30% red
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from app.core.perf_monitor import PerfMonitor


# ---------------------------------------------------------------------------
# Color thresholds
# ---------------------------------------------------------------------------

def _fps_color(v: float) -> str:
    if v >= 25: return "#10B981"
    if v >= 15: return "#F59E0B"
    return "#EF4444"

def _detect_color(v: float) -> str:
    if v < 20:  return "#10B981"
    if v < 50:  return "#F59E0B"
    return "#EF4444"

def _whisper_color(v: float) -> str:
    if v < 500:  return "#10B981"
    if v < 1000: return "#F59E0B"
    return "#EF4444"

def _e2e_color(v: float) -> str:
    if v < 2000:  return "#10B981"
    if v < 3500:  return "#F59E0B"
    return "#EF4444"

def _pct_color(v: float) -> str:
    if v < 10:  return "#10B981"
    if v < 30:  return "#F59E0B"
    return "#EF4444"

def _overflow_color(v: int) -> str:
    if v == 0: return "#10B981"
    if v < 5:  return "#F59E0B"
    return "#EF4444"

def _generic_good() -> str:
    return "#10B981"

def _dim() -> str:
    return "#9CA3AF"


# ---------------------------------------------------------------------------
# Small metric tile
# ---------------------------------------------------------------------------

class _MetricTile(QWidget):
    """A labelled metric with a colored value."""

    def __init__(self, label: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 2)
        layout.setSpacing(1)

        self._label = QLabel(label)
        self._label.setStyleSheet("color: #6B7280; font-size: 11px;")
        self._label.setAlignment(Qt.AlignLeft)

        self._value = QLabel("—")
        self._value.setStyleSheet("color: #9CA3AF; font-size: 14px; font-weight: bold;")
        self._value.setAlignment(Qt.AlignLeft)

        layout.addWidget(self._label)
        layout.addWidget(self._value)

    def update(self, text: str, color: str):
        self._value.setText(text)
        self._value.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: bold;"
        )


# ---------------------------------------------------------------------------
# Section card (groups several metric tiles)
# ---------------------------------------------------------------------------

class _SectionCard(QFrame):
    def __init__(self, title: str, icon: str):
        super().__init__()
        self.setStyleSheet(
            "background-color: #0D0D1A; border-radius: 10px; "
            "border: 1px solid #1F1F33;"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)

        hdr = QLabel(f"{icon}  {title}")
        hdr.setStyleSheet(
            "color: #E5E7EB; font-size: 13px; font-weight: bold; border: none;"
        )
        outer.addWidget(hdr)

        self._grid = QGridLayout()
        self._grid.setSpacing(10)
        outer.addLayout(self._grid)
        self._tiles: dict[str, _MetricTile] = {}

    def add_tile(self, key: str, label: str, row: int, col: int) -> "_MetricTile":
        tile = _MetricTile(label)
        self._grid.addWidget(tile, row, col)
        self._tiles[key] = tile
        return tile

    def tile(self, key: str) -> _MetricTile:
        return self._tiles[key]


# ---------------------------------------------------------------------------
# Main PerfPanel widget
# ---------------------------------------------------------------------------

class PerfPanel(QWidget):
    """
    Always-visible real-time performance panel.

    Call `update_metrics(snap)` (or let the internal QTimer do it).
    Wire camera/voice perf signals in main_window.py.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pm = PerfMonitor.instance()
        self._build_ui()

        # Internal timer — snapshots PerfMonitor every second
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # ---- Header row ----
        hdr = QHBoxLayout()

        title = QLabel("⚡  Performance Monitor")
        title.setStyleSheet(
            "color: #E5E7EB; font-size: 15px; font-weight: bold;"
        )
        hdr.addWidget(title)
        hdr.addStretch()

        self._log_count_lbl = QLabel("Log: 0 rows")
        self._log_count_lbl.setStyleSheet("color: #6B7280; font-size: 12px;")
        hdr.addWidget(self._log_count_lbl)
        hdr.addSpacing(10)

        btn_reset = self._make_btn("Reset Log", "#1F1F33", "#6B7280")
        btn_reset.clicked.connect(self._on_reset)
        hdr.addWidget(btn_reset)

        self._btn_copy = self._make_btn("📋  Copy Stats Log", "#1A2E47", "#3B82F6")
        self._btn_copy.clicked.connect(self._on_copy)
        hdr.addWidget(self._btn_copy)

        root.addLayout(hdr)

        # ---- Cards row ----
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        # Camera card
        self._cam = _SectionCard("Camera", "📷")
        self._cam.add_tile("fps",    "FPS",            0, 0)
        self._cam.add_tile("detect", "Face detect",    1, 0)
        self._cam.add_tile("cursor", "Cursor move",    2, 0)
        cards_layout.addWidget(self._cam)

        # VAD card
        self._vad = _SectionCard("Voice Activity (VAD)", "🎙")
        self._vad.add_tile("total",   "Segments total", 0, 0)
        self._vad.add_tile("dropped", "Noise-dropped",  1, 0)
        self._vad.add_tile("last_ms", "Last seg dur",   2, 0)
        cards_layout.addWidget(self._vad)

        # Whisper card
        self._wh = _SectionCard("Whisper ASR", "🧠")
        self._wh.add_tile("last",    "Last latency",   0, 0)
        self._wh.add_tile("avg",     "Avg latency",    1, 0)
        self._wh.add_tile("count",   "Transcriptions", 2, 0)
        cards_layout.addWidget(self._wh)

        # Commands card
        self._cmd = _SectionCard("Commands", "⚡")
        self._cmd.add_tile("total",    "Total cmds",    0, 0)
        self._cmd.add_tile("unknown",  "Unknown cmds",  1, 0)
        self._cmd.add_tile("unk_pct",  "Unknown rate",  2, 0)
        cards_layout.addWidget(self._cmd)

        root.addLayout(cards_layout)

        # ---- Bottom summary row ----
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet(
            "background-color: #0D0D1A; border-radius: 8px; border: 1px solid #1F1F33;"
        )
        bot = QHBoxLayout(bottom_frame)
        bot.setContentsMargins(14, 8, 14, 8)
        bot.setSpacing(30)

        self._e2e_lbl       = self._summary_item(bot, "🔁 E2E Voice Latency")
        self._dispatch_lbl  = self._summary_item(bot, "⚡ Dispatch")
        self._overflow_lbl  = self._summary_item(bot, "🔊 Audio Overflows")

        root.addWidget(bottom_frame)

    def _make_btn(self, text: str, bg: str, border: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid {border};
                border-radius: 6px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {border};
            }}
            QPushButton:pressed {{
                opacity: 0.8;
            }}
        """)
        return btn

    def _summary_item(self, layout: QHBoxLayout, label: str) -> QLabel:
        """Add a label+value pair to the bottom summary row; return value label."""
        col = QVBoxLayout()
        col.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #6B7280; font-size: 11px; border: none;")
        val = QLabel("—")
        val.setStyleSheet("color: #9CA3AF; font-size: 14px; font-weight: bold; border: none;")
        col.addWidget(lbl)
        col.addWidget(val)
        layout.addLayout(col)
        return val

    # ------------------------------------------------------------------
    # Tick (called every second by QTimer)
    # ------------------------------------------------------------------

    def _tick(self):
        snap = self._pm.snapshot()
        self._apply(snap)
        self._log_count_lbl.setText(f"Log: {len(self._pm._history)} rows")

    def _apply(self, s: dict):
        # Camera
        self._cam.tile("fps").update(
            f"{s['camera_fps']} fps", _fps_color(s['camera_fps']))
        self._cam.tile("detect").update(
            f"{s['face_detect_ms']} ms", _detect_color(s['face_detect_ms']))
        self._cam.tile("cursor").update(
            f"{s['cursor_ms']} ms", _generic_good())

        # VAD
        self._vad.tile("total").update(
            str(s['vad_total']), _dim())
        self._vad.tile("dropped").update(
            f"{s['vad_dropped']}  ({s['vad_noise_pct']}%)",
            _pct_color(s['vad_noise_pct']))
        self._vad.tile("last_ms").update(
            f"{int(s['vad_last_ms'])} ms", _dim())

        # Whisper
        self._wh.tile("last").update(
            f"{int(s['whisper_last_ms'])} ms", _whisper_color(s['whisper_last_ms']))
        self._wh.tile("avg").update(
            f"{int(s['whisper_avg_ms'])} ms", _whisper_color(s['whisper_avg_ms']))
        self._wh.tile("count").update(
            str(s['vad_total'] - s['vad_dropped']), _dim())

        # Commands
        self._cmd.tile("total").update(str(s['cmd_total']), _dim())
        self._cmd.tile("unknown").update(str(s['cmd_unknown']), _dim())
        self._cmd.tile("unk_pct").update(
            f"{s['cmd_unknown_pct']}%", _pct_color(s['cmd_unknown_pct']))

        # Bottom row
        e2e = s['e2e_ms']
        self._e2e_lbl.setText(
            f"{int(e2e)} ms" if e2e > 0 else "—")
        self._e2e_lbl.setStyleSheet(
            f"color: {_e2e_color(e2e)}; font-size: 14px; font-weight: bold; border: none;"
            if e2e > 0 else
            "color: #9CA3AF; font-size: 14px; font-weight: bold; border: none;"
        )

        self._dispatch_lbl.setText(f"{s['cmd_dispatch_ms']} ms")
        self._dispatch_lbl.setStyleSheet(
            "color: #10B981; font-size: 14px; font-weight: bold; border: none;"
        )

        ov = s['audio_overflows']
        self._overflow_lbl.setText(str(ov))
        self._overflow_lbl.setStyleSheet(
            f"color: {_overflow_color(ov)}; font-size: 14px; font-weight: bold; border: none;"
        )

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------

    def _on_copy(self):
        """Copy the full per-second CSV log to the system clipboard."""
        csv_text = self._pm.export_csv()
        QApplication.clipboard().setText(csv_text)

        # Brief visual feedback on the button
        self._btn_copy.setText("✅  Copied!")
        QTimer.singleShot(2000, lambda: self._btn_copy.setText("📋  Copy Stats Log"))

    def _on_reset(self):
        """Clear the history log for a fresh test run."""
        self._pm.reset_history()
        self._log_count_lbl.setText("Log: 0 rows")
