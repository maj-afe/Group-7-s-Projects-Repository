<<<<<<< HEAD
# app/voice/speech_recognition.py

import json
=======
"""
Local, offline speech recognition for BUG.

This module now drives `whisper.cpp` (the standalone, fully-offline C/C++
Whisper binary) instead of Vosk. The public interface is unchanged: it still
exposes `SpeechRecognitionThread(QThread)` emitting three signals
(`command_recognized`, `status_update`, `error_occurred`) that
`VoiceAssistant` wires up exactly as before. So `voice_assist.py` and
`command_handler.py` need no changes.

Why whisper.cpp over Vosk
-------------------------
Vosk uses small n-gram/DSTF models and has high word-error rate on noisy
telephone/mic speech. Whisper is an encoder-decoder transformer whose
`medium`/turbo GGUF models run on CPU and cut WER dramatically while staying
100% offline (model file on disk, no network, no account).

Setup
-----
1. Install the whisper.cpp binary (one of `whisper.cpp`, `whisper`, or `main`
   on PATH), OR set `WHISPER_BIN=/path/to/whisper.cpp`.
2. Download a model into `models/`, e.g. `ggml-medium.en.bin` for 16kHz English:
       wget -O models/ggml-medium.en.bin \
         https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.en.bin
   Override with `WHISPER_MODEL=/path/to/ggml-large-v3-turbo-q5_K.gguf`.

Audio contract is identical to the old Vosk path: 16kHz mono int16 PCM from
`sounddevice`, flushed per utterance once trailing silence is detected.
"""

import array
>>>>>>> cf128a4 (whisper.cpp implementation against vosk)
import os
import queue
import re
import shutil
import subprocess
import tempfile
import time
import wave

import sounddevice as sd
from PySide6.QtCore import QThread, Signal


# --------------------------------------------------------------------------- #
# Audio parameters
# --------------------------------------------------------------------------- #
SAMPLE_RATE = 16000      # Whisper expects 16 kHz mono.
CHANNELS = 1
# 160 samples @ 16 kHz = 10 ms per callback hop. Small enough for tight
# end-of-utterance / silence detection.
BLOCKSIZE = 160

# --------------------------------------------------------------------------- #
# Voice-activity detection (simple energy gate, no extra deps)
# --------------------------------------------------------------------------- #
# RMS threshold (int16 units) under which a 10 ms frame counts as silence.
# Tune up if the room is noisy, down if voice is being clipped.
SILENCE_RMS_THRESHOLD = 40
# Minimum speech to accept before we start counting trailing silence.
MIN_SPEECH_SECONDS = 0.3
# Silence tail that finalizes an utterance.
MAX_SILENCE_SECONDS = 0.7
# Hard cap on a single utterance so we never accumulate forever.
MAX_UTTERANCE_SECONDS = 8.0
# How long (seconds) to wait for a queued audio frame before re-checking the
# running flag. Also the cadence of the idle loop.
QUEUE_POLL_TIMEOUT = 0.05

# --------------------------------------------------------------------------- #
# Whisper defaults
# --------------------------------------------------------------------------- #
# `medium` is the sweet spot for a student laptop: far more accurate than Vosk,
# runs on CPU, ~1.5 GB. Drop to `tiny`/`base` for speed, or `large-v3-turbo`
# / `ggml-large-v3-q5_K` if you want max accuracy and have the RAM.
DEFAULT_MODEL_NAME = "ggml-medium.en.bin"
# Subprocess timeout per utterance (seconds). Whisper on CPU is ~1-2x realtime
# for `medium`; generous headroom avoids false failures on slow machines.
WHISPER_TIMEOUT = 60
# CPU threads handed to whisper.cpp via `-t`.
WHISPER_THREADS = max(1, min(4, os.cpu_count() or 1))

# Candidate binary names tried in order when WHISPER_BIN is unset.
_WHISPER_BIN_CANDIDATES = ("whisper.cpp", "whisper", "main")
# Candidate model filenames tried in order when WHISPER_MODEL is unset.
_MODEL_CANDIDATES = (
    "ggml-medium.en.bin",
    "ggml-turbo.en.bin",
    "ggml-large-v3-turbo-q5_K.gguf",
    "ggml-large-v3.bin",
    "ggml-base.en.bin",
)


def _rms_int16(chunk_bytes: bytes) -> float:
    """Root-mean-square amplitude of a little-endian int16 frame."""
    if not chunk_bytes:
        return 0.0
    samples = array.array("h")
    samples.frombytes(chunk_bytes)
    if not samples:
        return 0.0
    sq = sum(s * s for s in samples) / len(samples)
    return sq ** 0.5


class SpeechRecognitionThread(QThread):
<<<<<<< HEAD
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
=======
    """Background thread: capture mic audio, detect utterances, transcribe offline
    with whisper.cpp, and emit each recognized transcript as a command."""
>>>>>>> cf128a4 (whisper.cpp implementation against vosk)

    command_recognized = Signal(str)
    status_update = Signal(str)
    error_occurred = Signal(str)

