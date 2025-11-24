import time
from abc import ABC, abstractmethod
from typing import Callable, Optional

from core.serial_manager import SerialManager


class BaseMeasurement(ABC):
    """
    Základ pro všechna měření:
      - správa start/stop
      - callbacky pro nové datové body a změnu stavu
    """

    def __init__(self, serial_mgr: SerialManager):
        self.serial = serial_mgr
        self._on_data: Optional[Callable[[float, dict], None]] = None
        self._on_progress: Optional[Callable[[float], None]] = None
        self._on_finished: Optional[Callable[[], None]] = None
        self._running = False
        self._t0 = 0.0

    def set_callbacks(
        self,
        on_data: Callable[[float, dict], None],
        on_progress: Callable[[float], None],
        on_finished: Callable[[], None],
    ):
        self._on_data = on_data
        self._on_progress = on_progress
        self._on_finished = on_finished

    def start(self):
        if self._running:
            return
        self._t0 = time.time()
        self._running = True
        self.on_start()

    def stop(self):
        if not self._running:
            return
        self._running = False
        self.on_stop()
        if self._on_finished:
            self._on_finished()

    def is_running(self) -> bool:
        return self._running

    def now_s(self) -> float:
        return time.time() - self._t0

    def emit_data(self, t_s: float, values: dict):
        if self._on_data:
            self._on_data(t_s, values)

    def emit_progress(self, fraction: float):
        if self._on_progress:
            self._on_progress(max(0.0, min(1.0, fraction)))

    @abstractmethod
    def on_start(self):
        ...

    @abstractmethod
    def on_stop(self):
        ...

    @abstractmethod
    def handle_line(self, line: str):
        """
        Každé měření si samo rozhodne, co s přijatým řádkem ze sériovky.
        Volá UI / jádro přes SerialManager.set_line_callback(...)
        """
        ...
