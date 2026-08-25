# app/voice/whisper_engine.py
"""
Faster-Whisper inference engine.

Model choice
------------
Model  : base
Device : cpu
Dtype  : int8

Rationale: base+int8 on CPU gives ~200–400 ms per short desktop command —
fast enough for interactive use without needing a GPU.  Change WHISPER_MODEL
and COMPUTE_TYPE below if you have an NVIDIA GPU with CUDA and cuDNN
installed (device="cuda", compute_type="float16").

Initial prompt
--------------
The 'initial_prompt' biases Whisper's decoder vocabulary towards the
words that appear in BUG's command set.  This measurably improves
accuracy on short commands with unusual capitalization or spacing.

Model download
--------------
Faster-Whisper downloads the model on first use to:
    models/whisper/<model_name>/
This is ~147 MB for "base".  Subsequent runs use the cached model.
"""

import os
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Configuration — change here only
# ---------------------------------------------------------------------------

WHISPER_MODEL: str = "base"        # tiny | base | small | medium | large-v3
DEVICE: str = "cpu"                # cpu | cuda
COMPUTE_TYPE: str = "int8"         # int8 (cpu) | float16 (cuda) | float32

# Whisper decoder bias: words from BUG's command vocabulary
# IMPORTANT: Include exact words that Whisper was hallucinating, so it
# learns the correct pronunciation for this domain.
_INITIAL_PROMPT: str = (
    "open chrome open notepad open calculator open youtube open reddit "
    "scroll down scroll up page down page up new tab close tab go back "
    "volume up volume down minimize window close window refresh "
    "select all copy paste cut undo redo click double click right click "
    "change tab next tab previous tab start typing stop typing "
    "emergency stop enable control"
)

# Where to cache the model weights
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MODEL_CACHE_DIR = str(_PROJECT_ROOT / "models" / "whisper")


class WhisperEngine:
    """
    Wraps Faster-Whisper for offline speech-to-text transcription.

    Usage::

        engine = WhisperEngine()
        engine.start()                          # loads model
        text = engine.transcribe(audio_np)      # float32 array [-1, 1]
        engine.stop()
    """

    def __init__(
        self,
        model: str = WHISPER_MODEL,
        device: str = DEVICE,
        compute_type: str = COMPUTE_TYPE,
    ):
        self._model_name = model
        self._device = device
        self._compute_type = compute_type
        self._model = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Load the Whisper model (downloads on first run)."""
        self._load_model()

    def stop(self) -> None:
        """Release model resources."""
        self._model = None
        print("[Whisper] Model released")

    def transcribe(self, audio_np: np.ndarray, sample_rate: int = 16_000) -> str:
        """
        Transcribe a speech segment.

        Parameters
        ----------
        audio_np :
            Float32 numpy array in the range [-1, 1], at 16 kHz.
        sample_rate :
            Must be 16 000 Hz (Whisper's native rate).

        Returns
        -------
        str
            Lowercased transcript, stripped of leading/trailing whitespace.
            Returns "" on failure.
        """
        if self._model is None:
            print("[Whisper] WARNING: Model not loaded — call start() first")
            return ""

        if len(audio_np) == 0:
            return ""

        # Ensure float32
        if audio_np.dtype != np.float32:
            audio_np = audio_np.astype(np.float32)

        # Clip to [-1, 1] just in case
        audio_np = np.clip(audio_np, -1.0, 1.0)

        try:
            segments, info = self._model.transcribe(
                audio_np,
                language="en",
                initial_prompt=_INITIAL_PROMPT,
                # Beam search settings — balance speed vs accuracy
                beam_size=3,
                best_of=3,
                temperature=0.0,           # greedy — faster, more deterministic
                vad_filter=False,          # VAD already applied upstream
                word_timestamps=False,     # not needed for command matching
                # Condition on previous text — disabled for short commands
                condition_on_previous_text=False,
                # Suppress empty / hallucinated tokens aggressively
                no_speech_threshold=0.6,
                compression_ratio_threshold=2.4,
            )

            # Collect segment texts
            parts = []
            for seg in segments:
                text = seg.text.strip()
                if text:
                    parts.append(text)

            transcript = " ".join(parts).lower().strip()

            if transcript:
                print(f"[Whisper] Transcript: '{transcript}'")
            else:
                print("[Whisper] No speech detected in segment")

            return transcript

        except Exception as e:
            print(f"[Whisper] Transcription error: {e}")
            return ""

    def transcribe_file(self, wav_path: str) -> str:
        """
        Transcribe a WAV file.  Convenience method for testing.

        Parameters
        ----------
        wav_path :
            Path to a 16 kHz mono WAV file.
        """
        import wave
        import struct

        with wave.open(wav_path, "rb") as wf:
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return self.transcribe(audio_np)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import]

            # Create cache dir if it doesn't exist
            os.makedirs(_MODEL_CACHE_DIR, exist_ok=True)

            print(
                f"[Whisper] Loading model '{self._model_name}' "
                f"({self._device}, {self._compute_type}) — "
                f"may download ~150 MB on first run..."
            )

            self._model = WhisperModel(
                self._model_name,
                device=self._device,
                compute_type=self._compute_type,
                download_root=_MODEL_CACHE_DIR,
                # Single-threaded for laptops to avoid thermal throttling
                cpu_threads=4,
                num_workers=1,
            )

            print(f"[Whisper] Model ready: {self._model_name}")

        except ImportError as e:
            raise ImportError(
                f"faster-whisper not installed: {e}\n"
                "Install with: pip install faster-whisper"
            ) from e

        except Exception as e:
            raise RuntimeError(
                f"[Whisper] Failed to load model '{self._model_name}': {e}"
            ) from e