<<<<<<< HEAD
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
=======
    def __init__(self, model_path=None, whisper_bin=None, language="en"):
>>>>>>> cf128a4 (whisper.cpp implementation against vosk)
        super().__init__()

        self.audio_queue: "queue.Queue[bytes]" = queue.Queue()
        self.running = False
        self.sample_rate = SAMPLE_RATE

<<<<<<< HEAD
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
=======
        # Resolve whisper binary (env > PATH lookup over candidate names).
        if whisper_bin:
            self.whisper_bin = whisper_bin
        elif os.environ.get("WHISPER_BIN"):
            self.whisper_bin = os.environ["WHISPER_BIN"]
        else:
            self.whisper_bin = next(
                (shutil.which(name) for name in _WHISPER_BIN_CANDIDATES if shutil.which(name)),
                None,
>>>>>>> cf128a4 (whisper.cpp implementation against vosk)
            )

        # Resolve model (explicit arg > env > on-disk candidates).
        if model_path:
            self.model_path = model_path
        else:
            self.model_path = os.environ.get("WHISPER_MODEL") or self.find_model()

        self.language = language

        # Per-process temp workspace for utterance WAVs + whisper txt output.
        self._tmpdir = tempfile.mkdtemp(prefix="bug-whisper-")
        self._utt_seq = 0

    # ------------------------------------------------------------------ #
    # Model / binary resolution
    # ------------------------------------------------------------------ #
    def find_model(self):
        """Locate a whisper.cpp model under the project's `models/` dir.

        Returns the path if found, otherwise returns the *expected default*
        path so that a missing-model error message names something concrete
        the user can download.
        """
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        models_dir = os.path.join(project_root, "models")
        for name in _MODEL_CANDIDATES:
            candidate = os.path.join(models_dir, name)
            if os.path.isfile(candidate):
                return candidate
        return os.path.join(models_dir, DEFAULT_MODEL_NAME)

<<<<<<< HEAD
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
=======
    # ------------------------------------------------------------------ #
    # Audio callback (runs on sounddevice's audio thread)
    # ------------------------------------------------------------------ #
    def audio_callback(self, indata, frames, time_info, status):
>>>>>>> cf128a4 (whisper.cpp implementation against vosk)
        if status:
            # Non-fatal; report but keep running.
            print("[Voice Audio]", status)
        if self.running:
            # indata is a numpy int16 array (dtype="int16"); flatten+bytes gives
            # raw little-endian PCM 16-bit mono samples.
            self.audio_queue.put(bytes(indata))

<<<<<<< HEAD
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
=======
    # ------------------------------------------------------------------ #
    # Utterance transcription
    # ------------------------------------------------------------------ #
    def _transcribe(self, pcm_bytes: bytes) -> str:
        """Write captured PCM to a temp WAV and run whisper.cpp over it.

        Returns the stripped transcript. Raises on failure so the caller can
        emit an `error_occurred` signal.
        """
        if not self.whisper_bin:
            raise RuntimeError(
                "whisper.cpp binary not found. Install it and put it on PATH, "
                "or set WHISPER_BIN=/path/to/whisper.cpp. "
                f"(tried: {_WHISPER_BIN_CANDIDATES})"
            )
        if not self.model_path or not os.path.isfile(self.model_path):
            raise RuntimeError(
                f"Whisper model not found at {self.model_path}. "
                "Download one (e.g. ggml-medium.en.bin) into models/, or set "
                "WHISPER_MODEL=/path/to/model.gguf."
            )

        os.makedirs(self._tmpdir, exist_ok=True)
        prefix = os.path.join(self._tmpdir, f"utt-{self._utt_seq}")
        wav_path = prefix + ".wav"

        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm_bytes)

        cmd = [
            self.whisper_bin,
            "-m", str(self.model_path),
            "-f", wav_path,
            "-of", prefix,            # output prefix -> writes prefix + ".txt"
            "-otxt",                  # force plain-text output
            "--language", self.language,
            "-t", str(WHISPER_THREADS),
            # N.B. `--no-warmup` is intentionally omitted: it is not present on
            # older whisper.cpp builds and would turn into a CLI error.
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=WHISPER_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"whisper.cpp timed out after {WHISPER_TIMEOUT}s on this utterance."
            )

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            raise RuntimeError(
                f"whisper.cpp exited {proc.returncode}: {stderr[-500:]}"
            )

        txt_path = prefix + ".txt"
        if not os.path.isfile(txt_path):
            # No text produced (e.g. a whisper no-speech segment) -> treat as
            # empty, not an error, so command flow keeps listening.
            return ""

        text = open(txt_path, "r", encoding="utf-8", errors="replace").read()

        # whisper.cpp `-otxt` writes one line per segment, each prefixed with
        # a bracketed `[hh:mm:ss,ms --> hh:mm:ss,ms]` timestamp that we discard.
        # Also drop special-token brackets (`[xxx]` / `【xxx】`) and arrow
        # markers emitted under `--print_special`.
        text = re.sub(r"\[[^\]]*\]|【[^】]*】|→", "", text)

        # Defensively strip any *bare* (unbracketed) leading timestamp range too,
        # then join surviving lines into one command string.
        ts = re.compile(
            r"^\s*\d{1,2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*"
            r"\d{1,2}:\d{2}:\d{2}[.,]\d{3}\s*"
        )
        lines = [ts.sub("", ln.strip()) for ln in text.splitlines()]
        lines = [ln for ln in lines if ln]
        return " ".join(" ".join(lines).split())

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self):
        # Preflight: binary + model. Report cleanly instead of crashing.
        if not self.whisper_bin:
