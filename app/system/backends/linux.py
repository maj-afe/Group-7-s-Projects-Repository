import subprocess
from typing import List
from app.system.interfaces import BaseWindowManager, BaseSystemController

class LinuxWindowManager(BaseWindowManager):
    """
    Manages Linux windows. 
    Requires specific compositors (e.g., hyprctl, swaymsg, or xdotool).
    Gracefully degrades if tools are missing.
    """
    def __init__(self):
        self._last_error = ""

    def get_all_windows(self) -> List[str]:
        # Placeholder for Wayland window introspection
        return []

    def find_window(self, title_keyword: str) -> bool:
        return False

    def switch_to_window(self, title_keyword: str) -> bool:
        self._last_error = "Window switching not universally supported on Wayland."
        return False

    def minimize_window(self, title_keyword: str) -> bool:
        return False

    def maximize_window(self, title_keyword: str) -> bool:
        return False

    def move_active_window(self, direction: str) -> bool:
        return False

    def close_active_window(self) -> bool:
        return False

    def get_last_error(self) -> str:
        return self._last_error

class LinuxSystemController(BaseSystemController):
    """
    Handles Linux system-level operations including power control using systemd/logind.
    """
    def __init__(self):
        self._last_error = ""

    def lock_computer(self) -> bool:
        try:
            subprocess.run(["loginctl", "lock-session"], capture_output=True, timeout=5)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to lock computer: {e}"
            return False

    def sleep_computer(self) -> bool:
        try:
            subprocess.run(["systemctl", "suspend"], capture_output=True, timeout=5)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to sleep computer: {e}"
            return False

    def restart_computer(self) -> bool:
        try:
            subprocess.run(["systemctl", "reboot"], capture_output=True, timeout=5)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to restart computer: {e}"
            return False

    def shutdown_computer(self) -> bool:
        try:
            subprocess.run(["systemctl", "poweroff"], capture_output=True, timeout=5)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to shutdown computer: {e}"
            return False

    def get_last_error(self) -> str:
        return self._last_error
