# app/voice/speech_recognition.py

import json
import os
import queue

import sounddevice as sd
from vosk import Model, KaldiRecognizer
from PySide6.QtCore import QThread, Signal


class SpeechRecognitionThread(QThread):
    """
    Offline speech recognition thread using Vosk + SoundDevice.

    Key design decisions:
    - Partial results are ONLY emitted for short (1-2 word) exact-match commands.
      This prevents "open you to" / "open your" style garbage from firing
      the generic open-site regex before the final result arrives.
    - A 'pending_partial' flag tracks which partial was acted on so that
      the subsequent final result (which is more accurate) does NOT
      trigger the same command a second time via cooldown bypass.
    - Full 3+ word phrases are ONLY acted on via the final result, which
      is the most accurate transcription Vosk can produce.
    - Audio queue draining on stop prevents stale audio being processed
      if the thread is restarted.
    """

    command_recognized = Signal(str)
    status_update = Signal(str)
    error_occurred = Signal(str)

    # =========================================================
    # SHORT COMMANDS that are safe to act on via partial results.
    # These MUST be single or two-word exact commands.
    # DO NOT add regex-matched commands (like "open X") here —
    # those must come from the accurate final result only.
    # =========================================================
    _PARTIAL_WHITELIST = frozenset([
        # Single-word
        "click", "paste", "copy", "cut", "undo", "redo", "save",
        "enter", "backspace", "escape", "yes", "no", "mute", "unmute",
        "play", "pause", "cancel", "help",
        # Two-word
        "left click", "right click", "double click",
        "scroll down", "scroll up", "page down", "page up",
        "go back", "new tab", "close tab", "next tab", "zoom in", "zoom out",
        "volume up", "volume down", "next video", "select all",
        "minimize window", "close window", "switch window",
        "emergency stop", "stop automation", "enable control",
        "start typing", "stop typing",
        # Scroll aliases (misheard words for scroll up/down)
        "roll up", "sold out", "roll down", "slow down",
    ])

    def __init__(self, model_path=None):
        super().__init__()

        self.audio_queue = queue.Queue()
        self.running = False
        self.sample_rate = 16000

        self.model_path = model_path or self._find_model()

        # Track the last partial we emitted so we can tell the
        # final result handler to skip it (preventing double-fire).
        self._pending_partial = ""

    # =========================================================
    # MODEL DISCOVERY
    # =========================================================

    def _find_model(self) -> str:
        """
        Locates the Vosk model directory automatically.
        Prefers the Indian English model for better accent coverage,
        falls back to US English if not found.
        """
        project_root = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                ".."
            )
        )

        models_dir = os.path.join(project_root, "models")

        # Preference order: Indian English > US English > any model found
        preferred = [
            "vosk-model-small-en-in-0.4",
            "vosk-model-small-en-us-0.15",
        ]

        for model_name in preferred:
            path = os.path.join(models_dir, model_name)
            if os.path.isdir(path):
                print(f"[Voice] Found model: {model_name}")
                return path

        # Fallback: use any model directory found in models/
        if os.path.isdir(models_dir):
            for entry in os.listdir(models_dir):
                full_path = os.path.join(models_dir, entry)
                if os.path.isdir(full_path):
                    print(f"[Voice] Falling back to model: {entry}")
                    return full_path

        # Return preferred path even if missing (error handled in run())
        return os.path.join(models_dir, preferred[0])

    # =========================================================
    # AUDIO CALLBACK
    # =========================================================

    def audio_callback(self, indata, frames, time, status):
        if status:
            print("[Voice Audio]", status)
        if self.running:
            self.audio_queue.put(bytes(indata))

    # =========================================================
    # MAIN THREAD LOOP
    # =========================================================

    def run(self):

        self.running = True

        self.status_update.emit("Loading offline voice model...")

        if not os.path.isdir(self.model_path):
            self.error_occurred.emit(
                f"Vosk model not found:\n{self.model_path}\n\n"
                "Please ensure a Vosk model is in the 'models/' directory."
            )
            self.running = False
            return

        try:
            print("[Voice] Loading model:", self.model_path)
            model = Model(self.model_path)
            recognizer = KaldiRecognizer(model, self.sample_rate)
            recognizer.SetMaxAlternatives(0)
            recognizer.SetWords(False)

        except Exception as e:
            self.error_occurred.emit(
                f"Failed to load Vosk model:\n{e}"
            )
            self.running = False
            return

        self.status_update.emit("Listening")

        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=4000,
                dtype="int16",
                channels=1,
                callback=self.audio_callback
            ):
                while self.running:
                    try:
                        data = self.audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    # --------------------------------------------------
                    # FINAL RESULT
                    # Vosk emits a final result when it detects silence.
                    # This is the most accurate transcription.
                    # --------------------------------------------------
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "").strip()

                        if text:
                            print(f"[Voice] Final: '{text}'")

                            # If we already fired on a partial that matches
                            # this final result closely, skip it to prevent
                            # the command from executing twice.
                            if text == self._pending_partial:
                                print(f"[Voice] Skipping final (already ran as partial): '{text}'")
                                self._pending_partial = ""
                            else:
                                self._pending_partial = ""
                                self.command_recognized.emit(text)

                    else:
                        # --------------------------------------------------
                        # PARTIAL RESULT
                        # Only emit SHORT, KNOWN commands from the whitelist.
                        # This prevents garbage like "open your" / "open you to"
                        # from prematurely firing the generic website opener.
                        # --------------------------------------------------
                        partial_result = json.loads(recognizer.PartialResult())
                        partial_text = partial_result.get("partial", "").strip()

                        if (
                            partial_text
                            and partial_text != self._pending_partial
                            and partial_text in self._PARTIAL_WHITELIST
                        ):
                            self._pending_partial = partial_text
                            print(f"[Voice] Partial (whitelisted): '{partial_text}'")
                            self.command_recognized.emit(partial_text)

        except sd.PortAudioError as e:
            self.error_occurred.emit(
                f"Microphone error:\n{e}\n\n"
                "Please check that your microphone is connected and "
                "not being used by another application."
            )

        except Exception as e:
            self.error_occurred.emit(
                f"Voice recognition error:\n{e}"
            )

        finally:
            self.running = False
            # Drain the audio queue so stale data is not processed
            # if the thread is restarted.
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break

            self.status_update.emit("Inactive")

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):
        self.running = False
        if self.isRunning():
            self.wait(2000)
