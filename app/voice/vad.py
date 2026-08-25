# app/voice/vad.py
"""
Silero VAD — Voice Activity Detection state machine.
Tested against silero-vad 6.x (PyTorch backend).

Key API facts (silero-vad 6.x)
-------------------------------
- load_silero_vad() returns the model directly (not a (model, utils) tuple).
- Minimum input chunk: 512 samples at 16 kHz (= 32 ms).
- Input must be a 1-D torch.FloatTensor.
- Output is a scalar tensor; call .item() to get a float.

Frame accumulation
------------------
AudioCapture produces 160-sample (10 ms) frames.
We accumulate 512 samples before passing to Silero, giving ~32 ms resolution.
This is still fast enough for desktop command detection.

State machine
-------------
    WAITING  →  (speech prob ≥ THRESHOLD)  →  SPEAKING
    SPEAKING →  (silence frames ≥ POST_ROLL_FRAMES)  →  emit segment → WAITING
    SPEAKING →  (segment too long)  →  emit segment → WAITING

Pre-roll
--------
A ring buffer keeps PRE_ROLL_CHUNKS worth of Silero chunks (not raw frames)
during WAITING so we don't clip the first phoneme when speech starts.

Post-roll
---------
POST_ROLL_CHUNKS of silence after the last speech chunk before finalising.
"""

import collections
from enum import Enum, auto
from typing import Callable

import numpy as np

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SAMPLE_RATE: int = 16_000
RAW_FRAME_SAMPLES: int = 160        # 10 ms — matches AudioCapture
SILERO_CHUNK_SAMPLES: int = 512     # minimum chunk Silero accepts at 16 kHz

SPEECH_THRESHOLD: float = 0.5       # Silero probability threshold
PRE_ROLL_CHUNKS: int = 6            # ~192 ms of audio before speech starts
POST_ROLL_CHUNKS: int = 15          # ~480 ms of silence before finalising
MAX_SEGMENT_CHUNKS: int = 250       # ~8 s safety cap


class _State(Enum):
    WAITING = auto()
    SPEAKING = auto()


