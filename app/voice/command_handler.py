
# # app/voice/command_handler.py

# import re
# import subprocess
# import webbrowser
# import threading
# import time
# from urllib.parse import quote_plus
# import pyautogui


# class CommandHandler:
#     """
#     Desktop voice command engine.

#     Converts recognized speech into Windows-level
#     mouse, keyboard, browser and application actions.
#     """

#     def __init__(self):
#         self.last_command = ""
#         self.command_history = []
#         self.max_history = 10

#         # Dictation mode
#         self.dictation_mode = False

#         # Emergency stop
#         self.enabled = True

#         # Continuous scrolling
#         self.scrolling = False
#         self.scroll_direction = 0
#         self.scroll_thread = None
#         self.scroll_speed = 5
#         self.scroll_interval = 0.04
#         self.scroll_stop_event = threading.Event()

#     # =========================================================
#     # NORMALIZATION
#     # =========================================================

#     def normalize(self, text: str) -> str:
#         text = text.lower().strip()

#         text = re.sub(
#             r"""[.,!?;:'"()\[\]{}<>]""",
#             "",
#             text
#         )

#         text = re.sub(r"\s+", " ", text)

#         return text.strip()

#     # =========================================================
#     # SCROLLING METHODS
#     # =========================================================

#     def start_scrolling(self, direction: int):
#         """
#         Start continuous scrolling in the specified direction.
#         direction: -1 for down, 1 for up
#         """
#         # If scrolling is already active, stop it first
#         if self.scrolling:
#             self.stop_scrolling()

#         # Set up scrolling parameters
#         self.scrolling = True
#         self.scroll_direction = direction
#         self.scroll_stop_event.clear()

#         # Start scroll thread
#         self.scroll_thread = threading.Thread(
#             target=self._scroll_loop,
#             daemon=True
#         )
#         self.scroll_thread.start()

#         direction_name = "down" if direction < 0 else "up"
#         print(f"[Voice] Started continuous scrolling {direction_name}")

#     def _scroll_loop(self):
#         """
#         Background thread that performs continuous scrolling.
#         """
#         while self.scrolling and not self.scroll_stop_event.is_set():
#             # Perform the scroll
#             pyautogui.scroll(self.scroll_direction * self.scroll_speed)
            
#             # Wait for the next scroll interval
#             time.sleep(self.scroll_interval)

#         print("[Voice] Scroll loop ended")

#     def stop_scrolling(self):
#         """
#         Stop continuous scrolling immediately.
#         """
#         if self.scrolling:
#             self.scrolling = False
#             self.scroll_stop_event.set()
            
#             # Wait for thread to finish (with timeout)
#             if self.scroll_thread and self.scroll_thread.is_alive():
#                 self.scroll_thread.join(timeout=0.5)
            
#             self.scroll_thread = None
#             print("[Voice] Stopped continuous scrolling")

#     def increase_scroll_speed(self):
#         """
#         Increase scrolling speed.
#         """
#         # Max speed limit
#         if self.scroll_speed < 20:
#             self.scroll_speed += 2
#             print(f"[Voice] Scroll speed increased to {self.scroll_speed}")
#         else:
#             print("[Voice] Scroll speed already at maximum")

#     def decrease_scroll_speed(self):
#         """
#         Decrease scrolling speed.
#         """
#         # Min speed limit
#         if self.scroll_speed > 2:
#             self.scroll_speed -= 2
#             print(f"[Voice] Scroll speed decreased to {self.scroll_speed}")
#         else:
#             print("[Voice] Scroll speed already at minimum")

#     # =========================================================
#     # MAIN COMMAND PROCESSOR
#     # =========================================================

#     def execute(self, transcript: str) -> str | None:

#         if not self.enabled:
#             return None

#         normalized = self.normalize(transcript)

#         if not normalized:
#             return None

#         print(f"[Voice] Heard: {normalized}")

#         # -----------------------------------------------------
#         # DICTATION MODE
#         # -----------------------------------------------------

#         if self.dictation_mode:
#             if normalized in [
#                 "stop typing",
#                 "stop dictation",
#                 "exit typing",
#                 "end typing"
#             ]:
#                 self.dictation_mode = False
#                 print("[Voice] Dictation stopped")
#                 return "stop_typing"

