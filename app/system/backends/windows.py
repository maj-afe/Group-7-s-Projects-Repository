import re
from typing import Optional, List, Tuple
from app.system.interfaces import BaseWindowManager, BaseSystemController

try:
    import win32gui
    import win32con
    import win32process
    import ctypes
except ImportError:
    pass  # We don't crash here; Factory pattern handles this

import psutil
import subprocess

class WindowsWindowManager(BaseWindowManager):
    """
    Manages Windows windows using Win32 APIs.
    """
    
    def __init__(self):
        self._last_error = ""
    
    def get_all_windows(self) -> List[Tuple[int, str, str]]:
        windows = []
        
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        try:
                            process = psutil.Process(pid)
                            process_name = process.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            process_name = "Unknown"
                        hwnds.append((hwnd, title, process_name))
                    except Exception:
                        pass
            return True
        
        win32gui.EnumWindows(callback, windows)
        return windows
    
    def find_window(self, app_name: str) -> bool:
        # We need this to match the old signature conceptually, 
        # or we update to just return bool if found
        res = self._find_window_internal(app_name)
        return res is not None

    def _find_window_internal(self, app_name: str) -> Optional[Tuple[int, str, str]]:
        if not app_name or len(app_name.strip()) < 2:
            return None
        
        app_name = app_name.lower().strip()
        windows = self.get_all_windows()
        
        for hwnd, title, process_name in windows:
            if process_name.lower() == app_name:
                return (hwnd, title, process_name)
        
        for hwnd, title, process_name in windows:
            if app_name in process_name.lower():
                return (hwnd, title, process_name)
        
        for hwnd, title, process_name in windows:
            if app_name in title.lower():
                return (hwnd, title, process_name)
        
        app_words = set(app_name.split())
        for hwnd, title, process_name in windows:
            title_words = set(title.lower().split())
            if app_words.issubset(title_words):
                return (hwnd, title, process_name)
        
        return None
    
    def switch_to_window(self, app_name: str) -> bool:
        result = self._find_window_internal(app_name)
        if result is None:
            self._last_error = f"Window '{app_name}' is not currently open."
            return False
        
        hwnd, title, process_name = result
        
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            win32gui.SetForegroundWindow(hwnd)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to switch to window: {e}"
            return False
    
    def minimize_window(self, app_name: str) -> bool:
        result = self._find_window_internal(app_name)
        if result is None:
            self._last_error = f"Window '{app_name}' is not currently open."
            return False
        
        hwnd, title, process_name = result
        
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to minimize window: {e}"
            return False
    
    def maximize_window(self, app_name: str) -> bool:
        result = self._find_window_internal(app_name)
        if result is None:
            self._last_error = f"Window '{app_name}' is not currently open."
            return False
        
        hwnd, title, process_name = result
        
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to maximize window: {e}"
            return False
    
    def move_active_window(self, direction: str, pixels: int = 100) -> bool:
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                self._last_error = "No active window found."
                return False
            
            rect = win32gui.GetWindowRect(hwnd)
            x, y, right, bottom = rect
            width = right - x
            height = bottom - y
            
            if direction == "left":
                new_x, new_y = x - pixels, y
            elif direction == "right":
                new_x, new_y = x + pixels, y
            elif direction == "up":
                new_x, new_y = x, y - pixels
            elif direction == "down":
                new_x, new_y = x, y + pixels
            else:
                self._last_error = f"Invalid direction: {direction}"
                return False
            
            win32gui.SetWindowPos(
                hwnd, None, new_x, new_y, width, height,
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE
            )
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to move window: {e}"
            return False
    
    def close_active_window(self) -> bool:
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                self._last_error = "No active window found."
                return False
            
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to close window: {e}"
            return False
    
    def get_last_error(self) -> str:
        return self._last_error


class WindowsSystemController(BaseSystemController):
    def __init__(self):
        self._last_error = ""
    
    def lock_computer(self) -> bool:
        try:
            ctypes.windll.user32.LockWorkStation()
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to lock computer: {e}"
            return False
    
    def sleep_computer(self) -> bool:
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)
            ctypes.windll.powrprof.SetSuspendState(0, 0, 0)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to sleep computer: {e}"
            return False
    
    def restart_computer(self) -> bool:
        try:
            subprocess.run(["shutdown", "/r", "/t", "0", "/f"], capture_output=True, timeout=5)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to restart computer: {e}"
            return False
    
    def shutdown_computer(self) -> bool:
        try:
            subprocess.run(["shutdown", "/s", "/t", "0", "/f"], capture_output=True, timeout=5)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to shutdown computer: {e}"
            return False
    
    def get_last_error(self) -> str:
        return self._last_error
