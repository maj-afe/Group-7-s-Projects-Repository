# app/voice/speech_recognition.py
"""
Voice pipeline thread: Microphone → WebRTC APM → Silero VAD → Faster-Whisper.

This module replaces the previous Vosk-based implementation.
The public Qt interface is IDENTICAL to the old version so that
VoiceAssistant and MainWindow need no changes:

    Signals emitted
    ---------------
    command_recognized(str)   — normalized text ready for CommandHandler
    status_update(str)        — human-readable status string
    error_occurred(str)       — error message

    Methods
    -------
    run()                     — QThread entry point (called by start())
    stop()                    — graceful shutdown

Pipeline
--------
SoundDevice callback
    ↓ 10 ms int16 PCM frame
AudioProcessor (WebRTC APM)
    ↓ cleaned frame
SileroVAD
    ↓ complete speech segment (float32 numpy array)
WhisperEngine
    ↓ raw transcript string
CommandNormalizer
    ↓ normalized string
command_recognized.emit(text)

Thread safety
-------------
- The SoundDevice callback runs on PortAudio's thread.
  It only does queue.put_nowait() — no blocking, no model inference.
- The SileroVAD.process_frame() and WhisperEngine.transcribe() both run
  inside SpeechRecognitionThread.run() on this QThread.
- Whisper inference is synchronous and blocks this thread for ~200–800 ms.
  This is acceptable because the QThread is separate from the UI thread.
  The UI remains responsive throughout.
"""

import queue
import threading
import time

import numpy as np
from PySide6.QtCore import QThread, Signal

from .audio_capture import AudioCapture
from .audio_processor import AudioProcessor
from .vad import SileroVAD
from .whisper_engine import WhisperEngine



class SpeechRecognitionThread(QThread):
    """
    Offline speech recognition thread using:
        WebRTC APM + Silero VAD + Faster-Whisper.

    Key design decisions
    --------------------
    - The VAD state machine collects a complete command segment before
      invoking Whisper, so Whisper never receives silence or partial words.
    - WhisperEngine.transcribe() is called synchronously on this thread;
      the ~200–800 ms inference time is intentionally acceptable here
      because it runs in a dedicated QThread, keeping the UI thread free.
    - AudioProcessor degrades to a pass-through if pywebrtc-audio is not
      installed, so the pipeline still runs without the noise suppression.
    - A threading.Event is used to signal the VAD callback to post the
      segment to the Whisper queue rather than calling Whisper directly
      from the VAD callback (which could re-enter while another segment
      is being processed).
    """

    command_recognized = Signal(str)
    status_update = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, model_path=None):
        super().__init__()
        # model_path is accepted for API compatibility with old code but unused
        # (Faster-Whisper manages its own model cache in models/whisper/)
        self.running = False
        self._segment_queue: queue.Queue = queue.Queue(maxsize=4)

    # =========================================================
    # MAIN THREAD LOOP
    # =========================================================

    def run(self):
        self.running = True

        # ----------------------------------------------------------
        # 1. Audio capture
        # ----------------------------------------------------------
        capture = AudioCapture()

        # ----------------------------------------------------------
        # 2. WebRTC APM (NS + AGC + HPF)
        # ----------------------------------------------------------
        self.status_update.emit("Initializing audio processor...")
        processor = AudioProcessor()

        # ----------------------------------------------------------
        # 3. Silero VAD
        # ----------------------------------------------------------
        self.status_update.emit("Loading VAD model...")
        try:
            vad = SileroVAD(on_segment=self._on_vad_segment)
            vad.start()
        except ImportError as e:
            self.error_occurred.emit(
                f"Silero VAD not available:\n{e}\n\n"
                "Install with: pip install silero-vad"
            )
            self.running = False
            return
        except Exception as e:
            self.error_occurred.emit(
                f"VAD initialization failed:\n{e}"
            )
            self.running = False
            return

        # ----------------------------------------------------------
        # 4. Faster-Whisper
        # ----------------------------------------------------------
        self.status_update.emit("Loading speech recognition model...")
        try:
            whisper = WhisperEngine()
            whisper.start()
        except Exception as e:
            self.error_occurred.emit(
                f"Whisper model failed to load:\n{e}\n\n"
                "Check your internet connection for the first download."
            )
            self.running = False
            return

        # ----------------------------------------------------------
        # 5. Start microphone
        # ----------------------------------------------------------
        try:
            capture.start()
        except Exception as e:
            self.error_occurred.emit(
                f"Microphone error:\n{e}\n\n"
                "Please check that your microphone is connected and "
                "not being used by another application."
            )
            self.running = False
            return

        self.status_update.emit("Listening")
        print("[Voice] Pipeline running: WebRTC APM → Silero VAD → Faster-Whisper")

        # ----------------------------------------------------------
        # 6. Main loop
        # ----------------------------------------------------------
        try:
            while self.running:
                # ---- A. Consume audio frames ---------------------
                frame = capture.get_frame(timeout=0.05)

                if frame is not None:
                    # WebRTC APM cleaning
                    clean_frame = processor.process(frame)

                    # VAD — emits to _segment_queue via callback
                    vad.process_frame(clean_frame)

                # ---- B. Transcribe any complete segments ---------
                try:
                    audio_np, sr = self._segment_queue.get_nowait()
                except queue.Empty:
                    continue

                # Whisper inference (~200–800 ms on CPU)
                raw_text = whisper.transcribe(audio_np, sr)

                if not raw_text:
                    continue

                print(f"[Voice] Recognized: '{raw_text}'")
                self.command_recognized.emit(raw_text)

        except Exception as e:
            if self.running:
                self.error_occurred.emit(
                    f"Voice recognition error:\n{e}"
                )

        finally:
            # Graceful shutdown in reverse order
            self.running = False
            capture.stop()
            vad.stop()
            whisper.stop()
            self.status_update.emit("Inactive")
            print("[Voice] Pipeline stopped")

    # =========================================================
    # VAD SEGMENT CALLBACK
    # =========================================================

    def _on_vad_segment(self, audio_np: np.ndarray, sample_rate: int) -> None:
        """
        Called by SileroVAD when a complete speech segment is ready.
        Runs on the same thread as run() — simply enqueues for Whisper.
        """
        try:
            self._segment_queue.put_nowait((audio_np, sample_rate))
        except queue.Full:
            print("[Voice] Segment queue full — dropping oldest segment")
            try:
                self._segment_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._segment_queue.put_nowait((audio_np, sample_rate))
            except queue.Full:
                pass

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):
        self.running = False
        if self.isRunning():
            self.wait(5000)  # Whisper may need up to ~1 s to finish
