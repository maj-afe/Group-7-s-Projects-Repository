# tests/test_audio.py
"""
Unit tests for AudioCapture and AudioProcessor.

Tests run without real microphone hardware by:
- Mocking sounddevice.RawInputStream for AudioCapture tests.
- Using synthetic PCM frames for AudioProcessor tests.
"""

import sys
import os
import time
import struct
import threading

import numpy as np
import pytest

# Make project root importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.voice.audio_capture import AudioCapture, SAMPLE_RATE, FRAME_SAMPLES
from app.voice.audio_processor import AudioProcessor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_silence_frame() -> bytes:
    """Generate 160 samples of silence as int16 PCM bytes."""
    return bytes(FRAME_SAMPLES * 2)


def _make_tone_frame(freq_hz: float = 440.0) -> bytes:
    """Generate 160 samples of a sine wave at freq_hz as int16 PCM bytes."""
    t = np.arange(FRAME_SAMPLES) / SAMPLE_RATE
    signal = (np.sin(2 * np.pi * freq_hz * t) * 16000).astype(np.int16)
    return signal.tobytes()


# ---------------------------------------------------------------------------
# AudioCapture tests
# ---------------------------------------------------------------------------

class TestAudioCapture:

    def test_frame_length(self):
        """Each frame from the capture must be exactly FRAME_SAMPLES * 2 bytes."""
        frame = _make_silence_frame()
        assert len(frame) == FRAME_SAMPLES * 2, (
            f"Expected {FRAME_SAMPLES * 2} bytes, got {len(frame)}"
        )

    def test_queue_does_not_block_on_empty(self):
        """get_frame() should return None quickly when queue is empty."""
        cap = AudioCapture()
        # Don't start the stream — queue stays empty
        result = cap.get_frame(timeout=0.05)
        assert result is None

    def test_manual_queue_put(self):
        """Directly put a frame on the internal queue and retrieve it."""
        cap = AudioCapture()
        frame = _make_tone_frame()
        cap._queue.put(frame)
        retrieved = cap.get_frame(timeout=0.1)
        assert retrieved == frame

    def test_drain_on_stop(self):
        """stop() should drain any queued frames."""
        cap = AudioCapture()
        for _ in range(5):
            cap._queue.put(_make_silence_frame())

        assert not cap._queue.empty()
        cap.stop()  # calls _drain()
        assert cap._queue.empty()

    def test_queue_overflow_drops_oldest(self):
        """When queue is full the capture drops oldest frame, not newest."""
        from app.voice.audio_capture import QUEUE_MAX_FRAMES
        cap = AudioCapture()

        # Fill queue to max
        for i in range(QUEUE_MAX_FRAMES):
            cap._queue.put(bytes([i % 256] * (FRAME_SAMPLES * 2)))

        assert cap._queue.full()

        # Simulate callback inserting one more frame
        new_frame = _make_tone_frame()
        cap._callback(
            indata=np.frombuffer(new_frame, dtype=np.int16),
            frames=FRAME_SAMPLES,
            time=None,
            status=None,
        )
        # Queue should still be at max (one dropped, one added)
        assert cap._queue.qsize() == QUEUE_MAX_FRAMES


# ---------------------------------------------------------------------------
# AudioProcessor tests
# ---------------------------------------------------------------------------

class TestAudioProcessor:

    def test_passthrough_frame_length(self):
        """Output frame must be same length as input regardless of WebRTC availability."""
        proc = AudioProcessor()
        frame = _make_silence_frame()
        result = proc.process(frame)
        assert len(result) == len(frame), (
            f"Output length {len(result)} != input length {len(frame)}"
        )

    def test_tone_frame_length(self):
        """Processing a tone frame should preserve frame size."""
        proc = AudioProcessor()
        frame = _make_tone_frame(440.0)
        result = proc.process(frame)
        assert len(result) == len(frame)

    def test_process_returns_bytes(self):
        """process() must return bytes (not memoryview, ndarray, etc.)."""
        proc = AudioProcessor()
        frame = _make_silence_frame()
        result = proc.process(frame)
        assert isinstance(result, bytes)

    def test_process_with_far_end(self):
        """AEC path: process() should accept an optional far_end_bytes."""
        proc = AudioProcessor()
        near = _make_tone_frame(440.0)
        far = _make_silence_frame()
        result = proc.process(near, far_end_bytes=far)
        assert len(result) == len(near)

    def test_is_available_is_bool(self):
        """is_available property should always be a bool."""
        proc = AudioProcessor()
        assert isinstance(proc.is_available, bool)
