# app/system/startup_manager.py
"""
Windows Startup Manager
-----------------------
Registers / deregisters BUG to auto-launch when the current Windows user
logs in, using the HKCU Run registry key.

The entry runs:
    pythonw.exe  <absolute-path-to-app/main.py>

pythonw.exe is used so no console window appears on startup.

Public API
----------
    StartupManager.is_enabled()  -> bool
    StartupManager.enable()      -> bool   (True on success)
    StartupManager.disable()     -> bool   (True on success)
"""

import sys
import os
from pathlib import Path

# Registry key where per-user startup entries live
_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "FGA_Accessibility"


def _get_launch_command() -> str:
    """
    Build the command string stored in the registry.

    Uses pythonw.exe (same venv, no console window) to launch app/main.py.
    Falls back to python.exe if pythonw.exe is not found (edge case).
    """
    # Resolve paths relative to THIS file's location:
    # startup_manager.py  ->  app/system/  ->  app/  ->  repo root
    repo_root = Path(__file__).resolve().parent.parent.parent
    main_py = repo_root / "app" / "main.py"

    # Prefer pythonw.exe (silent, no console) from the same interpreter dir
    python_dir = Path(sys.executable).parent
    pythonw = python_dir / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)          # fallback: python.exe

    # Quote paths so spaces don't break the command
    return f'"{pythonw}" "{main_py}"'


def is_enabled() -> bool:
    """Return True if BUG is currently registered for Windows startup."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as key:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> bool:
    """
    Register BUG to launch on Windows login.
    Returns True on success, False on failure.
    """
    try:
        import winreg
        cmd = _get_launch_command()
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REG_PATH,
            access=winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, cmd)
        print(f"[Startup] Registered: {cmd}")
        return True
    except Exception as e:
        print(f"[Startup] Failed to enable: {e}")
        return False


def disable() -> bool:
    """
    Remove BUG from Windows startup.
    Returns True on success (or if it was never registered), False on error.
    """
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REG_PATH,
            access=winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, _APP_NAME)
        print("[Startup] Deregistered from Windows startup.")
        return True
    except FileNotFoundError:
        # Value didn't exist — that's fine, goal achieved
        return True
    except Exception as e:
        print(f"[Startup] Failed to disable: {e}")
        return False
