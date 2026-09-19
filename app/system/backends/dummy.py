from typing import List
from app.system.interfaces import BaseWindowManager, BaseSystemController

class DummyWindowManager(BaseWindowManager):
    def __init__(self):
        self._last_error = "Platform unsupported. Using DummyWindowManager."

    def get_all_windows(self) -> List[str]:
        return []

    def find_window(self, title_keyword: str) -> bool:
        return False

    def switch_to_window(self, title_keyword: str) -> bool:
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

class DummySystemController(BaseSystemController):
    def __init__(self):
        self._last_error = "Platform unsupported. Using DummySystemController."

    def lock_computer(self) -> bool:
        return False

    def sleep_computer(self) -> bool:
        return False

    def restart_computer(self) -> bool:
        return False

    def shutdown_computer(self) -> bool:
        return False

    def get_last_error(self) -> str:
        return self._last_error