#             pyautogui.write(normalized + " ", interval=0.01)

#             self._save_history("dictation", normalized)

#             return "dictation"

#         # -----------------------------------------------------
#         # EMERGENCY STOP
#         # -----------------------------------------------------

#         if normalized in [
#             "emergency stop",
#             "stop automation",
#             "stop control",
#             "disable control"
#         ]:
#             self.enabled = False
#             self.dictation_mode = False
            
#             # Stop scrolling if active
#             if self.scrolling:
#                 self.stop_scrolling()

#             pyautogui.keyUp("ctrl")
#             pyautogui.keyUp("shift")
#             pyautogui.keyUp("alt")

#             print("[Voice] !!! EMERGENCY STOP !!!")

#             return "emergency_stop"

#         # -----------------------------------------------------
#         # VOICE / CONTROL
#         # -----------------------------------------------------

#         if normalized in [
#             "enable voice",
#             "turn on voice"
#         ]:
#             return "voice_enabled"

#         if normalized in [
#             "disable voice",
#             "turn off voice"
#         ]:
#             return "voice_disabled"

#         if normalized in [
#             "enable control",
#             "enable automation"
#         ]:
#             self.enabled = True
#             return "control_enabled"

#         # =====================================================
#         # MOUSE
#         # =====================================================

#         if normalized in [
#             "click",
#             "left click"
#         ]:
#             pyautogui.click()
#             return self._done("click")

#         if normalized in [
#             "double click",
#             "double-click"
#         ]:
#             pyautogui.doubleClick(interval=0.1)
#             return self._done("double_click")

#         if normalized in [
#             "right click",
#             "right-click"
#         ]:
#             pyautogui.rightClick()
#             return self._done("right_click")

#         # =====================================================
#         # SCROLL
#         # =====================================================

#         if normalized in [
#             "scroll down",
#             "down",
#             "page down",
#         ]:
#             # Start continuous scrolling down
#             self.start_scrolling(-1)
#             return self._done("scroll_down_started")

#         if normalized in [
#             "scroll up",
#             "up",
#             "page up"
#         ]:
#             # Start continuous scrolling up
#             self.start_scrolling(1)
#             return self._done("scroll_up_started")

#         if normalized == "scroll faster":
#             self.increase_scroll_speed()
#             return self._done("scroll_faster")

#         if normalized == "scroll slower":
#             self.decrease_scroll_speed()
#             return self._done("scroll_slower")

#         if normalized in [
#             "stop scrolling",
#             "stop scroll",
#             "stop"
#         ]:
#             self.stop_scrolling()
#             return self._done("stop_scrolling")

#         # =====================================================
#         # BROWSER NAVIGATION
#         # =====================================================

#         if normalized in [
#             "go back",
#             "back",
#             "previous page"
#         ]:
#             pyautogui.hotkey("alt", "left")
#             return self._done("go_back")

#         if normalized in [
#             "go forward",
#             "forward",
#             "next page"
#         ]:
#             pyautogui.hotkey("alt", "right")
#             return self._done("go_forward")

#         if normalized in [
#             "refresh page",
#             "refresh",
#             "reload page",
#             "reload"
#         ]:
#             pyautogui.hotkey("ctrl", "r")
#             return self._done("refresh")

#         # =====================================================
#         # TABS
#         # =====================================================

#         if normalized in [
#             "new tab",
#             "open new tab"
#         ]:
#             pyautogui.hotkey("ctrl", "t")
#             return self._done("new_tab")

#         if normalized == "close tab":
#             pyautogui.hotkey("ctrl", "w")
#             return self._done("close_tab")

#         if normalized == "next tab":
#             pyautogui.hotkey("ctrl", "tab")
#             return self._done("next_tab")

#         if normalized in [
#             "previous tab",
#             "prev tab"
#         ]:
#             pyautogui.hotkey("ctrl", "shift", "tab")
#             return self._done("previous_tab")

#         # =====================================================
#         # ZOOM
#         # =====================================================

#         if normalized == "zoom in":
#             pyautogui.hotkey("ctrl", "+")
#             return self._done("zoom_in")

