# app/system/system_controller.py

import subprocess
import ctypes
import os
import time

class SystemController:
    """
    Handles Windows system-level operations including power control.
    All methods include error handling and return success status.
    """
    
    def __init__(self):
        self._last_error = ""
    
    def lock_computer(self) -> bool:
        """Lock the Windows workstation immediately."""
        try:
            ctypes.windll.user32.LockWorkStation()
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to lock computer: {e}"
            return False
    
    def sleep_computer(self) -> bool:
        """Put the computer to sleep."""
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)
            ctypes.windll.powrprof.SetSuspendState(0, 0, 0)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to sleep computer: {e}"
            return False
    
    def restart_computer(self) -> bool:
        """Restart the computer using Windows shutdown command."""
        try:
            subprocess.run(
                ["shutdown", "/r", "/t", "0", "/f"],
                capture_output=True,
                timeout=5
            )
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to restart computer: {e}"
            return False
    
    def shutdown_computer(self) -> bool:
        """Shut down the computer using Windows shutdown command."""
        try:
            subprocess.run(
                ["shutdown", "/s", "/t", "0", "/f"],
                capture_output=True,
                timeout=5
            )
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to shutdown computer: {e}"
            return False
    
    def get_last_error(self) -> str:
        """Get the last error message."""
        return self._last_error