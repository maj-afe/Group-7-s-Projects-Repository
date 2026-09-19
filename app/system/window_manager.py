import sys

def WindowManager():
    """
    Factory function returning OS-specific WindowManager instance.
    """
    if sys.platform == "win32":
        from app.system.backends.windows import WindowsWindowManager
        return WindowsWindowManager()
    elif sys.platform.startswith("linux"):
        from app.system.backends.linux import LinuxWindowManager
        return LinuxWindowManager()
    else:
        from app.system.backends.dummy import DummyWindowManager
        return DummyWindowManager()