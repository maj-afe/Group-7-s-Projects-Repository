# app/core/perf_monitor.py
"""
Central performance metrics collector.

Design
------
- Singleton: `PerfMonitor.instance()` returns the one shared object.
- Thread-safe: all mutating methods acquire a short-lived threading.Lock.
- Non-blocking: record_* calls are O(1) — safe to call from tight camera loops.
- Snapshot: `snapshot()` returns a frozen dict of current stats, called once/s
  by the UI timer.
- History: every snapshot is appended to `_history` (list of dicts).
  The UI can export the full history as CSV via `export_csv()`.

Metrics collected
-----------------
  camera_fps           — frames per second from CameraThread
  face_detect_ms       — MediaPipe detect_for_video() latency (ms)
  cursor_ms            — pyautogui.moveTo() latency (ms)
  vad_total_segments   — total VAD segments emitted since start
  vad_dropped_segments — segments dropped (too short / noise)
  vad_last_segment_ms  — duration of last segment (ms)
  whisper_last_ms      — last Whisper transcription latency (ms)
  whisper_avg_ms       — rolling average Whisper latency (ms)
  cmd_total            — total commands processed since start
  cmd_unknown          — commands that returned 'unknown'
  cmd_dispatch_ms      — last command_handler.execute() latency (ms)
  e2e_ms               — last end-to-end latency: VAD→command done (ms)
  audio_overflows      — SoundDevice input overflow count
"""

import threading
import time
from datetime import datetime
from typing import Dict, Any, List


