from typing import Optional, Set
from PySide6.QtCore import Slot, QTimer, Signal  # <-- Signal musí být importován
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox, QFileDialog
)

from core.serial_manager import SerialManager
from core.parser import parse_json_message
from core.measurement_manager import MeasurementManager 
from ui.styles import STYLESHEET

from ui.panels.sidebar import Sidebar
from ui.panels.cards import ValueCardsPanel
from ui.realtime_plot import RealtimePlotWidget
from ui.dialogs.sensor_config import SensorConfigDialog
from measurements.part_one import PartOneMeasurement 

class MainWindow(QMainWindow):
    # --- DEFINICE SIGNÁLŮ ---
    handshake_received_signal = Signal() # <-- TOTO CHYBĚLO

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Temp-Lab Dashboard")
        self.resize(1200, 750)
        self.setStyleSheet(STYLESHEET)

        self.serial_mgr = SerialManager()
        self.meas_mgr = MeasurementManager(self.serial_mgr)
        self.allowed_sensors: Set[str] = set()
        
        self.detected_sensors: list[str] = []

        self.meas_mgr.data_received.connect(self._on_measurement_data)
        self.meas_mgr.progress_updated.connect(self._on_measurement_progress)
        self.meas_mgr.finished.connect(self._on_measurement_finished)
        self.meas_mgr.error_occurred.connect(lambda msg: QMessageBox.warning(self, "Chyba", msg))

        # Nyní už tento signál existuje a půjde propojit
        self.handshake_received_signal.connect(self._on_handshake_ok)

        self.handshake_timer = QTimer()
        self.handshake_timer.setSingleShot(True)
        self.handshake_timer.timeout.connect(self._on_handshake_timeout)

        self._init_ui()
        
        # Ošetření prázdného slovníku typů měření
        available_types = self.meas_mgr.get_available_types()
        if available_types:
            first_type = available_types[0]
            self._on_measurement_type_changed(first_type)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar(self.meas_mgr.get_available_types())
        self.sidebar.connect_requested.connect(self._handle_connect_request)
        self.sidebar.disconnect_requested.connect(self._handle_disconnect_request)
        self.sidebar.start_measurement_clicked.connect(self._start_measurement)
        self.sidebar.stop_measurement_clicked.connect(self._stop_measurement)
        self.sidebar.sensor_settings_clicked.connect(self._open_sensor_settings)
        self.sidebar.measurement_type_changed.connect(self._on_measurement_type_changed)
        self.sidebar.pwm_changed.connect(self._on_pwm_changed)
        self.sidebar.export_clicked.connect(self._on_export_clicked)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.cards_panel = ValueCardsPanel()
        right_layout.addWidget(self.cards_panel)
        
        self.plot_widget = RealtimePlotWidget(time_window_s=60.0)
        right_layout.addWidget(self.plot_widget, stretch=1)

        layout.addWidget(self.sidebar)
        layout.addLayout(right_layout)

    @Slot(str)
    def _on_measurement_type_changed(self, type_name: str):
        if type_name == PartOneMeasurement.DISPLAY_NAME:
            self.sidebar.show_pwm_controls()
            self.plot_widget.set_dual_axis_mode(True)
        else:
            self.sidebar.show_simple_controls()
            self.plot_widget.set_dual_axis_mode(False)
        
        self.plot_widget.clear()
        self.cards_panel.clear()

    @Slot(str)
    def _start_measurement(self, type_name: str):
        self.cards_panel.clear()
        self.plot_widget.clear()
        self.sidebar.progress.setValue(0)
        self.sidebar.set_measurement_running(True)

        self.meas_mgr.start_measurement(type_name)
        
        duration = self.meas_mgr.get_duration()
        self.plot_widget.set_time_window(60.0 if duration > 300 else duration)

    @Slot()
    def _stop_measurement(self):
        self.meas_mgr.stop_measurement()

    @Slot()
    def _on_export_clicked(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Uložit CSV", "", "CSV (*.csv)")
        if filename:
            if self.meas_mgr.export_data(filename):
                QMessageBox.information(self, "OK", "Data exportována.")
            else:
                QMessageBox.warning(self, "Chyba", "Nelze exportovat data.")

    @Slot(int, int)
    def _on_pwm_changed(self, channel: int, value: int):
        if self.serial_mgr.is_open():
            self.serial_mgr.write_line(f"SET PWM {channel} {value}")

    @Slot(float, dict)
    def _on_measurement_data(self, t_s: float, values: dict):
        if self.allowed_sensors:
            filtered = {k: v for k, v in values.items() if k in self.allowed_sensors}
        else:
            filtered = values
        if filtered:
            self.cards_panel.update_values(filtered)
            self.plot_widget.add_point(t_s, filtered)

    @Slot(float)
    def _on_measurement_progress(self, fraction: float):
        val = max(0, min(100, int(fraction * 100)))
        self.sidebar.progress.setValue(val)

    @Slot()
    def _on_measurement_finished(self):
        self.sidebar.set_measurement_running(False)
        QMessageBox.information(self, "Hotovo", "Měření dokončeno.")
    
    @Slot(str)
    def _handle_connect_request(self, port: str):
        try:
            self.serial_mgr.open(port)
            self.serial_mgr.set_line_callback(self._wait_for_handshake)
            self.sidebar.set_waiting_state()
            self.handshake_timer.start(3000)
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Port nelze otevřít:\n{e}")
            self.sidebar.set_connected_state(False)

    def _wait_for_handshake(self, line: str):
        # Běží ve vlákně SerialManageru
        msg = parse_json_message(line)
        if msg and msg.get("type") == "hello":
            self.detected_sensors = []
            if str(msg.get("bme")).lower() == "true":
                self.detected_sensors.append("T_BME")
            if str(msg.get("tmp")).lower() == "true":
                self.detected_sensors.append("T_TMP")
            if str(msg.get("adc")).lower() == "true":
                self.detected_sensors.extend(["ADC_R", "ADC_NTC", "ESP_R", "ESP_NTC"])
            try:
                dallas_count = int(msg.get("dallas", 0))
                for i in range(dallas_count):
                    self.detected_sensors.append(f"T_DS{i}")
            except: pass
            
            print(f"Detekováno: {self.detected_sensors}")
            
            # Emitujeme signál, který bezpečně přejde do hlavního vlákna GUI
            self.handshake_received_signal.emit()

    @Slot()
    def _on_handshake_ok(self):
        self.handshake_timer.stop()
        self.sidebar.set_connected_state(True)
        QMessageBox.information(self, "Připojeno", "Spojení navázáno.")

    @Slot()
    def _on_handshake_timeout(self):
        self.serial_mgr.close()
        self.sidebar.set_connected_state(False)
        QMessageBox.warning(self, "Timeout", "ESP32 neodpovědělo.")

    @Slot()
    def _handle_disconnect_request(self):
        self.meas_mgr.stop_measurement()
        self.serial_mgr.close()
        self.sidebar.set_connected_state(False)
        self.sidebar.set_measurement_running(False)
        self.cards_panel.clear()
        self.plot_widget.clear()
        
    @Slot()
    def _open_sensor_settings(self):
        dlg = SensorConfigDialog(self.allowed_sensors, self.detected_sensors, self)
        if dlg.exec():
            self.allowed_sensors = dlg.get_allowed_sensors()