>>>>>>> cf128a4 (whisper.cpp implementation against vosk)
            self.error_occurred.emit(
                "whisper.cpp binary not found. Install `whisper.cpp` (or set "
                "WHISPER_BIN) and a model in models/ before starting voice."
            )
<<<<<<< HEAD
            self.running = False
=======
            self.status_update.emit("Error")
>>>>>>> cf128a4 (whisper.cpp implementation against vosk)
            return

        if not self.model_path or not os.path.isfile(self.model_path):
            self.error_occurred.emit(
                f"Whisper model missing: {self.model_path}. "
                "Download ggml-medium.en.bin into models/."
            )
            self.status_update.emit("Error")
            return

        self.status_update.emit("Loading whisper model...")
        # whisper.cpp loads the model per-invocation, so there's a fixed per-call
        # startup cost. We accept it for command-grade latency.

        self.running = True
        self.status_update.emit("Listening")

        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
<<<<<<< HEAD
                blocksize=4000,
=======
                blocksize=BLOCKSIZE,
>>>>>>> cf128a4 (whisper.cpp implementation against vosk)
                dtype="int16",
                channels=CHANNELS,
                callback=self.audio_callback,
            ):
<<<<<<< HEAD
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
=======
                # Local VAD state for the current utterance.
                buf = bytearray()
                utterance_samples = 0
                speech_samples = 0
                last_speech_sample = 0
                silence_samples = 0
                have_speech = False

                while self.running:
                    try:
                        chunk = self.audio_queue.get(timeout=QUEUE_POLL_TIMEOUT)
                    except queue.Empty:
                        continue

                    # Energy gate on this 10 ms frame.
                    rms = _rms_int16(chunk)
                    is_speech = rms > SILENCE_RMS_THRESHOLD

                    buf.extend(chunk)
                    utterance_samples += BLOCKSIZE
                    if is_speech:
                        speech_samples += BLOCKSIZE
                        last_speech_sample = utterance_samples
                        have_speech = True
                        silence_samples = 0
                    else:
                        silence_samples += BLOCKSIZE

                    # Finalize triggers.
                    trailing_silence = utterance_samples - last_speech_sample
                    max_utterance = int(MAX_UTTERANCE_SECONDS * SAMPLE_RATE)
                    min_speech = int(MIN_SPEECH_SECONDS * SAMPLE_RATE)
                    max_silence = int(MAX_SILENCE_SECONDS * SAMPLE_RATE)

                    should_flush = False
                    if have_speech and speech_samples >= min_speech:
                        if trailing_silence >= max_silence:
                            should_flush = True  # natural end of utterance
                            reason = "silence"
                        elif utterance_samples >= max_utterance:
                            should_flush = True  # safety cap
                            reason = "max_len"
                    elif not have_speech and utterance_samples >= max_utterance:
                        should_flush = True  # nothing but silence; drain
                        reason = "timeout"
>>>>>>> cf128a4 (whisper.cpp implementation against vosk)

                    if should_flush and len(buf) > 0:
                        self._flush(buf, reason)
                        buf = bytearray()
                        utterance_samples = 0
                        speech_samples = 0
                        last_speech_sample = 0
                        silence_samples = 0
                        have_speech = False
        finally:
            self.running = False
<<<<<<< HEAD
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
=======
            self.status_update.emit("Inactive")

    def _flush(self, buf, reason):
        """Transcribe one accumulated utterance and emit its text."""
        self.status_update.emit("Transcribing...")
        pcm = bytes(buf)
        try:
            text = self._transcribe(pcm)
        except Exception as e:
            self.error_occurred.emit(f"whisper: {e}")
            self.status_update.emit("Error")
            return
        finally:
            self._utt_seq += 1
>>>>>>> cf128a4 (whisper.cpp implementation against vosk)

        if text:
            print("[Voice] Recognized:", text)
            self.command_recognized.emit(text)
        else:
            if reason == "timeout":
                # Pure silence drain — not an error, just keep listening.
                pass
            else:
                print("[Voice] whisper returned no speech text; dropping.")
        self.status_update.emit("Listening")

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def stop(self):
        self.running = False
<<<<<<< HEAD
        if self.isRunning():
            self.wait(2000)
=======
        self.requestExit()  # polite: let the loop exit at the next poll
>>>>>>> cf128a4 (whisper.cpp implementation against vosk)
