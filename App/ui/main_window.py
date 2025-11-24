from typing import Optional, Type, Dict

from PySide6.QtCore import Slot, Signal, QTimer, Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox
)

from core.serial_manager import SerialManager
from core.parser import parse_json_message
from ui.realtime_plot import RealtimePlotWidget
from ui.styles import STYLESHEET

# --- NOVÉ IMPORTY ---
from ui.panels.sidebar import Sidebar
from ui.panels.cards import ValueCardsPanel

from measurements.base import BaseMeasurement
from measurements.streaming_measurement import StreamingTempMeasurement
from measurements.bme_dallas_slow import BmeDallasSlowMeasurement

class MainWindow(QMainWindow):
    # Interní signály pro "přemostění" thread-safe volání z BaseMeasurement
    measurement_data_signal = Signal(float, dict)
    measurement_progress_signal = Signal(float)
    measurement_finished_signal = Signal()
    handshake_received_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Temp-Lab Dashboard")
        self.resize(1200, 700)
        
        # Aplikace stylů
        self.setStyleSheet(STYLESHEET)

        self.serial_mgr = SerialManager()
        self.current_measurement: Optional[BaseMeasurement] = None

        self._measurement_types: Dict[str, Type[BaseMeasurement]] = {
            "Streaming (Rychlé - 100ms)": StreamingTempMeasurement,
            "Slow (Pomalé - 600s)": BmeDallasSlowMeasurement,
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
        
        # Hlavní horizontální layout (Sidebar | Obsah)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. SIDEBAR (Levý panel)
        # Předáme mu seznam názvů měření pro Combo Box
        meas_names = list(self._measurement_types.keys())
        self.sidebar = Sidebar(meas_names)
        
        # Propojení signálů ze Sidebaru
        self.sidebar.connect_requested.connect(self._handle_connect_request)
        self.sidebar.disconnect_requested.connect(self._handle_disconnect_request)
        self.sidebar.start_measurement_clicked.connect(self._start_measurement)
        self.sidebar.stop_measurement_clicked.connect(self._stop_measurement)
        self.sidebar.sensor_visibility_changed.connect(self._on_sensor_visibility_changed)

        # 2. CONTENT (Pravý panel)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # A) Kartičky s hodnotami
        self.cards_panel = ValueCardsPanel()
        content_layout.addWidget(self.cards_panel)
        
        # B) Graf
        self.plot_widget = RealtimePlotWidget(time_window_s=60.0)
        content_layout.addWidget(self.plot_widget, stretch=1)

        # Složení hlavního layoutu
        main_layout.addWidget(self.sidebar)
        main_layout.addLayout(content_layout)

    # --- Logic: Connection ---

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
        self.cards_panel.clear()
        self.plot_widget.clear()
        self.sidebar.clear_sensors()

    def _wait_for_handshake_callback(self, line: str):
        msg = parse_json_message(line)
        if msg and msg.get("type") == "hello":
            self.handshake_received_signal.emit()

    @Slot()
    def _on_handshake_ok(self):
        self.handshake_timer.stop()
        self.sidebar.set_connected_state(True)
        QMessageBox.information(self, "Připojeno", "Spojení s ESP32 navázáno.")

    @Slot()
    def _on_handshake_timeout(self):
        self.serial_mgr.close()
        self.sidebar.set_connected_state(False)
        QMessageBox.warning(self, "Timeout", "ESP32 neodpovědělo včas.")

    # --- Logic: Measurement ---

    @Slot(str)
    def _start_measurement(self, type_name: str):
        cls = self._measurement_types.get(type_name)
        if not cls: return

        # Reset UI
        self.cards_panel.clear()
        self.sidebar.clear_sensors()
        self.plot_widget.clear()
        self.sidebar.progress.setValue(0)

        # Start instance
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
        self._update_ui_state()

    @Slot()
    def _stop_measurement(self):
        if self.current_measurement:
            self.current_measurement.stop()
        self._update_ui_state()

    @Slot(float, dict)
    def _on_measurement_data_ui(self, t_s: float, values: dict):
        # 1. Aktualizovat seznam senzorů v sidebaru (pokud přibyl nový)
        self.sidebar.update_sensor_list(values)
        
        # 2. Aktualizovat kartičky (ukazujeme vše, co přijde)
        self.cards_panel.update_values(values)
        
        # 3. Aktualizovat graf (filtrujeme podle toho, co je zaškrtnuté)
        # Zde je drobná finta: Checkboxy v sidebaru ovládají VIDITELNOST křivek,
        # ne odesílání dat. Takže do grafu pošleme vše, a graf se rozhodne, co vykreslí.
        # ALE: Pokud RealtimePlotWidget nemá logiku pro skrývání, musíme to udělat tady.
        # Pro čistotu kódu pošleme vše a implementujeme "hide" logiku přímo v grafu 
        # (pomocí signálu visibility_changed).
        
        self.plot_widget.add_point(t_s, values)

    @Slot(str, bool)
    def _on_sensor_visibility_changed(self, key: str, visible: bool):
        # Tuhle metodu musíme přidat do RealtimePlotWidget
        if hasattr(self.plot_widget, "set_curve_visibility"):
            self.plot_widget.set_curve_visibility(key, visible)

    @Slot(float)
    def _on_measurement_progress_ui(self, fraction: float):
        val = max(0, min(100, int(fraction * 100)))
        self.sidebar.progress.setValue(val)

    @Slot()
    def _on_measurement_finished_ui(self):
        self.current_measurement = None
        self._update_ui_state()

    def _update_ui_state(self):
        running = self.current_measurement is not None and self.current_measurement.is_running()
        self.sidebar.set_measurement_running(running)