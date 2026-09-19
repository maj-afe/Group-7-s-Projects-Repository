import sys

def SystemController():
    """
    Factory function returning OS-specific SystemController instance.
    """
    if sys.platform == "win32":
        from app.system.backends.windows import WindowsSystemController
        return WindowsSystemController()
    elif sys.platform.startswith("linux"):
        from app.system.backends.linux import LinuxSystemController
        return LinuxSystemController()
    else:
        from app.system.backends.dummy import DummySystemController
        return DummySystemController()