class SileroVAD:
    """
    Real-time VAD that emits complete speech segments via a callback.

    Parameters
    ----------
    on_segment :
        Callable receiving (audio_np: np.ndarray, sample_rate: int).
        Called from the same thread as process_frame().
        audio_np is float32 in [-1, 1].
    speech_threshold :
        Silero probability score above which a frame is considered speech.

    Usage::

        def got_segment(audio, sr):
            text = whisper.transcribe(audio)

        vad = SileroVAD(on_segment=got_segment)
        vad.start()
        for frame in audio_source:
            vad.process_frame(frame)     # frame = bytes (int16 PCM)
        vad.stop()
    """

    def __init__(
        self,
        on_segment: Callable[[np.ndarray, int], None],
        speech_threshold: float = SPEECH_THRESHOLD,
    ):
        self._on_segment = on_segment
        self._threshold = speech_threshold

        self._model = None
        self._state = _State.WAITING

        # Raw-frame accumulator — fills until we have SILERO_CHUNK_SAMPLES
        self._raw_accum: list[bytes] = []
        self._raw_accum_samples: int = 0

        # Chunk-level buffers (each chunk = SILERO_CHUNK_SAMPLES samples)
        self._pre_roll: collections.deque = collections.deque(
            maxlen=PRE_ROLL_CHUNKS
        )
        self._segment_chunks: list[bytes] = []  # bytes per chunk
        self._silence_chunk_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Load the Silero VAD model."""
        self._load_model()
        self._reset()
        print(
            f"[VAD] Silero VAD ready — "
            f"threshold={self._threshold}, "
            f"pre-roll={PRE_ROLL_CHUNKS * SILERO_CHUNK_SAMPLES * 1000 // SAMPLE_RATE} ms, "
            f"post-roll={POST_ROLL_CHUNKS * SILERO_CHUNK_SAMPLES * 1000 // SAMPLE_RATE} ms"
        )

    def stop(self) -> None:
        """Reset internal state."""
        self._reset()
        print("[VAD] Stopped")

    def process_frame(self, frame_bytes: bytes) -> float:
        """
        Feed one 10 ms PCM frame (160 int16 samples = 320 bytes).

        Accumulates frames internally until a 512-sample Silero chunk
        is ready, then runs inference.

        Returns
        -------
        float
            Last known Silero speech probability (0.0–1.0).
            Returns 0.0 when chunk is not yet full.
        """
        self._raw_accum.append(frame_bytes)
        self._raw_accum_samples += RAW_FRAME_SAMPLES

        if self._raw_accum_samples < SILERO_CHUNK_SAMPLES:
            return 0.0

        # Build chunk from accumulated frames
        chunk_bytes = b"".join(self._raw_accum)
        # Take exactly SILERO_CHUNK_SAMPLES, keep any overflow
        needed = SILERO_CHUNK_SAMPLES * 2  # *2 for int16
        chunk_to_process = chunk_bytes[:needed]
        overflow = chunk_bytes[needed:]

        # Reset accumulator with any overflow samples
        self._raw_accum = []
        self._raw_accum_samples = 0
        if overflow:
            self._raw_accum.append(overflow)
            self._raw_accum_samples = len(overflow) // 2

        # Compute speech probability
        prob = self._speech_prob(chunk_to_process)

        # ---------------------------------------------------------------
        # State machine (chunk-level)
        # ---------------------------------------------------------------
        if self._state == _State.WAITING:
            self._pre_roll.append(chunk_to_process)

            if prob >= self._threshold:
                # Transition to SPEAKING — prepend pre-roll
                self._segment_chunks = list(self._pre_roll)
                self._silence_chunk_count = 0
                self._state = _State.SPEAKING

        elif self._state == _State.SPEAKING:
            self._segment_chunks.append(chunk_to_process)

            if prob < self._threshold:
                self._silence_chunk_count += 1
                if self._silence_chunk_count >= POST_ROLL_CHUNKS:
                    self._finalise_segment()
            else:
                self._silence_chunk_count = 0

            # Safety cap
            if len(self._segment_chunks) >= MAX_SEGMENT_CHUNKS:
                print("[VAD] Segment capped at max length — finalising")
                self._finalise_segment()

        return prob

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        """Load Silero VAD (PyTorch — silero-vad 6.x API)."""
        try:
            import torch  # type: ignore[import]
            from silero_vad import load_silero_vad  # type: ignore[import]

            # In silero-vad 6.x, load_silero_vad returns the model directly
            result = load_silero_vad(onnx=False)

            # Guard against old API that returned (model, utils) tuple
            if isinstance(result, tuple):
                self._model = result[0]
            else:
                self._model = result

            print("[VAD] Loaded Silero VAD (PyTorch)")

        except ImportError as e:
            raise ImportError(
                f"Could not load Silero VAD: {e}\n"
                "Install with: pip install silero-vad\n"
                "(Also requires torch — pip install torch)"
            ) from e

        except Exception as e:
            raise RuntimeError(
                f"Silero VAD init failed: {e}"
            ) from e

    def _speech_prob(self, chunk_bytes: bytes) -> float:
        """Run Silero on one 512-sample chunk. Returns probability [0,1]."""
        if self._model is None:
            return 0.0
        try:
            import torch  # type: ignore[import]
            audio_np = np.frombuffer(chunk_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            # Silero expects a 1-D FloatTensor
            tensor = torch.from_numpy(audio_np)
            result = self._model(tensor, SAMPLE_RATE)
            return float(result.item()) if hasattr(result, "item") else float(result)
        except Exception as e:
            print(f"[VAD] Speech prob error: {e}")
            return 0.0

    def _finalise_segment(self) -> None:
        """Concatenate buffered chunks and emit via callback."""
        raw = b"".join(self._segment_chunks)
        audio_f32 = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

        duration_ms = len(audio_f32) * 1000 // SAMPLE_RATE
        print(f"[VAD] Segment ready — {duration_ms} ms ({len(audio_f32)} samples)")

        self._on_segment(audio_f32, SAMPLE_RATE)
        self._reset()

    def _reset(self) -> None:
        self._state = _State.WAITING
        self._segment_chunks = []
        self._silence_chunk_count = 0
        self._pre_roll.clear()
        self._raw_accum = []
        self._raw_accum_samples = 0
