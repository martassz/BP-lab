import time
import csv
from abc import ABC, abstractmethod
from typing import Callable, Optional, Set, List

from core.serial_manager import SerialManager


class BaseMeasurement(ABC):
    """
    Základ pro všechna měření:
      - správa start/stop
      - callbacky pro nové datové body a změnu stavu
      - univerzální export do CSV
    """

    def __init__(self, serial_mgr: SerialManager):
        self.serial = serial_mgr
        self._on_data: Optional[Callable[[float, dict], None]] = None
        self._on_progress: Optional[Callable[[float], None]] = None
        self._on_finished: Optional[Callable[[], None]] = None
        self._running = False
        self._t0 = 0.0
        
        # Zde se mohou ukládat data pro export (seznam slovníků)
        # Pokud měření data neukládá, zůstane toto None nebo prázdné
        self.recorded_data: Optional[List[dict]] = None

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

    def export_to_csv(self, filename: str, allowed_sensors: Optional[Set[str]] = None) -> bool:
        """
        Univerzální export uložených dat do CSV.
        - Používá středník jako oddělovač (Excel friendly).
        - Převádí desetinné tečky na čárky.
        - Filtruje sloupce podle allowed_sensors (pokud je zadáno).
        """
        if not self.recorded_data:
            return False
        
        try:
            # 1. Zjistíme všechny dostupné klíče z prvního řádku
            all_keys = list(self.recorded_data[0].keys())
            
            # 2. Filtrace sloupců
            if allowed_sensors:
                # Vždy zachováme 't_s', zbytek filtrujeme
                fieldnames = [k for k in all_keys if k == "t_s" or k in allowed_sensors]
            else:
                fieldnames = all_keys
            
            # 3. Zajistíme, že t_s je první
            if "t_s" in fieldnames:
                fieldnames.remove("t_s")
                fieldnames.insert(0, "t_s")
            
            # 4. Zápis do souboru
            with open(filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
                writer.writeheader()
                
                for row in self.recorded_data:
                    # Vytvoříme filtrovaný řádek s formátovanými čísly
                    out_row = {}
                    for k in fieldnames:
                        if k in row:
                            val = row[k]
                            if isinstance(val, float):
                                # Trik pro český Excel: 10.5 -> 10,5
                                out_row[k] = str(val).replace('.', ',')
                            else:
                                out_row[k] = val
                    writer.writerow(out_row)
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False

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