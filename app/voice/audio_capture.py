# app/voice/audio_capture.py
"""
Microphone capture using SoundDevice.

Design decisions:
- 16 kHz mono int16, matching WebRTC APM's preferred sample rate.
- 160-sample frames = exactly 10 ms, which is the WebRTC APM processing unit.
- The callback is kept absolutely minimal (one queue.put); all heavy
  processing happens downstream in separate threads.
- Audio queue is bounded at 200 frames (~2 seconds) to prevent unbounded
  growth if the downstream pipeline stalls.
"""

import queue
import sounddevice as sd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMPLE_RATE: int = 16_000          # Hz — 16 kHz is the WebRTC APM sweet spot
CHANNELS: int = 1                  # Mono
DTYPE: str = "int16"               # 16-bit PCM
FRAME_SAMPLES: int = 160           # 10 ms × 16 000 Hz = 160 samples per frame
QUEUE_MAX_FRAMES: int = 200        # ~2 s of audio before we start dropping


class AudioCapture:
    """
    Captures microphone audio and places raw PCM bytes onto a queue.

    Usage::

        cap = AudioCapture()
        cap.start()
        while running:
            frame = cap.get_frame(timeout=0.1)   # bytes | None
            ...
        cap.stop()
    """

    def __init__(self):
        self._queue: queue.Queue = queue.Queue(maxsize=QUEUE_MAX_FRAMES)
        self._stream: sd.RawInputStream | None = None
        self._running: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Open the microphone stream."""
        if self._running:
            return

        self._running = True
        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=FRAME_SAMPLES,
            dtype=DTYPE,
            channels=CHANNELS,
            callback=self._callback,
        )
        self._stream.start()
        print("[AudioCapture] Microphone stream started "
              f"({SAMPLE_RATE} Hz, {FRAME_SAMPLES}-sample frames)")

    def stop(self) -> None:
        """Close the microphone stream and drain the queue."""
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        # Drain so stale audio isn't processed on restart
        self._drain()
        print("[AudioCapture] Microphone stream stopped")

    def get_frame(self, timeout: float = 0.1) -> bytes | None:
        """
        Return the next 10 ms PCM frame, or None on timeout.

        Parameters
        ----------
        timeout:
            Seconds to wait for a frame before returning None.
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def sample_rate(self) -> int:
        return SAMPLE_RATE

    @property
    def frame_samples(self) -> int:
        return FRAME_SAMPLES

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _callback(
        self,
        indata,        # numpy array view of the raw audio block
        frames: int,
        time,
        status,
    ) -> None:
        """SoundDevice callback — runs on a dedicated audio thread."""
        if status:
            print(f"[AudioCapture] SoundDevice status: {status}")
        if self._running:
            try:
                self._queue.put_nowait(bytes(indata))
            except queue.Full:
                # Drop the oldest frame to keep latency low
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self._queue.put_nowait(bytes(indata))
                except queue.Full:
                    pass

    def _drain(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