#         if normalized == "zoom out":
#             pyautogui.hotkey("ctrl", "-")
#             return self._done("zoom_out")

#         if normalized == "reset zoom":
#             pyautogui.hotkey("ctrl", "0")
#             return self._done("reset_zoom")

#         # =====================================================
#         # FULL SCREEN
#         # =====================================================

#         if normalized in [
#             "fullscreen",
#             "full screen"
#         ]:
#             pyautogui.press("f11")
#             return self._done("fullscreen")

#         if normalized == "exit fullscreen":
#             pyautogui.press("f11")
#             return self._done("exit_fullscreen")

#         # =====================================================
#         # TEXT / CLIPBOARD
#         # =====================================================

#         if normalized == "select all":
#             pyautogui.hotkey("ctrl", "a")
#             return self._done("select_all")

#         if normalized == "copy":
#             pyautogui.hotkey("ctrl", "c")
#             return self._done("copy")

#         if normalized == "paste":
#             pyautogui.hotkey("ctrl", "v")
#             return self._done("paste")

#         if normalized == "cut":
#             pyautogui.hotkey("ctrl", "x")
#             return self._done("cut")

#         if normalized == "undo":
#             pyautogui.hotkey("ctrl", "z")
#             return self._done("undo")

#         if normalized == "redo":
#             pyautogui.hotkey("ctrl", "y")
#             return self._done("redo")

#         if normalized in [
#             "delete last word",
#             "delete word"
#         ]:
#             pyautogui.hotkey("ctrl", "backspace")
#             return self._done("delete_last_word")

#         # =====================================================
#         # KEYBOARD
#         # =====================================================

#         if normalized in [
#             "press enter",
#             "enter"
#         ]:
#             pyautogui.press("enter")
#             return self._done("enter")

#         if normalized in [
#             "press tab",
#             "tab"
#         ]:
#             pyautogui.press("tab")
#             return self._done("tab")

#         if normalized in [
#             "press escape",
#             "escape",
#             "esc"
#         ]:
#             pyautogui.press("esc")
#             return self._done("escape")

#         if normalized in [
#             "backspace",
#             "press backspace"
#         ]:
#             pyautogui.press("backspace")
#             return self._done("backspace")

#         # =====================================================
#         # WINDOW CONTROL
#         # =====================================================

#         if normalized in [
#             "switch window",
#             "next window",
#             "change window"
#         ]:
#             pyautogui.hotkey("alt", "tab")
#             return self._done("switch_window")

#         if normalized in [
#             "minimize window",
#             "minimize"
#         ]:
#             pyautogui.hotkey("alt", "space")
#             pyautogui.press("n")
#             return self._done("minimize")

#         if normalized in [
#             "close window"
#         ]:
#             pyautogui.hotkey("alt", "f4")
#             return self._done("close_window")

#         # =====================================================
#         # MEDIA
#         # =====================================================

#         if normalized == "play":
#             pyautogui.press("playpause")
#             return self._done("play")

#         if normalized == "pause":
#             pyautogui.press("playpause")
#             return self._done("pause")

#         if normalized == "mute":
#             pyautogui.press("volumemute")
#             return self._done("mute")

#         if normalized == "unmute":
#             pyautogui.press("volumemute")
#             return self._done("unmute")

#         if normalized in [
#             "volume up",
#             "increase volume",
#             "louder",
#             "sound up"
#         ]:
#             pyautogui.press("volumeup", presses=3, interval=0.05)
#             return self._done("volume_up")

#         if normalized in [
#             "volume down",
#             "decrease volume",
#             "quieter",
#             "sound down"
#         ]:
#             pyautogui.press("volumedown", presses=3, interval=0.05)
#             return self._done("volume_down")

#         if normalized in [
#             "next video",
#             "next media"
#         ]:
#             pyautogui.hotkey("shift", "n")
#             return self._done("next_video")

#         if normalized in [
#             "skip forward",
#             "forward ten seconds",
#             "forward 10 seconds",
#             "jump ahead"
#         ]:
#             pyautogui.press("right", presses=2)
#             return self._done("skip_forward")

#         if normalized in [
#             "skip back",
#             "back ten seconds",
#             "rewind",
#             "video back"
#         ]:
#             pyautogui.press("left", presses=2)
#             return self._done("skip_back")

