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
import os
import queue
import re
import shutil
import subprocess
import tempfile
import wave

import sounddevice as sd
from PySide6.QtCore import QThread, Signal


# --------------------------------------------------------------------------- #
# Audio parameters
# --------------------------------------------------------------------------- #
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCKSIZE = 160
SILENCE_RMS_THRESHOLD = 100
MIN_SPEECH_SECONDS = 0.2
MAX_SILENCE_SECONDS = 0.3
MAX_UTTERANCE_SECONDS = 3.0
QUEUE_POLL_TIMEOUT = 0.05


DEFAULT_MODEL_NAME = "ggml-base.en.bin"
WHISPER_TIMEOUT = 60
WHISPER_THREADS = max(1, min(8, os.cpu_count() or 1))

_WHISPER_BIN_CANDIDATES = ("whisper.cpp", "whisper", "main")
_MODEL_CANDIDATES = (
    "ggml-small.en.bin",
    "ggml-base.en.bin",
    "ggml-medium.en.bin",
    "ggml-turbo.en.bin",
    "ggml-large-v3-turbo-q5_K.gguf",
    "ggml-large-v3.bin",
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
    """Background thread: capture mic audio, detect utterances, transcribe offline
    with whisper.cpp, and emit each recognized transcript as a command."""

    command_recognized = Signal(str)
    status_update = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, model_path=None, whisper_bin=None, language="en"):
        super().__init__()

        self.audio_queue: "queue.Queue[bytes]" = queue.Queue()
        self.running = False
        self.sample_rate = SAMPLE_RATE

        if whisper_bin:
            self.whisper_bin = whisper_bin
        elif os.environ.get("WHISPER_BIN"):
            self.whisper_bin = os.environ["WHISPER_BIN"]
        else:
            self.whisper_bin = next(
                (shutil.which(name) for name in _WHISPER_BIN_CANDIDATES if shutil.which(name)),
                None,
            )

        if model_path:
            self.model_path = model_path
        else:
            self.model_path = os.environ.get("WHISPER_MODEL") or self.find_model()

        self.language = language

        # Silero VAD model path
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self.vad_model_path = os.path.join(
            project_root,
            "whisper.cpp",
            "models",
            "ggml-silero-v5.1.2.bin",
        )
        self.vad_model_path = os.path.abspath(self.vad_model_path)

        print("[Voice] VAD model:", self.vad_model_path)
        print("[Voice] VAD exists:", os.path.isfile(self.vad_model_path))

        self._tmpdir = tempfile.mkdtemp(prefix="bug-whisper-")
        self._utt_seq = 0

    # ------------------------------------------------------------------ #
    # Model / binary resolution
    # ------------------------------------------------------------------ #
    def find_model(self):
        """Locate a whisper.cpp model under the project's `models/` dir."""
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        models_dir = os.path.join(project_root, "models")
        for name in _MODEL_CANDIDATES:
            candidate = os.path.join(models_dir, name)
            if os.path.isfile(candidate):
                return candidate
        return os.path.join(models_dir, DEFAULT_MODEL_NAME)

    # ------------------------------------------------------------------ #
    # Audio callback
    # ------------------------------------------------------------------ #
    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print("[Voice Audio]", status)
        if self.running:
            self.audio_queue.put(bytes(indata))

    # ------------------------------------------------------------------ #
    # Utterance transcription
    # ------------------------------------------------------------------ #
    def _transcribe(self, pcm_bytes: bytes) -> str:
        """Write captured PCM to a temp WAV and run whisper.cpp over it."""
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
        if not os.path.isfile(self.vad_model_path):
            raise RuntimeError(
                f"Silero VAD model not found at {self.vad_model_path}"
            )

        os.makedirs(self._tmpdir, exist_ok=True)
        prefix = os.path.join(self._tmpdir, f"utt-{self._utt_seq}")
        wav_path = prefix + ".wav"

        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm_bytes)

        cmd = [
            self.whisper_bin,
            "-m", str(self.model_path),
            "-f", wav_path,
            "-of", prefix,
            "-otxt",
            "--language", self.language,
            "-bo", "1",
            "-bs", "1",
            "-nf",
            "--no-speech-thold", "0.75",
            "--temperature", "0",
            "--vad",
            "--vad-model", self.vad_model_path,
            "--vad-threshold", "0.5",
            "--vad-min-speech-duration-ms", "250",
            "--vad-min-silence-duration-ms", "300",
            "--vad-speech-pad-ms", "30",
            "-t", str(WHISPER_THREADS),
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
            return ""

        text = open(txt_path, "r", encoding="utf-8", errors="replace").read()

        text = re.sub(r"\[[^\]]*\]|【[^】]*】|→", "", text)

        ts = re.compile(
            r"^\s*\d{1,2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*"
            r"\d{1,2}:\d{2}:\d{2}[.,]\d{3}\s*"
        )
        lines = [ts.sub("", ln.strip()) for ln in text.splitlines()]
        lines = [ln for ln in lines if ln]
        cleaned = " ".join(" ".join(lines).split())
        return self._remove_repeated_words(cleaned)

    # ------------------------------------------------------------------ #
    # Remove repeated words
    # ------------------------------------------------------------------ #
    def _remove_repeated_words(self, text: str) -> str:
        words = text.split()

        if not words:
            return ""

        result = []
        i = 0

        while i < len(words):
            word = words[i]
            repeated = False

            for phrase_len in range(1, min(5, (len(words) - i) // 2 + 1)):
                first = [
                    w.lower().strip(".,!?")
                    for w in words[i:i + phrase_len]
                ]
                second = [
                    w.lower().strip(".,!?")
                    for w in words[i + phrase_len:i + 2 * phrase_len]
                ]

                if first == second:
                    result.extend(words[i:i + phrase_len])
                    i += phrase_len

                    while i + phrase_len <= len(words):
                        current = [
                            w.lower().strip(".,!?")
                            for w in words[i:i + phrase_len]
                        ]
                        if current != first:
                            break
                        i += phrase_len

                    repeated = True
                    break

            if not repeated:
                result.append(word)
                i += 1

        return " ".join(result)

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self):
        if not self.whisper_bin:
            self.error_occurred.emit(
                "whisper.cpp binary not found. Install `whisper.cpp` (or set "
                "WHISPER_BIN) and a model in models/ before starting voice."
            )
            self.status_update.emit("Error")
            return

        if not self.model_path or not os.path.isfile(self.model_path):
            self.error_occurred.emit(
                f"Whisper model missing: {self.model_path}. "
                "Download ggml-medium.en.bin into models/."
            )
            self.status_update.emit("Error")
            return

        self.status_update.emit("Loading whisper model...")

        self.running = True
        self.status_update.emit("Listening")

        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=BLOCKSIZE,
                dtype="int16",
                channels=CHANNELS,
                callback=self.audio_callback,
            ):
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

                    rms = _rms_int16(chunk)
                    is_speech = rms > SILENCE_RMS_THRESHOLD

                    if is_speech and not have_speech:
                        have_speech = True
                        buf = bytearray()
                        utterance_samples = 0
                        speech_samples = 0
                        last_speech_sample = 0
                        silence_samples = 0

                    if have_speech:
                        buf.extend(chunk)
                        utterance_samples += BLOCKSIZE

                        if is_speech:
                            speech_samples += BLOCKSIZE
                            last_speech_sample = utterance_samples
                            silence_samples = 0
                        else:
                            silence_samples += BLOCKSIZE

                    trailing_silence = utterance_samples - last_speech_sample
                    max_utterance = int(MAX_UTTERANCE_SECONDS * SAMPLE_RATE)
                    min_speech = int(MIN_SPEECH_SECONDS * SAMPLE_RATE)
                    max_silence = int(MAX_SILENCE_SECONDS * SAMPLE_RATE)

                    should_flush = False
                    reason = ""
                    if have_speech and speech_samples >= min_speech:
                        if trailing_silence >= max_silence:
                            should_flush = True
                            reason = "silence"
                        elif utterance_samples >= max_utterance:
                            should_flush = True
                            reason = "max_len"
                    elif not have_speech and utterance_samples >= max_utterance:
                        should_flush = True
                        reason = "timeout"

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
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
            self.status_update.emit("Inactive")

    # ------------------------------------------------------------------ #
    # Flush utterance
    # ------------------------------------------------------------------ #
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

        if text:
            text_clean = text.strip().lower()

            garbage = {
                "[",
                "]",
                "!!!",
                "so i",
                "dot",
                "india",
                "bye bye",
                "hello chindia",
                "thank you",
                "thank you for watching",
                "speaking in foreign language",
                "muffled speaking",
                "mumbles",
            }

            if text_clean in garbage:
                print("[Voice] Ignored low-confidence transcript:", text)
            else:
                print("[Voice] Recognized:", text)
                self.command_recognized.emit(text)
        else:
            if reason == "timeout":
                pass
            else:
                print("[Voice] whisper returned no speech text; dropping.")

        self.status_update.emit("Listening")

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def stop(self):
        self.running = False
        if self.isRunning():
            self.wait(2000)