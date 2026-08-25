# tests/test_vad.py
"""
Unit tests for the SileroVAD state machine.

Validates pre-roll / post-roll buffer logic, state transitions, and the
segment-ready callback — without loading the actual Silero model.

The mock _speech_prob is injected directly so tests run offline and fast.
"""

import sys
import os
import collections

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.voice.vad import (
    SileroVAD, _State,
    RAW_FRAME_SAMPLES, SILERO_CHUNK_SAMPLES,
    PRE_ROLL_CHUNKS, POST_ROLL_CHUNKS, MAX_SEGMENT_CHUNKS,
    SAMPLE_RATE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw_frame(amplitude: int = 0) -> bytes:
    """160 samples of int16 PCM (10 ms @ 16 kHz)."""
    return bytes([amplitude % 256, 0] * RAW_FRAME_SAMPLES)


def _silence_frame() -> bytes:
    return _make_raw_frame(0)


def _speech_frame() -> bytes:
    return _make_raw_frame(100)


def _frames_per_chunk() -> int:
    """How many 160-sample frames make one 512-sample Silero chunk."""
    import math
    return math.ceil(SILERO_CHUNK_SAMPLES / RAW_FRAME_SAMPLES)


def _make_vad(speech_prob_fn=None):
    """
    Create a SileroVAD with _speech_prob mocked out.

    speech_prob_fn: callable(chunk_bytes: bytes) -> float
    """
    segments = []

    def on_segment(audio_np, sr):
        segments.append((audio_np, sr))

    vad = SileroVAD(on_segment=on_segment)

    # Skip real model loading — inject mock
    vad._model = object()  # non-None sentinel
    # Patch _speech_prob at instance level
    if speech_prob_fn:
        vad._speech_prob = speech_prob_fn
    else:
        vad._speech_prob = lambda chunk: 0.0

    vad._reset()
    return vad, segments


def _feed_chunks(vad, n_chunks: int, prob: float) -> None:
    """
    Feed exactly n_chunks worth of raw frames into vad,
    with _speech_prob returning prob for each chunk.
    """
    vad._speech_prob = lambda chunk: prob
    frames_per_chunk = _frames_per_chunk()
    for _ in range(n_chunks * frames_per_chunk):
        vad.process_frame(_speech_frame() if prob >= 0.5 else _silence_frame())


# ---------------------------------------------------------------------------
# State machine tests
# ---------------------------------------------------------------------------

class TestVADStateMachine:

    def test_initial_state_is_waiting(self):
        vad, _ = _make_vad()
        assert vad._state == _State.WAITING

    def test_silence_stays_waiting(self):
        """Many silence chunks must keep the VAD in WAITING state."""
        vad, segments = _make_vad()
        _feed_chunks(vad, 20, prob=0.0)
        assert vad._state == _State.WAITING
        assert len(segments) == 0

    def test_speech_transitions_to_speaking(self):
        """One chunk with prob >= threshold should start SPEAKING."""
        vad, _ = _make_vad()
        _feed_chunks(vad, 1, prob=0.9)
        assert vad._state == _State.SPEAKING

    def test_post_roll_triggers_segment(self):
        """
        After speech ends, POST_ROLL_CHUNKS of silence should finalise the segment.
        """
        vad, segments = _make_vad()

        # Speech
        _feed_chunks(vad, 5, prob=0.95)
        assert vad._state == _State.SPEAKING

        # Post-roll silence
        _feed_chunks(vad, POST_ROLL_CHUNKS + 1, prob=0.0)

        assert len(segments) == 1
        assert vad._state == _State.WAITING

    def test_pre_roll_included_in_segment(self):
        """
        Pre-roll chunks captured during WAITING should be prepended
        to the emitted segment.
        """
        vad, segments = _make_vad()

        # Fill pre-roll ring buffer
        _feed_chunks(vad, PRE_ROLL_CHUNKS, prob=0.0)

        # Speech
        _feed_chunks(vad, 3, prob=0.9)

        # Silence to finalise
        _feed_chunks(vad, POST_ROLL_CHUNKS + 1, prob=0.0)

        assert len(segments) == 1
        audio_np, sr = segments[0]

        # Segment should be at least pre-roll + 3 speech chunks long
        min_samples = (PRE_ROLL_CHUNKS + 3) * SILERO_CHUNK_SAMPLES
        assert len(audio_np) >= min_samples, (
            f"Segment too short: {len(audio_np)} < {min_samples}"
        )

    def test_max_segment_cap_triggers_emission(self):
        """Continuous speech beyond MAX_SEGMENT_CHUNKS should force-finalise."""
        vad, segments = _make_vad()
        _feed_chunks(vad, MAX_SEGMENT_CHUNKS + 5, prob=0.99)
        assert len(segments) >= 1

    def test_segment_audio_is_float32_in_range(self):
        """The emitted segment must be float32 in [-1, 1]."""
        vad, segments = _make_vad()

        _feed_chunks(vad, 5, prob=0.9)
        _feed_chunks(vad, POST_ROLL_CHUNKS + 1, prob=0.0)

        assert len(segments) == 1
        audio_np, sr = segments[0]
        assert audio_np.dtype == np.float32
        assert np.all(audio_np >= -1.0) and np.all(audio_np <= 1.0)

    def test_segment_sample_rate_is_correct(self):
        vad, segments = _make_vad()
        _feed_chunks(vad, 5, prob=0.9)
        _feed_chunks(vad, POST_ROLL_CHUNKS + 1, prob=0.0)
        assert len(segments) == 1
        _, sr = segments[0]
        assert sr == SAMPLE_RATE

    def test_reset_clears_all_state(self):
        """_reset() should return to WAITING with empty buffers."""
        vad, _ = _make_vad()
        _feed_chunks(vad, 3, prob=0.9)
        assert vad._state == _State.SPEAKING

        vad._reset()

        assert vad._state == _State.WAITING
        assert len(vad._segment_chunks) == 0
        assert len(vad._pre_roll) == 0
        assert vad._silence_chunk_count == 0
        assert vad._raw_accum_samples == 0

    def test_frame_accumulation_needs_multiple_frames_per_chunk(self):
        """A single 160-sample frame should NOT trigger a Silero inference."""
        vad, segments = _make_vad(speech_prob_fn=lambda c: 0.99)

        # Feed ONE raw frame — not enough for a full chunk
        vad.process_frame(_speech_frame())

        # No chunk processed yet → still WAITING
        assert vad._state == _State.WAITING

    def test_two_separate_commands_emit_two_segments(self):
        """Two speech bursts separated by enough silence → two segments."""
        vad, segments = _make_vad()

        # First command
        _feed_chunks(vad, 5, prob=0.9)
        _feed_chunks(vad, POST_ROLL_CHUNKS + 1, prob=0.0)

        # Second command
        _feed_chunks(vad, 5, prob=0.9)
        _feed_chunks(vad, POST_ROLL_CHUNKS + 1, prob=0.0)

        assert len(segments) == 2