#         # =====================================================
#         # BROWSER SPECIAL PAGES
#         # =====================================================

#         if normalized in [
#             "open history",
#             "history"
#         ]:
#             pyautogui.hotkey("ctrl", "h")
#             return self._done("history")

#         if normalized in [
#             "open downloads",
#             "downloads"
#         ]:
#             pyautogui.hotkey("ctrl", "j")
#             return self._done("downloads")

#         if normalized in [
#             "open bookmarks",
#             "bookmarks"
#         ]:
#             pyautogui.hotkey("ctrl", "shift", "o")
#             return self._done("bookmarks")

#         # =====================================================
#         # SEARCH
#         # =====================================================

#         search_match = re.match(
#             r"^(?:search for|search)\s+(.+)$",
#             normalized
#         )

#         if search_match:
#             query = search_match.group(1).strip()

#             if query:
#                 url = (
#                     "https://www.google.com/search?q="
#                     + quote_plus(query)
#                 )

#                 webbrowser.open(url)

#                 return self._done(
#                     f"search:{query}"
#                 )

#         # =====================================================
#         # START TYPING / DICTATION
#         # =====================================================

#         if normalized in [
#             "start typing",
#             "start dictation"
#         ]:
#             self.dictation_mode = True
#             return self._done("start_typing")

#         if normalized in [
#             "stop typing",
#             "stop dictation"
#         ]:
#             self.dictation_mode = False
#             return self._done("stop_typing")

#         # =====================================================
#         # HEAD TRACKING
#         # =====================================================

#         if normalized in [
#             "enable head tracking",
#             "turn on head tracking"
#         ]:
#             return self._done("enable_head_tracking")

#         if normalized in [
#             "disable head tracking",
#             "turn off head tracking"
#         ]:
#             return self._done("disable_head_tracking")

#         # =====================================================
#         # MOUTH CLICK
#         # =====================================================

#         if normalized == "enable mouth click":
#             return self._done("enable_mouth_click")

#         if normalized == "disable mouth click":
#             return self._done("disable_mouth_click")

#         # =====================================================
#         # CALIBRATION
#         # =====================================================

#         if normalized in [
#             "start calibration",
#             "calibrate"
#         ]:
#             return self._done("start_calibration")

#         if normalized in [
#             "calibrate mouth",
#             "mouth calibrate",
#             "start mouth calibration"
#         ]:
#             return self._done("start_mouth_calibration")

#         if normalized == "reset calibration":
#             return self._done("reset_calibration")

#         # =====================================================
#         # HELP
#         # =====================================================

#         if normalized == "help":
#             return self._done("help")

#         # =====================================================
#         # YES / NO / CANCEL
#         # =====================================================

#         if normalized in ["yes", "yep", "yeah"]:
#             pyautogui.press("enter")
#             return self._done("yes")

#         if normalized in ["no", "nope"]:
#             pyautogui.press("esc")
#             return self._done("no")

#         if normalized == "cancel":
#             pyautogui.press("esc")
#             return self._done("cancel")

#         # =====================================================
#         # UNKNOWN
#         # =====================================================

#         print(f"[Voice] Unknown command: {normalized}")

#         return None

#     # =========================================================
#     # HELPERS
#     # =========================================================

#     def _done(self, command: str) -> str:
#         self.last_command = command
#         self._save_history(command, command)

#         print(f"[Voice] ✓ Executed: {command}")

#         return command

#     def _save_history(self, command: str, transcript: str):

#         self.command_history.append({
#             "command": command,
#             "transcript": transcript
#         })

#         if len(self.command_history) > self.max_history:
#             self.command_history.pop(0)

#     def reset_emergency_stop(self):
#         """
#         Re-enable desktop control.
#         """
#         self.enabled = True
#         print("[Voice] Desktop control enabled")

#     def get_history(self):
#         return list(self.command_history)


# app/voice/command_handler.py

import re
import subprocess
import webbrowser
import threading
import time
from urllib.parse import quote_plus
import pyautogui


