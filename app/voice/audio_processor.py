# app/voice/audio_processor.py
"""
WebRTC Audio Processing Module (APM) wrapper.

Applies — in order — the WebRTC APM chain:
    High-Pass Filter → Echo Cancellation → Noise Suppression → AGC

Uses the pywebrtc-audio third-party binding.
If the package is not installed or the wheel is incompatible, the processor
degrades gracefully to a pass-through so the rest of the pipeline can still
run (without audio enhancement).

Configuration rationale
-----------------------
NS level 2  ≈ 18 dB suppression — good for fan/AC noise without distorting
             speech. Start here; raise to 3 (21 dB) only if fan is very loud.
AGC enabled — compensates for quiet laptop microphones.
AEC enabled — available if BUG is playing audio; harmless when silent.
HPF enabled — removes low-frequency rumble (desk vibration, AC hum).
"""

import struct
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SAMPLE_RATE: int = 16_000          # Must match AudioCapture.SAMPLE_RATE
CHANNELS: int = 1
NS_LEVEL: int = 2                  # 0=6dB, 1=12dB, 2=18dB, 3=21dB
ENABLE_NS: bool = True
ENABLE_AGC: bool = True
ENABLE_AEC: bool = True            # Low impact when no far-end audio
ENABLE_HPF: bool = True


class AudioProcessor:
    """
    Wraps pywebrtc-audio AudioProcessor to clean microphone frames.

    Parameters
    ----------
    sample_rate : int
        Sample rate in Hz.  Must be 8000, 16000, 32000, or 48000.
    ns_level : int
        Noise suppression aggressiveness (0–3).

    Usage::

        proc = AudioProcessor()
        proc.start()
        clean_frame = proc.process(raw_frame_bytes)
        proc.stop()
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        ns_level: int = NS_LEVEL,
    ):
        self._sample_rate = sample_rate
        self._ns_level = ns_level
        self._processor = None
        self._available = False

        self._init_processor()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """No-op — initialisation is done in __init__."""
        pass

    def stop(self) -> None:
        """Release the WebRTC processor."""
        self._processor = None
        print("[AudioProcessor] Stopped")

    def process(self, frame_bytes: bytes, far_end_bytes: Optional[bytes] = None) -> bytes:
        """
        Process one 10 ms PCM frame through the WebRTC APM chain.

        Parameters
        ----------
        frame_bytes :
            Raw int16 PCM bytes from the microphone (near-end).
        far_end_bytes :
            Optional int16 PCM bytes being played by the speaker (far-end).
            Provide this when BUG is speaking to enable AEC.
            Pass None (default) when the system is silent.

        Returns
        -------
        bytes
            Cleaned int16 PCM bytes.  Same length as input.
            Falls back to input bytes if WebRTC is unavailable.
        """
        if not self._available or self._processor is None:
            return frame_bytes

        try:
            # The pywebrtc-audio API:
            #   process(near: bytes, far: bytes | None) -> bytes
            result = self._processor.process(
                frame_bytes,
                far_end_bytes,
            )
            return result if result else frame_bytes

        except Exception as e:
            print(f"[AudioProcessor] Process error (falling back): {e}")
            return frame_bytes

    @property
    def is_available(self) -> bool:
        """True if the WebRTC APM is active; False if running as pass-through."""
        return self._available

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _init_processor(self) -> None:
        try:
            import pywebrtc_audio  # type: ignore[import]

            self._processor = pywebrtc_audio.AudioProcessor(
                sample_rate=self._sample_rate,
                num_channels=CHANNELS,
                enable_high_pass_filter=ENABLE_HPF,
                enable_noise_suppression=ENABLE_NS,
                noise_suppression_level=self._ns_level,
                enable_gain_control=ENABLE_AGC,
                enable_echo_cancellation=ENABLE_AEC,
            )
            self._available = True
            print(
                f"[AudioProcessor] WebRTC APM ready — "
                f"NS={ENABLE_NS}(L{self._ns_level}), "
                f"AGC={ENABLE_AGC}, AEC={ENABLE_AEC}, HPF={ENABLE_HPF}"
            )

        except ImportError:
            self._available = False
            print(
                "[AudioProcessor] WARNING: pywebrtc-audio not available. "
                "Running as pass-through (no noise suppression / AGC). "
                "Install with: pip install pywebrtc-audio"
            )

        except Exception as e:
            self._available = False
            print(
                f"[AudioProcessor] WARNING: WebRTC APM init failed ({e}). "
                "Running as pass-through."
            )
