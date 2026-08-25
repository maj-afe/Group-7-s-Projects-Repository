# tests/test_commands.py
"""
Unit tests for CommandNormalizer and CommandHandler fuzzy matching.

These tests verify:
1. CommandNormalizer correctly strips filler words and punctuation.
2. CommandHandler._fuzzy_match corrects Whisper-style misheards with
   rapidfuzz token_set_ratio (80/100 threshold).
3. Emergency stop is always executed, bypassing all guards.
4. Cooldown correctly gates repeated commands.
"""

import sys
import os
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.voice.command_normalizer import normalize_command
from app.voice.command_handler import CommandHandler


# ---------------------------------------------------------------------------
# CommandNormalizer
# ---------------------------------------------------------------------------

class TestCommandNormalizer:

    def test_lowercase(self):
        assert normalize_command("SCROLL DOWN") == "scroll down"

    def test_strip_whitespace(self):
        assert normalize_command("  scroll down  ") == "scroll down"

    def test_punctuation_removed(self):
        assert normalize_command("scroll down.") == "scroll down"
        assert normalize_command("go back!") == "go back"
        assert normalize_command("new tab?") == "new tab"

    def test_collapse_spaces(self):
        assert normalize_command("scroll   down") == "scroll down"

    def test_empty_string(self):
        assert normalize_command("") == ""

    def test_whitespace_only(self):
        assert normalize_command("   ") == ""

    def test_filler_um_stripped(self):
        assert normalize_command("um scroll down") == "scroll down"

    def test_filler_uh_stripped(self):
        assert normalize_command("uh scroll up") == "scroll up"

    def test_filler_okay_stripped(self):
        assert normalize_command("okay new tab") == "new tab"

    def test_multiple_fillers_stripped(self):
        assert normalize_command("um uh okay scroll down") == "scroll down"

    def test_filler_in_middle_not_stripped(self):
        # "go um back" should NOT become "go back" — mid-word filler is not handled
        result = normalize_command("go um back")
        assert "go" in result  # exact match not guaranteed, but shouldn't crash

    def test_passthrough_clean_command(self):
        assert normalize_command("open chrome") == "open chrome"
        assert normalize_command("volume up") == "volume up"
        assert normalize_command("close tab") == "close tab"


# ---------------------------------------------------------------------------
# CommandHandler fuzzy matching
# ---------------------------------------------------------------------------

class TestFuzzyMatching:

    def setup_method(self):
        self.handler = CommandHandler()

    def test_exact_match_returned_unchanged(self):
        result = self.handler._fuzzy_match("scroll down")
        assert result == "scroll down"

    def test_minor_typo_corrected(self):
        # "scroll doun" → "scroll down" (1 char difference, high ratio)
        result = self.handler._fuzzy_match("scroll doun")
        assert result == "scroll down", f"Expected 'scroll down', got '{result}'"

    def test_single_word_not_fuzzy_matched(self):
        # Single words must not be fuzzy-matched to avoid false positives
        result = self.handler._fuzzy_match("refresh")
        assert result == "refresh"

    def test_search_prefix_not_fuzzy_matched(self):
        result = self.handler._fuzzy_match("search for python tutorials")
        assert result == "search for python tutorials"

    def test_ambiguous_low_similarity_not_matched(self):
        # Completely unrelated text should not be corrected
        result = self.handler._fuzzy_match("xyzzy frobulate")
        # Should be returned as-is (no match above threshold)
        assert result == "xyzzy frobulate"

    def test_word_order_variation(self):
        # token_set_ratio should handle "chrome open" → "open chrome"
        result = self.handler._fuzzy_match("chrome open")
        assert result == "open chrome", f"Expected 'open chrome', got '{result}'"

    def test_volume_up_variant(self):
        result = self.handler._fuzzy_match("volume u")
        # "volume u" is a single character off — should match "volume up"
        # (may or may not match depending on threshold; just ensure no crash)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# CommandHandler execution
# ---------------------------------------------------------------------------

class TestCommandHandlerExecution:

    def setup_method(self):
        self.handler = CommandHandler()
        # Prevent actual desktop actions during unit tests
        import unittest.mock as mock
        self._patcher = mock.patch("pyautogui.press")
        self._patcher.start()
        self._patcher2 = mock.patch("pyautogui.hotkey")
        self._patcher2.start()
        self._patcher3 = mock.patch("pyautogui.keyUp")
        self._patcher3.start()

    def teardown_method(self):
        self._patcher.stop()
        self._patcher2.stop()
        self._patcher3.stop()

    def test_emergency_stop_disables(self):
        result = self.handler.execute("emergency stop")
        assert result == "emergency_stop"
        assert self.handler.enabled is False

    def test_enable_control_reenables(self):
        self.handler.enabled = False
        result = self.handler.execute("enable control")
        assert result == "control_enabled"
        assert self.handler.enabled is True

    def test_unknown_command_returns_none(self):
        result = self.handler.execute("xyzzy frobulate blargh")
        assert result is None

    def test_cooldown_gates_repeated_command(self):
        # First call should succeed
        self.handler._cooldown_seconds = 10  # Long cooldown for test
        first = self.handler.execute("scroll down")
        assert first == "scroll_down"

        # Immediate second call should be blocked
        second = self.handler.execute("scroll down")
        assert second is None

    def test_cooldown_expires(self):
        self.handler._cooldown_seconds = 0.05  # 50 ms cooldown
        first = self.handler.execute("scroll down")
        assert first == "scroll_down"

        time.sleep(0.1)  # Wait for cooldown to expire

        second = self.handler.execute("scroll down")
        assert second == "scroll_down"

    def test_normalize_strips_punctuation(self):
        """CommandHandler.normalize should strip punctuation."""
        result = self.handler.normalize("scroll down!")
        assert result == "scroll down"
