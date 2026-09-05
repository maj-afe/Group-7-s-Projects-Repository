# app/system/window_manager.py

import re
import win32gui
import win32con
import win32process
import psutil
from typing import Optional, List, Tuple

class WindowManager:
    """
    Manages Windows windows using Win32 APIs.
    Provides dynamic window manipulation without hardcoded paths.
    """
    
    def __init__(self):
        self._last_error = ""
    
    def get_all_windows(self) -> List[Tuple[int, str, str]]:
        """
        Get all visible windows.
        Returns: List of (hwnd, title, process_name)
        """
        windows = []
        
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # Only include windows with titles
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
    
    def find_window(self, app_name: str) -> Optional[Tuple[int, str, str]]:
        """
        Find a window by application name or title.
        Case-insensitive, supports partial matching.
        
        Returns: (hwnd, title, process_name) or None
        """
        if not app_name or len(app_name.strip()) < 2:
            return None
        
        app_name = app_name.lower().strip()
        windows = self.get_all_windows()
        
        # Step 1: Try exact match on process name
        for hwnd, title, process_name in windows:
            if process_name.lower() == app_name:
                return (hwnd, title, process_name)
        
        # Step 2: Try partial match on process name
        for hwnd, title, process_name in windows:
            if app_name in process_name.lower():
                return (hwnd, title, process_name)
        
        # Step 3: Try match on window title
        for hwnd, title, process_name in windows:
            if app_name in title.lower():
                return (hwnd, title, process_name)
        
        # Step 4: Try fuzzy word matching on window title
        # Split the app name and check if all significant words appear in the title
        app_words = set(app_name.split())
        for hwnd, title, process_name in windows:
            title_words = set(title.lower().split())
            # Check if all words from app name appear in title
            if app_words.issubset(title_words):
                return (hwnd, title, process_name)
        
        return None
    
    def switch_to_window(self, app_name: str) -> bool:
        """
        Bring a window to the foreground.
        Returns True if successful, False otherwise.
        """
        result = self.find_window(app_name)
        if result is None:
            self._last_error = f"Window '{app_name}' is not currently open."
            return False
        
        hwnd, title, process_name = result
        
        try:
            # Restore if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # Bring to foreground
            win32gui.SetForegroundWindow(hwnd)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to switch to window: {e}"
            return False
    
    def minimize_window(self, app_name: str) -> bool:
        """
        Minimize a specific window.
        Returns True if successful, False otherwise.
        """
        result = self.find_window(app_name)
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
        """
        Maximize a specific window.
        Returns True if successful, False otherwise.
        """
        result = self.find_window(app_name)
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
        """
        Move the currently active window in a direction.
        direction: 'left', 'right', 'up', 'down'
        pixels: number of pixels to move
        Returns True if successful, False otherwise.
        """
        try:
            # Get active window
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                self._last_error = "No active window found."
                return False
            
            # Get current position
            rect = win32gui.GetWindowRect(hwnd)
            x, y, right, bottom = rect
            width = right - x
            height = bottom - y
            
            # Calculate new position
            if direction == "left":
                new_x = x - pixels
                new_y = y
            elif direction == "right":
                new_x = x + pixels
                new_y = y
            elif direction == "up":
                new_x = x
                new_y = y - pixels
            elif direction == "down":
                new_x = x
                new_y = y + pixels
            else:
                self._last_error = f"Invalid direction: {direction}"
                return False
            
            # Move window
            win32gui.SetWindowPos(
                hwnd,
                None,
                new_x,
                new_y,
                width,
                height,
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE
            )
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to move window: {e}"
            return False
    
    def close_active_window(self) -> bool:
        """
        Close the currently active window.
        Returns True if successful, False otherwise.
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                self._last_error = "No active window found."
                return False
            
            # Send close message
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = f"Failed to close window: {e}"
            return False
    
    def get_last_error(self) -> str:
        """Get the last error message."""
        return self._last_error