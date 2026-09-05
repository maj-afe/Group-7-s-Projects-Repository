# app/system/signal_bridge.py

from PySide6.QtCore import QObject, Signal

class SignalBridge(QObject):
    """
    Thread-safe signal bridge for GUI operations.
    Allows background threads to request GUI actions on the main thread.
    """
    
    # Signal to request power confirmation dialog
    request_power_confirmation = Signal(str)  # 'lock', 'sleep', 'restart', 'shutdown'
    
    # Singleton instance
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._initialized = True