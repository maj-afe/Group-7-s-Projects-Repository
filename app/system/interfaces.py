from abc import ABC, abstractmethod
from typing import List

class BaseWindowManager(ABC):
    @abstractmethod
    def get_all_windows(self) -> List[str]:
        pass

    @abstractmethod
    def find_window(self, title_keyword: str) -> bool:
        pass

    @abstractmethod
    def switch_to_window(self, title_keyword: str) -> bool:
        pass

    @abstractmethod
    def minimize_window(self, title_keyword: str) -> bool:
        pass

    @abstractmethod
    def maximize_window(self, title_keyword: str) -> bool:
        pass

    @abstractmethod
    def move_active_window(self, direction: str) -> bool:
        pass

    @abstractmethod
    def close_active_window(self) -> bool:
        pass

    @abstractmethod
    def get_last_error(self) -> str:
        pass

class BaseSystemController(ABC):
    @abstractmethod
    def lock_computer(self) -> bool:
        pass

    @abstractmethod
    def sleep_computer(self) -> bool:
        pass

    @abstractmethod
    def restart_computer(self) -> bool:
        pass

    @abstractmethod
    def shutdown_computer(self) -> bool:
        pass

    @abstractmethod
    def get_last_error(self) -> str:
        pass
