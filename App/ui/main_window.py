from typing import Optional, Type, Dict, Set

from PySide6.QtCore import Slot, Signal, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox
)

# --- Core & Utils ---
from core.serial_manager import SerialManager
from core.parser import parse_json_message
from ui.styles import STYLESHEET

# --- DŮLEŽITÉ: Ujisti se, že máš tyto soubory na správném místě ---
from ui.panels.sidebar import Sidebar
from ui.panels.cards import ValueCardsPanel
from ui.realtime_plot import RealtimePlotWidget
from ui.dialogs.sensor_config import SensorConfigDialog

# --- Měření ---
from measurements.base import BaseMeasurement
from measurements.streaming_measurement import StreamingTempMeasurement
from measurements.bme_dallas_slow import BmeDallasSlowMeasurement


class MainWindow(QMainWindow):
    measurement_data_signal = Signal(float, dict)
    measurement_progress_signal = Signal(float)
    measurement_finished_signal = Signal()
    handshake_received_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Temp-Lab Dashboard")
        self.resize(1200, 750)
        self.setStyleSheet(STYLESHEET)

        self.serial_mgr = SerialManager()
        self.current_measurement: Optional[BaseMeasurement] = None

        # Filtrace senzorů (prázdná = zobrazit vše)
        self.allowed_sensors: Set[str] = set()

        self._measurement_types: Dict[str, Type[BaseMeasurement]] = {
            "Kontinuální (Rychlé)": StreamingTempMeasurement,
            "Dlouhodobé (Pomalé)": BmeDallasSlowMeasurement,
        }

        self.handshake_timer = QTimer()
        self.handshake_timer.setSingleShot(True)
        self.handshake_timer.timeout.connect(self._on_handshake_timeout)
        
        self.handshake_received_signal.connect(self._on_handshake_ok)
        self.measurement_data_signal.connect(self._on_measurement_data_ui)
        self.measurement_progress_signal.connect(self._on_measurement_progress_ui)
        self.measurement_finished_signal.connect(self._on_measurement_finished_ui)

        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. LEVÝ PANEL (Sidebar)
        self.sidebar = Sidebar(list(self._measurement_types.keys()))
        
        # ZDE VZNIKALA CHYBA - Sidebar musí mít tento signál definovaný
        self.sidebar.connect_requested.connect(self._handle_connect_request)
        self.sidebar.disconnect_requested.connect(self._handle_disconnect_request)
        self.sidebar.start_measurement_clicked.connect(self._start_measurement)
        self.sidebar.stop_measurement_clicked.connect(self._stop_measurement)
        self.sidebar.sensor_settings_clicked.connect(self._open_sensor_settings)

        # 2. PRAVÝ PANEL
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.cards_panel = ValueCardsPanel()
        content_layout.addWidget(self.cards_panel)
        
        self.plot_widget = RealtimePlotWidget(time_window_s=60.0)
        content_layout.addWidget(self.plot_widget, stretch=1)

        main_layout.addWidget(self.sidebar)
        main_layout.addLayout(content_layout)

    @Slot()
    def _open_sensor_settings(self):
        # Pokud soubor sensor_config.py neexistuje, zde to spadne na ImportError
        dlg = SensorConfigDialog(self.allowed_sensors, self)
        if dlg.exec():
            self.allowed_sensors = dlg.get_allowed_sensors()

    # --- Ostatní metody (Connection / Measurement) ---

    @Slot(str)
    def _handle_connect_request(self, port: str):
        try:
            self.serial_mgr.open(port)
            self.serial_mgr.set_line_callback(self._wait_for_handshake_callback)
            self.sidebar.set_waiting_state()
            self.handshake_timer.start(3000)
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nelze otevřít port:\n{e}")
            self.sidebar.set_connected_state(False)

    @Slot()
    def _handle_disconnect_request(self):
        self.serial_mgr.close()
        self.sidebar.set_connected_state(False)
        self.sidebar.set_measurement_running(False)
        self.cards_panel.clear()
        self.plot_widget.clear()

    def _wait_for_handshake_callback(self, line: str):
        msg = parse_json_message(line)
        if msg and msg.get("type") == "hello":
            self.handshake_received_signal.emit()

    @Slot()
    def _on_handshake_ok(self):
        self.handshake_timer.stop()
        self.sidebar.set_connected_state(True)
        QMessageBox.information(self, "Připojeno", "Spojení s ESP32 úspěšně navázáno.")

    @Slot()
    def _on_handshake_timeout(self):
        self.serial_mgr.close()
        self.sidebar.set_connected_state(False)
        QMessageBox.warning(self, "Timeout", "ESP32 neodpovědělo včas.")

    @Slot(str)
    def _start_measurement(self, type_name: str):
        cls = self._measurement_types.get(type_name)
        if not cls: return

        self.cards_panel.clear()
        self.plot_widget.clear()
        self.sidebar.progress.setValue(0)

        self.current_measurement = cls(self.serial_mgr)
        if hasattr(self.current_measurement, "DURATION_S"):
            self.plot_widget.set_time_window(self.current_measurement.DURATION_S)

        self.current_measurement.set_callbacks(
            on_data=lambda t, v: self.measurement_data_signal.emit(t, v),
            on_progress=lambda f: self.measurement_progress_signal.emit(f),
            on_finished=lambda: self.measurement_finished_signal.emit(),
        )
        self.serial_mgr.set_line_callback(self.current_measurement.handle_line)
        self.current_measurement.start()
        self.sidebar.set_measurement_running(True)

    @Slot()
    def _stop_measurement(self):
        if self.current_measurement:
            self.current_measurement.stop()
        self.sidebar.set_measurement_running(False)

    @Slot(float, dict)
    def _on_measurement_data_ui(self, t_s: float, values: dict):
        # Filtrace
        if self.allowed_sensors:
            filtered_values = {k: v for k, v in values.items() if k in self.allowed_sensors}
        else:
            filtered_values = values

        if not filtered_values: return

        self.cards_panel.update_values(filtered_values)
        self.plot_widget.add_point(t_s, filtered_values)

    @Slot(float)
    def _on_measurement_progress_ui(self, fraction: float):
        val = max(0, min(100, int(fraction * 100)))
        self.sidebar.progress.setValue(val)

    @Slot()
    def _on_measurement_finished_ui(self):
        self.current_measurement = None
        self.sidebar.set_measurement_running(False)
        QMessageBox.information(self, "Hotovo", "Měření bylo dokončeno.")