# tests/test_accuracy.py
"""
End-to-end accuracy test matrix for the BUG voice pipeline.

This file implements the testing matrix from Section 25 of the
BUG Voice Processing Implementation Document:

    10 commands × 5 conditions × 3 repetitions = 150 tests

Commands tested
---------------
C01  open chrome
C02  open calculator
C03  open notepad
C04  scroll down
C05  scroll up
C06  go back
C07  new tab
C08  refresh
C09  volume up
C10  close window

Conditions
----------
ENV1  Quiet room
ENV2  Fan noise
ENV3  Keyboard noise
ENV4  Speaker audio playing
ENV5  Low microphone volume

How to use
----------
1. Record WAV files for each command × condition using the recorder below:
       python tests/test_accuracy.py --record

2. Run the accuracy tests (requires pre-recorded fixtures):
       pytest tests/test_accuracy.py -v -m accuracy

3. The test matrix table is printed at the end of the session.

WAV file naming convention
--------------------------
    tests/fixtures/<command_id>_<env_id>_<rep>.wav

    Example: tests/fixtures/C04_ENV1_01.wav
             → "scroll down", quiet room, first repetition

Notes
-----
- Tests are marked @pytest.mark.accuracy and are SKIPPED unless fixture files
  exist.  This allows pytest to run the rest of the test suite without WAV files.
- WhisperEngine is loaded once per session (module scope) to avoid repeated
  ~1 s model init times.
- CommandHandler.execute() is mocked to capture the matched command without
  touching the desktop.
"""

import os
import sys
import json
import wave
import struct
import argparse
import time
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.voice.whisper_engine import WhisperEngine
from app.voice.command_normalizer import normalize_command
from app.voice.command_handler import CommandHandler


# ---------------------------------------------------------------------------
# Test matrix definition
# ---------------------------------------------------------------------------

COMMANDS = {
    "C01": "open chrome",
    "C02": "open calculator",
    "C03": "open notepad",
    "C04": "scroll down",
    "C05": "scroll up",
    "C06": "go back",
    "C07": "new tab",
    "C08": "refresh",
    "C09": "volume up",
    "C10": "close window",
}

CONDITIONS = {
    "ENV1": "Quiet room",
    "ENV2": "Fan noise",
    "ENV3": "Keyboard noise",
    "ENV4": "Speaker audio",
    "ENV5": "Low mic volume",
}

REPETITIONS = 3   # per command × condition

FIXTURES_DIR = Path(__file__).parent / "fixtures"
RESULTS_FILE = Path(__file__).parent / "accuracy_results.json"


# ---------------------------------------------------------------------------
# Expected command outputs from CommandHandler
# ---------------------------------------------------------------------------

_EXPECTED_RESULT = {
    "open chrome":      "open_google",
    "open calculator":  None,          # not yet in CommandHandler — update when added
    "open notepad":     None,          # not yet in CommandHandler — update when added
    "scroll down":      "scroll_down",
    "scroll up":        "scroll_up",
    "go back":          "go_back",
    "new tab":          "new_tab",
    "refresh":          "refresh",
    "volume up":        "volume_up",
    "close window":     "close_window",
}


# ---------------------------------------------------------------------------
# Fixtures (session-scoped Whisper engine)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def whisper_engine():
    """Load Faster-Whisper once for the whole accuracy test session."""
    engine = WhisperEngine()
    engine.start()
    yield engine
    engine.stop()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_wav(path: str) -> np.ndarray:
    """Load a 16 kHz mono WAV file and return float32 array in [-1, 1]."""
    with wave.open(path, "rb") as wf:
        assert wf.getframerate() == 16_000, f"WAV must be 16 kHz: {path}"
        assert wf.getnchannels() == 1, f"WAV must be mono: {path}"
        raw = wf.readframes(wf.getnframes())
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return audio


def _fixture_path(cmd_id: str, env_id: str, rep: int) -> Path:
    return FIXTURES_DIR / f"{cmd_id}_{env_id}_{rep:02d}.wav"


def _run_pipeline(
    whisper: WhisperEngine,
    audio: np.ndarray,
    handler: CommandHandler,
) -> tuple[str, Optional[str]]:
    """
    Run Whisper → normalize → CommandHandler.execute() on an audio array.

    Returns (transcript, command_result).
    """
    transcript = whisper.transcribe(audio)
    normalized = normalize_command(transcript)

    with patch("pyautogui.press"), patch("pyautogui.hotkey"), \
         patch("webbrowser.open"):
        result = handler.execute(normalized) if normalized else None

    return normalized, result


# ---------------------------------------------------------------------------
# Accuracy tests
# ---------------------------------------------------------------------------