class PerfMonitor:
    """
    Set ENABLED = False to disable ALL instrumentation with zero runtime cost.
    All record_* methods become instant no-ops (single bool check, no lock).
    Use this to get a clean baseline run for comparison.
    """

    # ---------------------------------------------------------------
    # Kill switch — flip to False for a zero-overhead baseline run
    # ---------------------------------------------------------------
    ENABLED: bool = True

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls) -> "PerfMonitor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._mu = threading.Lock()

        # --- Camera ---
        self._frame_count = 0          # incremented per frame
        self._fps_window_start = time.time()
        self._camera_fps = 0.0
        self._face_detect_ms = 0.0
        self._cursor_ms = 0.0

        # --- VAD ---
        self._vad_total = 0
        self._vad_dropped = 0
        self._vad_last_ms = 0.0
        self._vad_segment_start: float = 0.0   # set when segment is emitted

        # --- Whisper ---
        self._whisper_last_ms = 0.0
        self._whisper_total_ms = 0.0
        self._whisper_count = 0

        # --- Commands ---
        self._cmd_total = 0
        self._cmd_unknown = 0
        self._cmd_dispatch_ms = 0.0
        self._e2e_ms = 0.0

        # --- Audio ---
        self._audio_overflows = 0

        # --- Session history (one dict per second snapshot) ---
        self._history: List[Dict[str, Any]] = []
        self._session_start = datetime.now()

    # ------------------------------------------------------------------
    # Camera
    # ------------------------------------------------------------------

    def record_frame(self):
        """Call once per camera frame to drive the FPS counter."""
        if not self.ENABLED:
            return
        with self._mu:
            self._frame_count += 1
            now = time.time()
            elapsed = now - self._fps_window_start
            if elapsed >= 1.0:
                self._camera_fps = self._frame_count / elapsed
                self._frame_count = 0
                self._fps_window_start = now

    def record_face_detect(self, ms: float):
        if not self.ENABLED:
            return
        with self._mu:
            self._face_detect_ms = ms

    def record_cursor_move(self, ms: float):
        if not self.ENABLED:
            return
        with self._mu:
            self._cursor_ms = ms

    # ------------------------------------------------------------------
    # VAD
    # ------------------------------------------------------------------

    def record_vad_segment(self, duration_ms: float):
        """Call when a real segment is emitted to Whisper."""
        if not self.ENABLED:
            return
        with self._mu:
            self._vad_total += 1
            self._vad_last_ms = duration_ms
            self._vad_segment_start = time.time()

    def record_vad_dropped(self):
        """Call when a segment is dropped as too-short noise."""
        if not self.ENABLED:
            return
        with self._mu:
            self._vad_total += 1
            self._vad_dropped += 1

    # ------------------------------------------------------------------
    # Whisper
    # ------------------------------------------------------------------

    def record_whisper(self, ms: float):
        if not self.ENABLED:
            return
        with self._mu:
            self._whisper_last_ms = ms
            self._whisper_total_ms += ms
            self._whisper_count += 1

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def record_command(self, result: str, dispatch_ms: float):
        """
        Call after command_handler.execute() returns.
        result  — the command key string (or 'unknown')
        dispatch_ms — time spent inside execute()
        """
        if not self.ENABLED:
            return
        with self._mu:
            self._cmd_total += 1
            if result == "unknown" or result is None:
                self._cmd_unknown += 1
            self._cmd_dispatch_ms = dispatch_ms
            # End-to-end: from VAD segment emit → command done
            if self._vad_segment_start > 0:
                self._e2e_ms = (time.time() - self._vad_segment_start) * 1000
                self._vad_segment_start = 0.0

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    def record_overflow(self):
        if not self.ENABLED:
            return
        with self._mu:
            self._audio_overflows += 1

    # ------------------------------------------------------------------
    # Snapshot (called by UI timer, once per second)
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return a frozen copy of current metrics and append to history."""
        with self._mu:
            whisper_avg = (
                self._whisper_total_ms / self._whisper_count
                if self._whisper_count > 0 else 0.0
            )
            unknown_pct = (
                (self._cmd_unknown / self._cmd_total * 100)
                if self._cmd_total > 0 else 0.0
            )
            noise_pct = (
                (self._vad_dropped / self._vad_total * 100)
                if self._vad_total > 0 else 0.0
            )

            snap = {
                "ts": datetime.now().strftime("%H:%M:%S"),
                # Camera
                "camera_fps":        round(self._camera_fps, 1),
                "face_detect_ms":    round(self._face_detect_ms, 1),
                "cursor_ms":         round(self._cursor_ms, 2),
                # VAD
                "vad_total":         self._vad_total,
                "vad_dropped":       self._vad_dropped,
                "vad_noise_pct":     round(noise_pct, 1),
                "vad_last_ms":       round(self._vad_last_ms, 0),
                # Whisper
                "whisper_last_ms":   round(self._whisper_last_ms, 0),
                "whisper_avg_ms":    round(whisper_avg, 0),
                # Commands
                "cmd_total":         self._cmd_total,
                "cmd_unknown":       self._cmd_unknown,
                "cmd_unknown_pct":   round(unknown_pct, 1),
                "cmd_dispatch_ms":   round(self._cmd_dispatch_ms, 2),
                "e2e_ms":            round(self._e2e_ms, 0),
                # Audio
                "audio_overflows":   self._audio_overflows,
            }

        self._history.append(snap)
        return snap

    # ------------------------------------------------------------------
    # Export (called by "Copy Stats Log" button)
    # ------------------------------------------------------------------

    def export_csv(self) -> str:
        """
        Return the full per-second session log as CSV text.
        Each row is one second of data since the app started.
        """
        if not self._history:
            return "No data recorded yet."

        headers = list(self._history[0].keys())
        lines = [",".join(headers)]
        for row in self._history:
            lines.append(",".join(str(row.get(h, "")) for h in headers))

        header_block = (
            f"# BUG Performance Log\n"
            f"# Session started: {self._session_start.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"# Total snapshots: {len(self._history)}\n"
            f"# \n"
        )
        return header_block + "\n".join(lines)

    def reset_history(self):
        """Clear the history log (useful for a fresh test run)."""
        with self._mu:
            self._history.clear()
            self._session_start = datetime.now()
