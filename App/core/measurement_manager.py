from typing import Optional, Dict, Type, Set, Any
from PySide6.QtCore import QObject, Signal

from core.serial_manager import SerialManager
from measurements.base import BaseMeasurement
from measurements.streaming_measurement import StreamingTempMeasurement
from measurements.bme_dallas_slow import BmeDallasSlowMeasurement
from measurements.part_one import PartOneMeasurement

class MeasurementManager(QObject):
    data_received = Signal(float, dict)
    progress_updated = Signal(float)
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, serial_mgr: SerialManager):
        super().__init__()
        self._serial_mgr = serial_mgr
        self._current_measurement: Optional[BaseMeasurement] = None
        
        self._types: Dict[str, Type[BaseMeasurement]] = {
            PartOneMeasurement.DISPLAY_NAME: PartOneMeasurement,
            "Krátké měření": StreamingTempMeasurement,
            "Pomalé měření": BmeDallasSlowMeasurement,
        }

    def get_available_types(self):
        return list(self._types.keys())

    def start_measurement(self, type_name: str, **kwargs):
        """
        Spustí vybrané měření. 
        Argumenty v **kwargs jsou předány konstruktoru třídy měření.
        """
        cls = self._types.get(type_name)
        if not cls:
            self.error_occurred.emit(f"Neznámý typ měření: {type_name}")
            return

        self.stop_measurement()

        # Zde předáme kwargs (např. pwm_channel, pwm_value) do konstruktoru
        # Pokud měření tyto argumenty nečeká, je nutné zajistit, aby kwargs byly prázdné,
        # nebo aby třída akceptovala **kwargs.
        # V našem případě to řídí MainWindow.
        try:
            self._current_measurement = cls(self._serial_mgr, **kwargs)
            
            self._current_measurement.set_callbacks(
                on_data=self._on_data_callback,
                on_progress=self.progress_updated.emit,
                on_finished=self.finished.emit
            )

            self._serial_mgr.set_line_callback(self._current_measurement.handle_line)
            self._current_measurement.start()
            
        except TypeError as e:
            # Ošetření chyby, pokud pošleme argumenty třídě, která je nečeká
            self.error_occurred.emit(f"Chyba při inicializaci měření: {e}")
            print(f"Init Error: {e}")

    def stop_measurement(self):
        if self._current_measurement:
            self._current_measurement.stop()

    def export_data(self, filename: str, allowed_sensors: Optional[Set[str]] = None) -> bool:
        if not self._current_measurement: return False
        
        if hasattr(self._current_measurement, "export_to_csv"):
            return self._current_measurement.export_to_csv(filename, allowed_sensors)
        return False

    def is_running(self) -> bool:
        return self._current_measurement.is_running() if self._current_measurement else False

    def get_duration(self) -> float:
        if self._current_measurement and hasattr(self._current_measurement, "DURATION_S"):
            return self._current_measurement.DURATION_S
        return 60.0

    def _on_data_callback(self, t_s: float, values: dict):
        self.data_received.emit(t_s, values)