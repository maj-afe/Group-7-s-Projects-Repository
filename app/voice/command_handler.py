

# app/voice/command_handler.py

import os  # ADDED: For file operations in app launcher
import re
import threading
import time
import webbrowser
from urllib.parse import quote_plus
import subprocess
import pyautogui

# Disable failsafe: Since BUG uses head tracking to move the mouse,
# the cursor will naturally hit the corners of the screen. We cannot
# have PyAutoGUI crashing the app every time this happens.
pyautogui.FAILSAFE = False

class CommandHandler:
    """
    Desktop voice command engine.

    Converts recognized speech into Windows-level
    mouse, keyboard, browser and application actions.

    Key design decisions:
    - Fuzzy matching is ONLY applied to multi-word commands.
      Single-word commands are NEVER fuzzy-matched to avoid
      dangerous false positives (e.g. "escape" -> "paste").
    - A per-command cooldown tracks the COMMAND key (not the
      raw transcript) so that cooldowns work even when the
      user says the same command with slightly different words.
    - Dictation mode bypasses fuzzy matching entirely so that
      typed text is not corrupted.
    - Emergency stop disables all commands EXCEPT "enable control"
      which always bypasses the stop to allow recovery.
    """

    def __init__(self):
        self.last_command = ""
        self.command_history = []
        self.max_history = 20

        # Dictation mode - raw text is typed, not matched as commands
        self.dictation_mode = False

        # Emergency stop flag
        self.enabled = True

        # Continuous scrolling state (kept for API compatibility)
        self.scrolling = False
        self.scroll_direction = 0
        self.scroll_thread = None
        self.scroll_speed = 5
        self.scroll_interval = 0.04
        self.scroll_stop_event = threading.Event()

        # Cooldown: track last execution time per COMMAND (not transcript)
        # so that cooldowns are consistent regardless of how a command is
        # phrased or which misheard alias triggered it.
        self._last_exec_time: dict = {}
        self._cooldown_seconds = 1.5

        # Pre-build the multi-word command list for fuzzy matching.
        # IMPORTANT: single-word commands are intentionally excluded
        # from this list because they are too short for safe fuzzy matching.
        self._multi_word_commands = [
            # Emergency
            "emergency stop", "stop automation", "stop control", "disable control",
            # Voice/control
            "enable voice", "turn on voice", "disable voice", "turn off voice",
            "enable control", "enable automation",
            # Mouse
            "left click", "double click", "right click",
            # Scroll
            "scroll down", "page down", "scroll up", "page up",
            "scroll faster", "scroll slower", "stop scrolling", "stop scroll",
            # Browser
            "go back", "previous page", "go forward", "next page",
            "refresh page", "reload page",
            # Tabs
            "new tab", "open new tab", "close tab", "next tab",
            "previous tab", "prev tab", "change tab", "change step",
            "change that",
            # Zoom
            "zoom in", "zoom out", "reset zoom",
            "full screen", "exit fullscreen",
            # Text
            "select all", "delete last word", "delete word",
            "press enter", "press tab", "press escape", "press backspace",
            "start of line", "end of line",
            "select next word", "select previous word",
            # Window
            "switch window", "next window", "change window",
            "minimize window", "close window",
            # Media
            "volume up", "increase volume", "sound up",
            "volume down", "decrease volume", "sound down",
            "next video", "next media",
            "skip forward", "forward ten seconds", "forward 10 seconds", "jump ahead",
            "skip back", "back ten seconds", "video back",
            # Browser pages
            "open history", "open downloads", "open bookmarks",
            # Sites
            "open youtube", "open google", "open chrome",
            "open facebook", "open instagram", "open github",
            "open reddit", "open twitter", "open netflix", "open amazon",
            "open linkedin",
            # Typing
            "start typing", "start dictation", "stop typing", "stop dictation",
            "exit typing", "end typing",
            # Head/mouth/calibration
            "enable head tracking", "turn on head tracking",
            "disable head tracking", "turn off head tracking",
            "enable mouth click", "disable mouth click",
            "start calibration", "calibrate mouth", "mouth calibrate",
            "start mouth calibration", "reset calibration",
            # System
            "save as", "open file", "new file",
            "open start menu", "open task manager", "lock computer",
            "open notepad", "open note pad", "open calculator",
        ]

    # =========================================================
    # TEXT NORMALIZATION
    # =========================================================

    def normalize(self, text: str) -> str:
        """Lowercase, strip punctuation, collapse whitespace, deduplicate."""
        text = text.lower().strip()
        text = re.sub(r"""[.,!?;:'"()\[\]{}<>]""", "", text)
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        text = self._deduplicate(text)
        return text

    def _deduplicate(self, text: str) -> str:
        """
        Collapse Whisper's word-repetition artefacts.

        Examples:
            'copy copy'                    -> 'copy'
            'open note pad open note pad'  -> 'open note pad'
            'scroll down scroll down'      -> 'scroll down'
            'open not bad ... open'        -> 'open not bad'  (partial tail)
        """
        words = text.split()
        n = len(words)
        if n < 2:
            return text
        # Try all unit lengths from 1 up to half the total word count
        for unit_len in range(1, n // 2 + 1):
            unit = words[:unit_len]
            reps = n // unit_len
            if unit * reps == words[:unit_len * reps]:
                leftover = words[unit_len * reps:]
                # Accept if no leftover OR if leftover is a prefix of the unit
                # (handles e.g. 'abc abc abc ab' -> 'abc')
                if not leftover or unit[:len(leftover)] == leftover:
                    return " ".join(unit)
        return text

    # =========================================================
    # COOLDOWN CHECK (keyed on COMMAND, not raw transcript)
    # =========================================================

    def _is_on_cooldown(self, command_key: str) -> bool:
        """
        Returns True if this command was executed too recently.
        Keyed on the command result (e.g. 'scroll_down'), NOT the
        raw transcript, so all aliases for the same action share one cooldown.
        """
        now = time.time()
        last = self._last_exec_time.get(command_key, 0.0)
        return (now - last) < self._cooldown_seconds

    def _mark_executed(self, command_key: str):
        self._last_exec_time[command_key] = time.time()

    # =========================================================
    # FUZZY MATCHING (multi-word only)
    # =========================================================

    def _fuzzy_match(self, text: str) -> str:
        """
        Attempts to correct a multi-word transcript using rapidfuzz.

        Uses token_set_ratio which handles:
        - Word order variation ("chrome open" → "open chrome")
        - Extra filler words from Whisper
        - Indian-English pronunciation variants

        Single-word inputs are returned unchanged — they are too short
        and ambiguous for safe fuzzy correction.
        """
        # Never fuzzy-match single words — too many false positives
        if len(text.split()) < 2:
            return text

        # Never fuzzy-match search/open queries — they contain arbitrary words
        if text.startswith("search"):
            return text

        try:
            from rapidfuzz import process as fz_process  # type: ignore[import]
            from rapidfuzz import fuzz as fz_fuzz         # type: ignore[import]

            result = fz_process.extractOne(
                text,
                self._multi_word_commands,
                scorer=fz_fuzz.token_set_ratio,
                score_cutoff=80,   # 0–100 scale; 80 ≈ high confidence
            )

            if result is not None:
                corrected, score, _ = result
                if corrected != text:
                    print(f"[Voice] Fuzzy corrected: '{text}' → '{corrected}' ({score:.0f}%)")
                return corrected

        except ImportError:
            # Graceful fallback: return text unchanged so CommandHandler
            # can still attempt exact matching.
            print("[Voice] rapidfuzz not installed — skipping fuzzy match")

        return text

    # =========================================================
    # CONTINUOUS SCROLLING (kept for API compatibility)
    # =========================================================

    def start_scrolling(self, direction: int):
        """Start continuous scrolling. direction: -1=down, 1=up"""
        if self.scrolling:
            self.stop_scrolling()

        self.scrolling = True
        self.scroll_direction = direction
        self.scroll_stop_event.clear()

        self.scroll_thread = threading.Thread(
            target=self._scroll_loop,
            daemon=True
        )
        self.scroll_thread.start()

        name = "down" if direction < 0 else "up"
        print(f"[Voice] Continuous scroll {name} started")

    def _scroll_loop(self):
        while self.scrolling and not self.scroll_stop_event.is_set():
            pyautogui.scroll(self.scroll_direction * self.scroll_speed)
            time.sleep(self.scroll_interval)
        print("[Voice] Scroll loop ended")

    def stop_scrolling(self):
        """Stop continuous scrolling immediately."""
        if not self.scrolling:
            return
        self.scrolling = False
        self.scroll_stop_event.set()
        if self.scroll_thread and self.scroll_thread.is_alive():
            self.scroll_thread.join(timeout=0.5)
        self.scroll_thread = None
        print("[Voice] Scrolling stopped")

    def increase_scroll_speed(self):
        if self.scroll_speed < 20:
            self.scroll_speed += 2
            print(f"[Voice] Scroll speed: {self.scroll_speed}")

    def decrease_scroll_speed(self):
        if self.scroll_speed > 2:
            self.scroll_speed -= 2
            print(f"[Voice] Scroll speed: {self.scroll_speed}")

    # =========================================================
    # DYNAMIC APPLICATION LAUNCHER (NEW)
    # =========================================================

    def _get_installed_apps(self) -> dict:
        """
        Get installed applications from Windows Start Menu using PowerShell.
        Returns a dictionary: {app_name_lower: (display_name, app_id)}
        """
        try:
            import json
            
            # PowerShell command to get Start Apps
            ps_command = """
            $apps = Get-StartApps
            $apps | ForEach-Object {
                [PSCustomObject]@{
                    Name = $_.Name
                    AppId = $_.AppId
                }
            } | ConvertTo-Json -Compress
            """
            
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                print(f"[Voice] PowerShell error: {result.stderr}")
                return {}
            
            # Parse the JSON output
            if not result.stdout or result.stdout.strip() == "":
                print("[Voice] No applications found")
                return {}
            
            apps_data = json.loads(result.stdout)
            
            # Handle single app case (json.loads returns dict, not list)
            if isinstance(apps_data, dict):
                apps_data = [apps_data]
            
            # Build lookup dictionary
            app_lookup = {}
            for app in apps_data:
                if isinstance(app, dict) and "Name" in app and "AppId" in app:
                    name = app["Name"].lower()
                    app_id = app["AppId"]
                    display_name = app["Name"]
                    app_lookup[name] = (display_name, app_id)
            
            print(f"[Voice] Loaded {len(app_lookup)} installed applications")
            return app_lookup
            
        except subprocess.TimeoutExpired:
            print("[Voice] PowerShell timeout while fetching applications")
            return {}
        except json.JSONDecodeError as e:
            print(f"[Voice] Failed to parse application list: {e}")
            return {}
        except Exception as e:
            print(f"[Voice] Error fetching applications: {e}")
            return {}

    def open_installed_app(self, app_name: str) -> bool:
        """
        Open an installed Windows application by name.
        
        Args:
            app_name: Name of the application to open (case-insensitive)
            
        Returns:
            bool: True if application was launched successfully, False otherwise
        """
        if not app_name or len(app_name.strip()) < 2:
            return False
            
        app_name = app_name.strip()
        app_lookup = self._get_installed_apps()
        
        if not app_lookup:
            print(f"[Voice] Could not retrieve installed applications list")
            return False
        
        # Step 1: Try exact match
        exact_match = app_name.lower()
        if exact_match in app_lookup:
            display_name, app_id = app_lookup[exact_match]
            try:
                # Launch using shell:AppsFolder
                subprocess.Popen(f'explorer.exe shell:AppsFolder\\{app_id}')
                print(f"[Voice] Launched: {display_name}")
                return True
            except Exception as e:
                print(f"[Voice] Failed to launch {display_name}: {e}")
                return False
        
        # Step 2: Try partial match (app_name is contained in the application name)
        partial_matches = []
        for app_display_name, (display_name, app_id) in app_lookup.items():
            if app_name.lower() in app_display_name or app_display_name in app_name.lower():
                partial_matches.append((app_display_name, display_name, app_id))
        
        if partial_matches:
            # Sort by relevance (shorter names first for better matching)
            partial_matches.sort(key=lambda x: len(x[0]))
            
            # Try launching the best match
            for app_key, display_name, app_id in partial_matches:
                try:
                    subprocess.Popen(f'explorer.exe shell:AppsFolder\\{app_id}')
                    print(f"[Voice] Launched: {display_name}")
                    return True
                except Exception as e:
                    print(f"[Voice] Failed to launch {display_name}: {e}")
                    continue
        
        # Step 3: Try launching common executables directly (fallback for non-Start Menu apps)
        # This handles apps that might not show up in Get-StartApps
        common_paths = [
            f"C:\\Program Files\\{app_name}\\{app_name}.exe",
            f"C:\\Program Files (x86)\\{app_name}\\{app_name}.exe",
            f"C:\\Program Files\\{app_name}",
            f"C:\\Program Files (x86)\\{app_name}",
        ]
        
        for path in common_paths:
            try:
                # Try to find .exe files in the directory
                import glob
                exe_files = glob.glob(f"{path}\\*.exe")
                for exe in exe_files:
                    if app_name.lower() in os.path.basename(exe).lower():
                        subprocess.Popen([exe])
                        print(f"[Voice] Launched: {os.path.basename(exe)}")
                        return True
            except Exception:
                continue
        
        print(f"[Voice] Application not found: {app_name}")
        return False

    # =========================================================
    # MAIN COMMAND PROCESSOR
    # =========================================================

    def execute(self, transcript: str):

        normalized = self.normalize(transcript)

        if not normalized:
            return None

        # ----------------------------------------------------------
        # DICTATION MODE: bypass all matching, type the raw text
        # ----------------------------------------------------------
        if self.dictation_mode and self.enabled:
            stop_phrases = {
                "stop typing", "stop dictation",
                "exit typing", "end typing"
            }
            if normalized in stop_phrases:
                self.dictation_mode = False
                print("[Voice] Dictation stopped")
                return "stop_typing"

            # Type directly - no fuzzy matching on dictated text
            pyautogui.write(normalized + " ", interval=0.02)
            self._save_history("dictation", normalized)
            return "dictation"

        # ----------------------------------------------------------
        # APPLY FUZZY CORRECTION (multi-word only)
        # ----------------------------------------------------------
        normalized = self._fuzzy_match(normalized)

        print(f"[Voice] Heard: '{normalized}'")

        # ===========================================================
        # ENABLE CONTROL - always works even after emergency stop
        # ===========================================================

        if normalized in {"enable control", "enable automation"}:
            self.enabled = True
            print("[Voice] Control re-enabled")
            return self._done("control_enabled", "control_enabled")

        # If system is disabled, ignore all other commands
        if not self.enabled:
            print(f"[Voice] System disabled, ignoring: '{normalized}'")
            return None

        # ===========================================================
        # EMERGENCY STOP (highest priority, skips cooldown)
        # ===========================================================

        if normalized in {
            "emergency stop", "stop automation",
            "stop control", "disable control"
        }:
            self.enabled = False
            self.dictation_mode = False
            if self.scrolling:
                self.stop_scrolling()
            pyautogui.keyUp("ctrl")
            pyautogui.keyUp("shift")
            pyautogui.keyUp("alt")
            print("[Voice] !!! EMERGENCY STOP !!!")
            # Emergency stop bypasses cooldown — log it but don't gate on it
            self._mark_executed("emergency_stop")
            self._save_history("emergency_stop", normalized)
            return "emergency_stop"

        # ----------------------------------------------------------
        # COOLDOWN CHECK (keyed on COMMAND, not transcript)
        # ----------------------------------------------------------
        # All commands below go through cooldown. We resolve the
        # command key first (via a helper) and check cooldown before
        # executing. This is handled inline per section.

        # ===========================================================
        # VOICE TOGGLES
        # ===========================================================

        if normalized in {"enable voice", "turn on voice"}:
            return self._done_if_ready("voice_enabled", normalized)

        if normalized in {"disable voice", "turn off voice"}:
            return self._done_if_ready("voice_disabled", normalized)

        # ===========================================================
        # MOUSE
        # ===========================================================

        if normalized in {"click", "left click"}:
            pyautogui.click()
            return self._done_if_ready("click", normalized)

        if normalized in {"double click", "double-click"}:
            pyautogui.doubleClick(interval=0.1)
            return self._done_if_ready("double_click", normalized)

        if normalized in {"right click", "right-click"}:
            pyautogui.rightClick()
            return self._done_if_ready("right_click", normalized)

        # ===========================================================
        # SCROLL  (one page at a time per command)
        # ===========================================================

        if normalized in {
            "scroll down", "page down",
            # Vosk misheard aliases for "scroll down"
            "sold out", "rolled out", "slow down", "pull down",
            "roll down", "go down",
        }:
            if self._is_on_cooldown("scroll_down"):
                return None
            pyautogui.press("pagedown")
            return self._done("scroll_down", "scroll_down")

        if normalized in {
            "scroll up", "page up", "up",
            # Vosk misheard aliases for "scroll up"
            "roll up", "pull up", "hold up", "grow up",
        }:
            if self._is_on_cooldown("scroll_up"):
                return None
            pyautogui.press("pageup")
            return self._done("scroll_up", "scroll_up")

        if normalized == "scroll faster":
            if self._is_on_cooldown("scroll_faster"):
                return None
            pyautogui.press("pagedown", presses=3, interval=0.08)
            return self._done("scroll_faster", "scroll_faster")

        if normalized == "scroll slower":
            if self._is_on_cooldown("scroll_slower"):
                return None
            pyautogui.press("down", presses=5, interval=0.04)
            return self._done("scroll_slower", "scroll_slower")

        if normalized in {"stop scrolling", "stop scroll"}:
            return self._done_if_ready("stop_scrolling", normalized)

        # ===========================================================
        # BROWSER NAVIGATION
        # ===========================================================

        if normalized in {"go back", "previous page"}:
            pyautogui.hotkey("alt", "left")
            return self._done_if_ready("go_back", normalized)

        if normalized in {"go forward", "next page"}:
            pyautogui.hotkey("alt", "right")
            return self._done_if_ready("go_forward", normalized)

        if normalized in {"refresh", "refresh page", "reload", "reload page"}:
            pyautogui.hotkey("ctrl", "r")
            return self._done_if_ready("refresh", normalized)

        # ===========================================================
        # TABS
        # ===========================================================

        if normalized in {"new tab", "open new tab"}:
            pyautogui.hotkey("ctrl", "t")
            return self._done_if_ready("new_tab", normalized)

        if normalized == "close tab":
            pyautogui.hotkey("ctrl", "w")
            return self._done_if_ready("close_tab", normalized)

        if normalized in {
            "next tab", "change tab", "change step", "change that",
            "next step", "change type", "next",
        }:
            pyautogui.hotkey("ctrl", "tab")
            return self._done_if_ready("next_tab", normalized)

        if normalized in {"previous tab", "prev tab"}:
            pyautogui.hotkey("ctrl", "shift", "tab")
            return self._done_if_ready("previous_tab", normalized)

        # ===========================================================
        # ZOOM
        # ===========================================================

        if normalized == "zoom in":
            pyautogui.hotkey("ctrl", "=")
            return self._done_if_ready("zoom_in", normalized)

        if normalized == "zoom out":
            pyautogui.hotkey("ctrl", "-")
            return self._done_if_ready("zoom_out", normalized)

        if normalized == "reset zoom":
            pyautogui.hotkey("ctrl", "0")
            return self._done_if_ready("reset_zoom", normalized)

        # ===========================================================
        # FULLSCREEN
        # ===========================================================

        if normalized in {"fullscreen", "full screen", "exit fullscreen"}:
            pyautogui.press("f11")
            return self._done_if_ready("fullscreen", normalized)

        # ===========================================================
        # TEXT / CLIPBOARD
        # ===========================================================

        if normalized == "select all":
            pyautogui.hotkey("ctrl", "a")
            return self._done_if_ready("select_all", normalized)

        if normalized in {"copy", "copy copy"}:
            pyautogui.hotkey("ctrl", "c")
            return self._done_if_ready("copy", normalized)

        if normalized in {"paste", "paste paste"}:
            pyautogui.hotkey("ctrl", "v")
            return self._done_if_ready("paste", normalized)

        if normalized == "cut":
            pyautogui.hotkey("ctrl", "x")
            return self._done_if_ready("cut", normalized)

        if normalized == "undo":
            pyautogui.hotkey("ctrl", "z")
            return self._done_if_ready("undo", normalized)

        if normalized == "redo":
            pyautogui.hotkey("ctrl", "y")
            return self._done_if_ready("redo", normalized)

        if normalized in {"delete last word", "delete word"}:
            pyautogui.hotkey("ctrl", "backspace")
            return self._done_if_ready("delete_last_word", normalized)

        if normalized == "select next word":
            pyautogui.hotkey("ctrl", "shift", "right")
            return self._done_if_ready("select_next_word", normalized)

        if normalized == "select previous word":
            pyautogui.hotkey("ctrl", "shift", "left")
            return self._done_if_ready("select_previous_word", normalized)

        if normalized == "start of line":
            pyautogui.press("home")
            return self._done_if_ready("start_of_line", normalized)

        if normalized == "end of line":
            pyautogui.press("end")
            return self._done_if_ready("end_of_line", normalized)

        # ===========================================================
        # KEYBOARD KEYS
        # ===========================================================

        if normalized in {"press enter", "enter"}:
            pyautogui.press("enter")
            return self._done_if_ready("enter", normalized)

        if normalized == "press tab":
            pyautogui.press("tab")
            return self._done_if_ready("tab", normalized)

        if normalized in {"press escape", "press esc", "escape"}:
            pyautogui.press("esc")
            return self._done_if_ready("escape", normalized)

        if normalized in {"backspace", "press backspace"}:
            pyautogui.press("backspace")
            return self._done_if_ready("backspace", normalized)

        # ===========================================================
        # WINDOW CONTROL
        # ===========================================================

        if normalized in {
            "switch window", "next window", "change window",
            # Misheard aliases
            "which will do", "switch will do",
        }:
            pyautogui.hotkey("alt", "tab")
            return self._done_if_ready("switch_window", normalized)

        if normalized in {
            "minimize window", "minimize",
            # Misheard aliases
            "minimize david do", "minimize damage", "sweet window",
        }:
            pyautogui.hotkey("win", "down")
            return self._done_if_ready("minimize", normalized)

        if normalized == "close window":
            pyautogui.hotkey("alt", "f4")
            return self._done_if_ready("close_window", normalized)

        # ===========================================================
        # MEDIA CONTROLS
        # ===========================================================

        if normalized in {"play", "pause", "play pause"}:
            pyautogui.press("playpause")
            return self._done_if_ready("play_pause", normalized)

        if normalized == "mute":
            pyautogui.press("volumemute")
            return self._done_if_ready("mute", normalized)

        if normalized == "unmute":
            pyautogui.press("volumemute")
            return self._done_if_ready("unmute", normalized)

        if normalized in {"volume up", "increase volume", "louder", "sound up"}:
            pyautogui.press("volumeup", presses=3, interval=0.05)
            return self._done_if_ready("volume_up", normalized)

        if normalized in {"volume down", "decrease volume", "quieter", "sound down"}:
            pyautogui.press("volumedown", presses=3, interval=0.05)
            return self._done_if_ready("volume_down", normalized)

        if normalized in {"next video", "next media"}:
            pyautogui.press("nexttrack")
            return self._done_if_ready("next_video", normalized)

        if normalized in {
            "skip forward", "forward ten seconds",
            "forward 10 seconds", "jump ahead"
        }:
            pyautogui.press("right", presses=2)
            return self._done_if_ready("skip_forward", normalized)

        if normalized in {
            "skip back", "back ten seconds", "rewind", "video back"
        }:
            pyautogui.press("left", presses=2)
            return self._done_if_ready("skip_back", normalized)

        # ===========================================================
        # BROWSER SPECIAL PAGES
        # ===========================================================

        if normalized in {"history", "open history"}:
            pyautogui.hotkey("ctrl", "h")
            return self._done_if_ready("history", normalized)

        if normalized in {"downloads", "open downloads"}:
            pyautogui.hotkey("ctrl", "j")
            return self._done_if_ready("downloads", normalized)

        if normalized in {"bookmarks", "open bookmarks"}:
            pyautogui.hotkey("ctrl", "shift", "o")
            return self._done_if_ready("bookmarks", normalized)

        # ===========================================================
        # GOOGLE SEARCH (must come BEFORE open-site matching)
        # ===========================================================

        search_match = re.match(
            r"^(?:search for|search)\s+(.+)$",
            normalized
        )
        if search_match:
            query = search_match.group(1).strip()
            if query:
                if self._is_on_cooldown("search"):
                    return None
                url = "https://www.google.com/search?q=" + quote_plus(query)
                webbrowser.open(url)
                return self._done("search", "search")

        # ===========================================================
        # OPEN WEBSITES
        # Priority: exact aliases first, then site_map, then regex.
        # This prevents misheard "open you to" from reaching the
        # generic fallback and searching Google for "you to".
        # ===========================================================

        # ---- YouTube (many Vosk misheard aliases) ----
        _YOUTUBE_ALIASES = {
            "open youtube",
            # Misheard by Vosk small Indian English model
            "when you do", "when you too", "when you to",
            "you too", "you to", "for you to",
            "well you too", "well you to",
            "you can you do", "when you took you too",
            "open you too", "open you to", "open to you too",
        }
        if normalized in _YOUTUBE_ALIASES:
            if self._is_on_cooldown("open_youtube"):
                return None
            webbrowser.open("https://www.youtube.com")
            return self._done("open_youtube", "open_youtube")

        # ---- Google / Chrome ----
        _CHROME_ALIASES = {
            "open chrome", "open google",
            "chrome", "a full grown",
        }
        if normalized in _CHROME_ALIASES:
            if self._is_on_cooldown("open_google"):
                return None
            webbrowser.open("https://www.google.com")
            return self._done("open_google", "open_google")

        # ---- Other named sites ----
        _SITE_MAP = {
            "open facebook":  "https://www.facebook.com",
            "open twitter":   "https://www.twitter.com",
            "open instagram": "https://www.instagram.com",
            "open github":    "https://www.github.com",
            "open reddit":    "https://www.reddit.com",
            "open linkedin":  "https://www.linkedin.com",
            "open netflix":   "https://www.netflix.com",
            "open amazon":    "https://www.amazon.com",
            "open chat gpt":  "https://chatgpt.com",
        }
        if normalized in _SITE_MAP:
            site_key = normalized.replace(" ", "_")
            if self._is_on_cooldown(site_key):
                return None
            webbrowser.open(_SITE_MAP[normalized])
            return self._done(site_key, site_key)

        # ===========================================================
        # DYNAMIC APPLICATION LAUNCHER (NEW)
        # Must be checked before website commands but after exact site matches
        # ===========================================================
        
        # Check for "open <app>", "launch <app>", "start <app>" patterns
        # But only if it's NOT a known website command
        app_launch_patterns = [
            (r"^open\s+(.+)$", "open"),
            (r"^launch\s+(.+)$", "launch"),
            (r"^start\s+(.+)$", "start"),
        ]
        
        for pattern, command_type in app_launch_patterns:
            app_match = re.match(pattern, normalized)
            if app_match:
                app_name = app_match.group(1).strip()
                
                # Skip if it's a known website (to avoid launching apps when website is intended)
                # Check against known website commands
                known_sites = {
                    "google", "youtube", "facebook", "twitter", "instagram", 
                    "github", "reddit", "linkedin", "netflix", "amazon", "chat gpt",
                    "chrome"  # chrome is a special case - launch app, not website
                }
                
                # Check if this is a known website command (except chrome)
                if app_name in known_sites and app_name != "chrome":
                    # Let the website handler below process this
                    break
                
                # For "open chrome", handle as app launch (not website)
                if app_name == "chrome" or app_name == "google chrome":
                    if self._is_on_cooldown("open_chrome_app"):
                        return None
                    success = self.open_installed_app("Google Chrome")
                    if success:
                        return self._done("open_chrome_app", "open_chrome_app")
                    else:
                        # If Chrome not found, fall back to opening Google
                        webbrowser.open("https://www.google.com")
                        return self._done("open_google_website", "open_google_website")
                
                # For other apps, try to launch
                if self._is_on_cooldown(f"launch_{app_name}"):
                    return None
                
                success = self.open_installed_app(app_name)
                if success:
                    return self._done(f"launch_{app_name}", f"launch_{app_name}")
                else:
                    # If app not found, we silently continue to allow other command types
                    # This prevents "open notepad" from failing if Notepad isn't installed
                    # and allows it to be handled by other handlers if possible
                    pass

        # ---- Generic "open X" — only fires if X looks like a real domain ----
        # AND if it wasn't already handled by the application launcher
        open_site_match = re.match(r"^open\s+(.+)$", normalized)
        if open_site_match:
            site = open_site_match.group(1).strip()
            # Only treat as a URL if the site word contains a dot (e.g. "open bbc.co.uk")
            # This prevents garbage like "open your" from doing anything.
            if "." in site:
                if self._is_on_cooldown(f"open_{site}"):
                    return None
                url = site if site.startswith("http") else f"https://{site}"
                webbrowser.open(url)
                return self._done(f"open_{site}", f"open_{site}")
            # Otherwise, silently ignore — no fallback Google search for "open X"
            # to prevent accidents.

        # ===========================================================
        # DICTATION TOGGLE
        # ===========================================================

        if normalized in {"start typing", "start dictation"}:
            self.dictation_mode = True
            return self._done_if_ready("start_typing", normalized)

        if normalized in {"stop typing", "stop dictation"}:
            self.dictation_mode = False
            return self._done_if_ready("stop_typing", normalized)

        # ===========================================================
        # HEAD TRACKING COMMANDS (signals to main_window)
        # ===========================================================

        if normalized in {"enable head tracking", "turn on head tracking"}:
            return self._done_if_ready("enable_head_tracking", normalized)

        if normalized in {"disable head tracking", "turn off head tracking"}:
            return self._done_if_ready("disable_head_tracking", normalized)

        # ===========================================================
        # MOUTH CLICK COMMANDS
        # ===========================================================

        if normalized == "enable mouth click":
            return self._done_if_ready("enable_mouth_click", normalized)

        if normalized == "disable mouth click":
            return self._done_if_ready("disable_mouth_click", normalized)

        # ===========================================================
        # CALIBRATION
        # ===========================================================

        if normalized in {"start calibration", "calibrate"}:
            return self._done_if_ready("start_calibration", normalized)

        if normalized in {
            "calibrate mouth", "mouth calibrate", "start mouth calibration"
        }:
            return self._done_if_ready("start_mouth_calibration", normalized)

        if normalized == "reset calibration":
            return self._done_if_ready("reset_calibration", normalized)

        # ===========================================================
        # CONFIRMATION SHORTCUTS
        # ===========================================================

        if normalized in {"yes", "yep", "yeah"}:
            pyautogui.press("enter")
            return self._done_if_ready("yes", normalized)

        if normalized in {"no", "nope"}:
            pyautogui.press("esc")
            return self._done_if_ready("no", normalized)

        if normalized == "cancel":
            pyautogui.press("esc")
            return self._done_if_ready("cancel", normalized)

        # ===========================================================
        # SYSTEM / FILE OPERATIONS
        # ===========================================================

        if normalized == "save":
            pyautogui.hotkey("ctrl", "s")
            return self._done_if_ready("save", normalized)

        if normalized == "save as":
            pyautogui.hotkey("ctrl", "shift", "s")
            return self._done_if_ready("save_as", normalized)

        if normalized == "open file":
            pyautogui.hotkey("ctrl", "o")
            return self._done_if_ready("open_file", normalized)

        if normalized == "new file":
            pyautogui.hotkey("ctrl", "n")
            return self._done_if_ready("new_file", normalized)

        if normalized in {
            "open notepad", "open note pad",
            "open not bad",    # Whisper mishear
            "open note pet",   # Whisper mishear
            "open your fat",   # Whisper mishear
            "one not bad",     # Whisper mishear
        }:
            subprocess.Popen(["notepad.exe"])
            return self._done_if_ready("open_notepad", normalized)

        if normalized == "open calculator":
            subprocess.Popen(["calc.exe"])
            return self._done_if_ready("open_calculator", normalized)

        if normalized in {"open start menu", "window"}:
            pyautogui.press("win")
            return self._done_if_ready("open_start_menu", normalized)

        if normalized == "open task manager":
            pyautogui.hotkey("ctrl", "shift", "esc")
            return self._done_if_ready("open_task_manager", normalized)

        if normalized == "lock computer":
            pyautogui.hotkey("win", "l")
            return self._done_if_ready("lock_computer", normalized)

        if normalized == "help":
            return self._done_if_ready("help", normalized)

        # ===========================================================
        # UNKNOWN COMMAND
        # ===========================================================

        print(f"[Voice] Unknown command: '{normalized}'")
        return None

    # =========================================================
    # HELPERS
    # =========================================================

    def _done(self, command_key: str, cooldown_key: str) -> str:
        """Execute a command and record it. Cooldown keyed on command_key."""
        self.last_command = command_key
        self._mark_executed(cooldown_key)
        self._save_history(command_key, cooldown_key)
        print(f"[Voice] Executed: {command_key}")
        return command_key

    def _done_if_ready(self, command_key: str, transcript: str):
        """Execute a command only if not on cooldown. Cooldown keyed on command_key."""
        if self._is_on_cooldown(command_key):
            print(f"[Voice] Cooldown active, skipping: '{command_key}'")
            return None
        return self._done(command_key, command_key)

    def _save_history(self, command: str, transcript: str):
        self.command_history.append({
            "command": command,
            "transcript": transcript
        })
        if len(self.command_history) > self.max_history:
            self.command_history.pop(0)

    def reset_emergency_stop(self):
        """Re-enable desktop control after emergency stop."""
        self.enabled = True
        print("[Voice] Desktop control re-enabled")

    def get_history(self):
        return list(self.command_history)