class TestAccuracyMatrix:
    """
    Parametrized accuracy tests.
    Skipped automatically if WAV fixture files don't exist yet.
    """

    results: dict = {}   # class-level results accumulator

    @pytest.mark.parametrize("cmd_id,cmd_text", list(COMMANDS.items()))
    @pytest.mark.parametrize("env_id,env_label", list(CONDITIONS.items()))
    @pytest.mark.parametrize("rep", range(1, REPETITIONS + 1))
    @pytest.mark.accuracy
    def test_command_recognized(
        self,
        cmd_id, cmd_text,
        env_id, env_label,
        rep,
        whisper_engine,
    ):
        wav = _fixture_path(cmd_id, env_id, rep)

        if not wav.exists():
            pytest.skip(f"Fixture not found: {wav.name}")

        audio = _load_wav(str(wav))
        handler = CommandHandler()

        normalized, result = _run_pipeline(whisper_engine, audio, handler)

        expected = _EXPECTED_RESULT.get(cmd_text)

        print(f"\n[{cmd_id} {env_id} rep{rep}] "
              f"heard='{normalized}' result={result} expected={expected}")

        # Store result for the summary table
        key = f"{cmd_id}_{env_id}_{rep:02d}"
        TestAccuracyMatrix.results[key] = {
            "command": cmd_text,
            "condition": env_label,
            "rep": rep,
            "transcript": normalized,
            "result": result,
            "expected": expected,
            "correct": result == expected,
        }

        if expected is not None:
            assert result == expected, (
                f"Command '{cmd_text}' in {env_label} (rep {rep}): "
                f"got '{result}', expected '{expected}'. "
                f"Transcript: '{normalized}'"
            )


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def _print_accuracy_table(results: dict) -> None:
    """Print the 10×5 command accuracy table to stdout."""
    print("\n" + "=" * 70)
    print("COMMAND ACCURACY MATRIX")
    print("=" * 70)

    header = f"{'Command':<20}" + "".join(f"{e:>10}" for e in CONDITIONS.keys())
    print(header)
    print("-" * 70)

    for cmd_id, cmd_text in COMMANDS.items():
        row = f"{cmd_text:<20}"
        for env_id in CONDITIONS.keys():
            correct = total = 0
            for rep in range(1, REPETITIONS + 1):
                key = f"{cmd_id}_{env_id}_{rep:02d}"
                if key in results:
                    total += 1
                    if results[key]["correct"]:
                        correct += 1
            if total:
                pct = correct * 100 // total
                row += f"{pct:>9}%"
            else:
                row += f"{'n/a':>10}"
        print(row)

    print("=" * 70)
    overall = [r["correct"] for r in results.values()]
    if overall:
        acc = sum(overall) * 100 // len(overall)
        print(f"Overall accuracy: {acc}% ({sum(overall)}/{len(overall)})")


def pytest_sessionfinish(session, exitstatus):
    """Print accuracy table when tests finish (only if results exist)."""
    results = TestAccuracyMatrix.results
    if results:
        _print_accuracy_table(results)

        # Save JSON for the report
        RESULTS_FILE.write_text(
            json.dumps(results, indent=2, default=str)
        )
        print(f"\nResults saved to: {RESULTS_FILE}")


# ---------------------------------------------------------------------------
# WAV recorder (run directly: python tests/test_accuracy.py --record)
# ---------------------------------------------------------------------------

def _record_fixtures(duration: float = 2.5, sample_rate: int = 16_000):
    """Interactive recorder to capture WAV fixtures for all conditions."""
    import sounddevice as sd

    print("\n=== BUG Voice Accuracy Fixture Recorder ===")
    print("For each condition, you'll record each command once.")
    print("Speak clearly when you see [RECORD].\n")

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    for env_id, env_label in CONDITIONS.items():
        input(f"\n--- Condition: {env_label} ---\nSet up the condition, then press Enter.")

        for rep in range(1, REPETITIONS + 1):
            print(f"\n  Repetition {rep}/{REPETITIONS}")

            for cmd_id, cmd_text in COMMANDS.items():
                wav_path = _fixture_path(cmd_id, env_id, rep)
                if wav_path.exists():
                    print(f"  ✓ {wav_path.name} already exists — skipping")
                    continue

                input(f"  Ready to record '{cmd_text}'. Press Enter then speak...")
                print("  [RECORDING]", end="", flush=True)

                audio = sd.rec(
                    int(duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype="int16",
                )
                sd.wait()
                print(" [DONE]")

                with wave.open(str(wav_path), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio.tobytes())

                print(f"  Saved: {wav_path.name}")

    print("\n✓ All fixtures recorded!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BUG accuracy fixture recorder")
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record WAV fixtures for the accuracy test matrix",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=2.5,
        help="Recording duration in seconds per command (default: 2.5)",
    )
    args = parser.parse_args()

    if args.record:
        _record_fixtures(duration=args.duration)
    else:
        parser.print_help()