class CommandHandler:
    """
    Desktop voice command engine.

    Converts recognized speech into Windows-level
    mouse, keyboard, browser and application actions.
    """

    def __init__(self):
        self.last_command = ""
        self.command_history = []
        self.max_history = 10

        # Dictation mode
        self.dictation_mode = False

        # Emergency stop
        self.enabled = True

        # Continuous scrolling
        self.scrolling = False
        self.scroll_direction = 0
        self.scroll_thread = None
        self.scroll_speed = 5
        self.scroll_interval = 0.04
        self.scroll_stop_event = threading.Event()

    # =========================================================
    # NORMALIZATION
    # =========================================================

    def normalize(self, text: str) -> str:
        text = text.lower().strip()

        text = re.sub(
            r"""[.,!?;:'"()\[\]{}<>]""",
            "",
            text
        )

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # =========================================================
    # SCROLLING METHODS
    # =========================================================

    def start_scrolling(self, direction: int):
        """
        Start continuous scrolling in the specified direction.
        direction: -1 for down, 1 for up
        """
        # If scrolling is already active, stop it first
        if self.scrolling:
            self.stop_scrolling()

        # Set up scrolling parameters
        self.scrolling = True
        self.scroll_direction = direction
        self.scroll_stop_event.clear()

        # Start scroll thread
        self.scroll_thread = threading.Thread(
            target=self._scroll_loop,
            daemon=True
        )
        self.scroll_thread.start()

        direction_name = "down" if direction < 0 else "up"
        print(f"[Voice] Started continuous scrolling {direction_name}")

    def _scroll_loop(self):
        """
        Background thread that performs continuous scrolling.
        """
        while self.scrolling and not self.scroll_stop_event.is_set():
            # Perform the scroll
            pyautogui.scroll(self.scroll_direction * self.scroll_speed)
            
            # Wait for the next scroll interval
            time.sleep(self.scroll_interval)

        print("[Voice] Scroll loop ended")

    def stop_scrolling(self):
        """
        Stop continuous scrolling immediately.
        """
        if self.scrolling:
            self.scrolling = False
            self.scroll_stop_event.set()
            
            # Wait for thread to finish (with timeout)
            if self.scroll_thread and self.scroll_thread.is_alive():
                self.scroll_thread.join(timeout=0.5)
            
            self.scroll_thread = None
            print("[Voice] Stopped continuous scrolling")

    def increase_scroll_speed(self):
        """
        Increase scrolling speed.
        """
        # Max speed limit
        if self.scroll_speed < 20:
            self.scroll_speed += 2
            print(f"[Voice] Scroll speed increased to {self.scroll_speed}")
        else:
            print("[Voice] Scroll speed already at maximum")

    def decrease_scroll_speed(self):
        """
        Decrease scrolling speed.
        """
        # Min speed limit
        if self.scroll_speed > 2:
            self.scroll_speed -= 2
            print(f"[Voice] Scroll speed decreased to {self.scroll_speed}")
        else:
            print("[Voice] Scroll speed already at minimum")

    # =========================================================
    # MAIN COMMAND PROCESSOR
    # =========================================================

    def execute(self, transcript: str) -> str | None:

        if not self.enabled:
            return None

        normalized = self.normalize(transcript)

        if not normalized:
            return None

        # --- FUZZY MATCHING LAYER ---
        if not (normalized.startswith("search") or normalized.startswith("search for")):
            import difflib
            expected_commands = [
                "stop typing", "stop dictation", "exit typing", "end typing",
                "emergency stop", "stop automation", "stop control", "disable control",
                "enable voice", "turn on voice", "disable voice", "turn off voice",
                "enable control", "enable automation",
                "click", "left click", "double click", "double-click", "right click", "right-click",
                "scroll down", "down", "page down", "scroll up", "up", "page up",
                "scroll faster", "scroll slower", "stop scrolling", "stop scroll", "stop",
                "go back", "back", "previous page", "go forward", "forward", "next page",
                "refresh page", "refresh", "reload page", "reload",
                "new tab", "open new tab", "close tab", "next tab", "previous tab", "prev tab",
                "zoom in", "zoom out", "reset zoom", "fullscreen", "full screen", "exit fullscreen",
                "select all", "copy", "paste", "cut", "undo", "redo", "delete last word", "delete word",
                "press enter", "enter", "press tab", "tab", "press escape", "escape", "esc", "backspace", "press backspace",
                "switch window", "next window", "change window", "minimize window", "minimize", "close window",
                "play", "pause", "mute", "unmute", "volume up", "increase volume", "louder", "sound up",
                "volume down", "decrease volume", "quieter", "sound down", "next video", "next media",
                "skip forward", "forward ten seconds", "forward 10 seconds", "jump ahead",
                "skip back", "back ten seconds", "rewind", "video back",
                "open history", "history", "open downloads", "downloads", "open bookmarks", "bookmarks",
                "start typing", "start dictation",
                "enable head tracking", "turn on head tracking", "disable head tracking", "turn off head tracking",
                "enable mouth click", "disable mouth click",
                "start calibration", "calibrate", "calibrate mouth", "mouth calibrate", "start mouth calibration", "reset calibration",
                "help", "yes", "yep", "yeah", "no", "nope", "cancel"
            ]
            matches = difflib.get_close_matches(normalized, expected_commands, n=1, cutoff=0.7)
            if matches:
                normalized = matches[0]
        # ----------------------------

        print(f"[Voice] Heard: {normalized}")

        # -----------------------------------------------------
        # DICTATION MODE
        # -----------------------------------------------------

        if self.dictation_mode:
            if normalized in [
                "stop typing",
                "stop dictation",
                "exit typing",
                "end typing"
            ]:
                self.dictation_mode = False
                print("[Voice] Dictation stopped")
                return "stop_typing"

            pyautogui.write(normalized + " ", interval=0.01)

            self._save_history("dictation", normalized)

            return "dictation"

        # -----------------------------------------------------
        # EMERGENCY STOP
        # -----------------------------------------------------

        if normalized in [
            "emergency stop",
            "stop automation",
            "stop control",
            "disable control"
        ]:
            self.enabled = False
            self.dictation_mode = False
            
            # Stop scrolling if active
            if self.scrolling:
                self.stop_scrolling()

            pyautogui.keyUp("ctrl")
            pyautogui.keyUp("shift")
            pyautogui.keyUp("alt")

            print("[Voice] !!! EMERGENCY STOP !!!")

            return "emergency_stop"

        # -----------------------------------------------------
        # VOICE / CONTROL
        # -----------------------------------------------------

        if normalized in [
            "enable voice",
            "turn on voice"
        ]:
            return "voice_enabled"

        if normalized in [
            "disable voice",
            "turn off voice"
        ]:
            return "voice_disabled"

        if normalized in [
            "enable control",
            "enable automation"
        ]:
            self.enabled = True
            return "control_enabled"

        # =====================================================
        # MOUSE
        # =====================================================

        if normalized in [
            "click",
            "left click"
        ]:
            pyautogui.click()
            return self._done("click")

        if normalized in [
            "double click",
            "double-click"
        ]:
            pyautogui.doubleClick(interval=0.1)
            return self._done("double_click")

        if normalized in [
            "right click",
            "right-click"
        ]:
            pyautogui.rightClick()
            return self._done("right_click")

        # =====================================================
        # SCROLL
        # =====================================================

        if normalized in [
            "scroll down",
            "down",
            "page down",
        ]:
            # Start continuous scrolling down
            self.start_scrolling(-1)
            return self._done("scroll_down_started")

        if normalized in [
            "scroll up",
            "up",
            "page up"
        ]:
            # Start continuous scrolling up
            self.start_scrolling(1)
            return self._done("scroll_up_started")

        if normalized == "scroll faster":
            self.increase_scroll_speed()
            return self._done("scroll_faster")

        if normalized == "scroll slower":
            self.decrease_scroll_speed()
            return self._done("scroll_slower")

        if normalized in [
            "stop scrolling",
            "stop scroll",
            "stop"
        ]:
            self.stop_scrolling()
            return self._done("stop_scrolling")

        # =====================================================
        # BROWSER NAVIGATION
        # =====================================================

        if normalized in [
            "go back",
            "back",
            "previous page"
        ]:
            pyautogui.hotkey("alt", "left")
            return self._done("go_back")

        if normalized in [
            "go forward",
            "forward",
            "next page"
        ]:
            pyautogui.hotkey("alt", "right")
            return self._done("go_forward")

        if normalized in [
            "refresh page",
            "refresh",
            "reload page",
            "reload"
        ]:
            pyautogui.hotkey("ctrl", "r")
            return self._done("refresh")

        # =====================================================
        # TABS
        # =====================================================

        if normalized in [
            "new tab",
            "open new tab"
        ]:
            pyautogui.hotkey("ctrl", "t")
            return self._done("new_tab")

        if normalized == "close tab":
            pyautogui.hotkey("ctrl", "w")
            return self._done("close_tab")

        if normalized == "next tab":
            pyautogui.hotkey("ctrl", "tab")
            return self._done("next_tab")

        if normalized in [
            "previous tab",
            "prev tab"
        ]:
            pyautogui.hotkey("ctrl", "shift", "tab")
            return self._done("previous_tab")

        # =====================================================
        # ZOOM
        # =====================================================

        if normalized == "zoom in":
            pyautogui.hotkey("ctrl", "+")
            return self._done("zoom_in")

        if normalized == "zoom out":
            pyautogui.hotkey("ctrl", "-")
            return self._done("zoom_out")

        if normalized == "reset zoom":
            pyautogui.hotkey("ctrl", "0")
            return self._done("reset_zoom")

        # =====================================================
        # FULL SCREEN
        # =====================================================

        if normalized in [
            "fullscreen",
            "full screen"
        ]:
            pyautogui.press("f11")
            return self._done("fullscreen")

        if normalized == "exit fullscreen":
            pyautogui.press("f11")
            return self._done("exit_fullscreen")

        # =====================================================
        # TEXT / CLIPBOARD
        # =====================================================

        if normalized == "select all":
            pyautogui.hotkey("ctrl", "a")
            return self._done("select_all")

        if normalized == "copy":
            pyautogui.hotkey("ctrl", "c")
            return self._done("copy")

        if normalized == "paste":
            pyautogui.hotkey("ctrl", "v")
            return self._done("paste")

        if normalized == "cut":
            pyautogui.hotkey("ctrl", "x")
            return self._done("cut")

        if normalized == "undo":
            pyautogui.hotkey("ctrl", "z")
            return self._done("undo")

        if normalized == "redo":
            pyautogui.hotkey("ctrl", "y")
            return self._done("redo")

        if normalized in [
            "delete last word",
            "delete word"
        ]:
            pyautogui.hotkey("ctrl", "backspace")
            return self._done("delete_last_word")

        # =====================================================
        # KEYBOARD
        # =====================================================

        if normalized in [
            "press enter",
            "enter"
        ]:
            pyautogui.press("enter")
            return self._done("enter")

        if normalized in [
            "press tab",
            "tab"
        ]:
            pyautogui.press("tab")
            return self._done("tab")

        if normalized in [
            "press escape",
            "escape",
            "esc"
        ]:
            pyautogui.press("esc")
            return self._done("escape")

        if normalized in [
            "backspace",
            "press backspace"
        ]:
            pyautogui.press("backspace")
            return self._done("backspace")

        # =====================================================
        # WINDOW CONTROL
        # =====================================================

        if normalized in [
            "switch window",
            "next window",
            "change window"
        ]:
            pyautogui.hotkey("alt", "tab")
            return self._done("switch_window")

        if normalized in [
            "minimize window",
            "minimize"
        ]:
            pyautogui.hotkey("alt", "space")
            pyautogui.press("n")
            return self._done("minimize")

        if normalized in [
            "close window"
        ]:
            pyautogui.hotkey("alt", "f4")
            return self._done("close_window")

        # =====================================================
        # MEDIA
        # =====================================================

        if normalized == "play":
            pyautogui.press("playpause")
            return self._done("play")

        if normalized == "pause":
            pyautogui.press("playpause")
            return self._done("pause")

        if normalized == "mute":
            pyautogui.press("volumemute")
            return self._done("mute")

        if normalized == "unmute":
            pyautogui.press("volumemute")
            return self._done("unmute")

        if normalized in [
            "volume up",
            "increase volume",
            "louder",
            "sound up"
        ]:
            pyautogui.press("volumeup", presses=3, interval=0.05)
            return self._done("volume_up")

        if normalized in [
            "volume down",
            "decrease volume",
            "quieter",
            "sound down"
        ]:
            pyautogui.press("volumedown", presses=3, interval=0.05)
            return self._done("volume_down")

        if normalized in [
            "next video",
            "next media"
        ]:
            pyautogui.hotkey("shift", "n")
            return self._done("next_video")

        if normalized in [
            "skip forward",
            "forward ten seconds",
            "forward 10 seconds",
            "jump ahead"
        ]:
            pyautogui.press("right", presses=2)
            return self._done("skip_forward")

        if normalized in [
            "skip back",
            "back ten seconds",
            "rewind",
            "video back"
        ]:
            pyautogui.press("left", presses=2)
            return self._done("skip_back")

        # =====================================================
        # BROWSER SPECIAL PAGES
        # =====================================================

        if normalized in [
            "open history",
            "history"
        ]:
            pyautogui.hotkey("ctrl", "h")
            return self._done("history")

        if normalized in [
            "open downloads",
            "downloads"
        ]:
            pyautogui.hotkey("ctrl", "j")
            return self._done("downloads")

        if normalized in [
            "open bookmarks",
            "bookmarks"
        ]:
            pyautogui.hotkey("ctrl", "shift", "o")
            return self._done("bookmarks")

        # =====================================================
        # SEARCH
        # =====================================================

        search_match = re.match(
            r"^(?:search for|search)\s+(.+)$",
            normalized
        )

        if search_match:
            query = search_match.group(1).strip()

            if query:
                url = (
                    "https://www.google.com/search?q="
                    + quote_plus(query)
                )

                webbrowser.open(url)

                return self._done(
                    f"search:{query}"
                )

        # =====================================================
        # START TYPING / DICTATION
        # =====================================================

        if normalized in [
            "start typing",
            "start dictation"
        ]:
            self.dictation_mode = True
            return self._done("start_typing")

        if normalized in [
            "stop typing",
            "stop dictation"
        ]:
            self.dictation_mode = False
            return self._done("stop_typing")

        # =====================================================
        # HEAD TRACKING
        # =====================================================

        if normalized in [
            "enable head tracking",
            "turn on head tracking"
        ]:
            return self._done("enable_head_tracking")

        if normalized in [
            "disable head tracking",
            "turn off head tracking"
        ]:
            return self._done("disable_head_tracking")

        # =====================================================
        # MOUTH CLICK
        # =====================================================

        if normalized == "enable mouth click":
            return self._done("enable_mouth_click")

        if normalized == "disable mouth click":
            return self._done("disable_mouth_click")

        # =====================================================
        # CALIBRATION
        # =====================================================

        if normalized in [
            "start calibration",
            "calibrate"
        ]:
            return self._done("start_calibration")

        if normalized in [
            "calibrate mouth",
            "mouth calibrate",
            "start mouth calibration"
        ]:
            return self._done("start_mouth_calibration")

        if normalized == "reset calibration":
            return self._done("reset_calibration")

        # =====================================================
        # HELP
        # =====================================================

        if normalized == "help":
            return self._done("help")

        # =====================================================
        # YES / NO / CANCEL
        # =====================================================

        if normalized in ["yes", "yep", "yeah"]:
            pyautogui.press("enter")
            return self._done("yes")

        if normalized in ["no", "nope"]:
            pyautogui.press("esc")
            return self._done("no")

        if normalized == "cancel":
            pyautogui.press("esc")
            return self._done("cancel")

        # =====================================================
        # UNKNOWN
        # =====================================================

        print(f"[Voice] Unknown command: {normalized}")

        return None

    # =========================================================
    # HELPERS
    # =========================================================

    def _done(self, command: str) -> str:
        self.last_command = command
        self._save_history(command, command)

        print(f"[Voice] ✓ Executed: {command}")

        return command

    def _save_history(self, command: str, transcript: str):

        self.command_history.append({
            "command": command,
            "transcript": transcript
        })

        if len(self.command_history) > self.max_history:
            self.command_history.pop(0)

    def reset_emergency_stop(self):
        """
        Re-enable desktop control.
        """
        self.enabled = True
        print("[Voice] Desktop control enabled")

    def get_history(self):
        return list(self.command_history)