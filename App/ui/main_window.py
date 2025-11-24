from typing import Optional, Type, Dict

from PySide6.QtCore import Slot, Signal, QTimer, Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QComboBox, QLabel, QProgressBar, QMessageBox,
    QFrame, QScrollArea
)
from PySide6.QtGui import QFont

from core.serial_manager import SerialManager
from core.parser import parse_json_message
from ui.realtime_plot import RealtimePlotWidget
from measurements.base import BaseMeasurement
from measurements.streaming_measurement import StreamingTempMeasurement

# --- MODERNÍ DARK THEME (FINAL FIX) ---
STYLESHEET = """
QMainWindow {
    background-color: #1e1e1e;
    color: #e0e0e0;
}
QWidget {
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
    color: #e0e0e0;
}

/* --- SIDEBAR --- */
QFrame#Sidebar {
    background-color: #252526;
    border-right: 1px solid #3e3e42;
}

/* --- KARTIČKY HODNOT (Vylepšená viditelnost) --- */
QFrame#ValueCard {
    background-color: #2d2d30; 
    border-radius: 6px;
    /* Světle šedý rámeček, aby byl dobře vidět na tmavém pozadí */
    border: 2px solid #B0B0B0; 
}
QFrame#ValueCard:hover {
    border: 2px solid #007acc; /* Modrá při najetí myší */
    background-color: #383838;
}
QLabel#ValueTitle {
    color: #007acc; /* Modrý nadpis */
    font-size: 13px;
    font-weight: bold;
    text-transform: uppercase;
}
QLabel#ValueNumber {
    color: #ffffff;
    font-size: 26px;
    font-weight: bold;
}

/* --- TLAČÍTKA --- */
QPushButton {
    background-color: #3e3e42;
    border: none;
    color: white;
    padding: 10px;
    border-radius: 5px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #505050;
}
QPushButton:disabled {
    background-color: #2d2d30;
    color: #606060;
    border: 1px solid #333333;
}

QPushButton#BtnConnect { background-color: #007acc; }
QPushButton#BtnConnect:hover { background-color: #0098ff; }
QPushButton#BtnConnect:disabled { background-color: #2d2d30; color: #aaaaaa; }

QPushButton#BtnStart { background-color: #2ea043; }
QPushButton#BtnStart:hover { background-color: #3fb950; }
QPushButton#BtnStart:disabled { background-color: #2d2d30; color: #606060; }

QPushButton#BtnStop { background-color: #da3633; }
QPushButton#BtnStop:hover { background-color: #f85149; }
QPushButton#BtnStop:disabled { background-color: #2d2d30; color: #606060; }

/* --- COMBOBOX (OPRAVA ČERNÉHO TEXTU) --- */
QComboBox {
    background-color: #333337;
    border: 1px solid #505050;
    padding: 5px;
    border-radius: 4px;
    color: white; /* Text v zavřeném stavu */
}
QComboBox:hover {
    border: 1px solid #007acc;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}

/* Tady je ten trik pro rozbalovací seznam */
QComboBox QAbstractItemView {
    background-color: #252526; /* Tmavé pozadí seznamu */
    color: white;              /* Bílé písmo položek */
    border: 1px solid #3e3e42;
    selection-background-color: #007acc;
    selection-color: white;
    outline: 0;
}

/* --- MODÁLNÍ OKNA --- */
QMessageBox { background-color: #252526; color: #e0e0e0; }
QMessageBox QLabel { color: #e0e0e0; }
QMessageBox QPushButton {
    width: 80px;
    background-color: #3e3e42;
    border: 1px solid #505050;
}
QMessageBox QPushButton:hover { background-color: #505050; }

/* --- PROGRESS BAR --- */
QProgressBar {
    border: 1px solid #3e3e42;
    border-radius: 4px;
    text-align: center;
    background-color: #252526;
}
QProgressBar::chunk {
    background-color: #007acc;
    border-radius: 3px;
}

/* --- SCROLLBAR --- */
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:horizontal {
    border: none;
    background: #252526;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #424242;
    min-width: 20px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #606060;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    background: none;
    border: none;
}
"""

class MainWindow(QMainWindow):
    measurement_data_signal = Signal(float, dict)
    measurement_progress_signal = Signal(float)
    measurement_finished_signal = Signal()
    handshake_received_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Temp-Lab Dashboard")
        self.resize(1200, 700)
        
        self.setStyleSheet(STYLESHEET)

        self.serial_mgr = SerialManager()
        self.current_measurement: Optional[BaseMeasurement] = None

        self._measurement_types: Dict[str, Type[BaseMeasurement]] = {
            "Streaming (Rychlé)": StreamingTempMeasurement,
        }

        self.handshake_timer = QTimer()
        self.handshake_timer.setSingleShot(True)
        self.handshake_timer.timeout.connect(self._on_handshake_timeout)
        
        self.live_value_labels: Dict[str, QLabel] = {}

        self._init_ui()
        
        self.handshake_received_signal.connect(self._on_handshake_ok)
        self.measurement_data_signal.connect(self._on_measurement_data_ui)
        self.measurement_progress_signal.connect(self._on_measurement_progress_ui)
        self.measurement_finished_signal.connect(self._on_measurement_finished_ui)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === SIDEBAR ===
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 20, 15, 20)
        sidebar_layout.setSpacing(15)

        # PŘIPOJENÍ
        lbl_conn = QLabel("PŘIPOJENÍ")
        lbl_conn.setStyleSheet("color: #808080; font-weight: bold; letter-spacing: 1px;")
        sidebar_layout.addWidget(lbl_conn)

        self.combo_ports = QComboBox()
        self.combo_ports.addItems(SerialManager.list_ports())
        sidebar_layout.addWidget(self.combo_ports)

        self.btn_connect = QPushButton("Připojit k ESP")
        self.btn_connect.setObjectName("BtnConnect")
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        sidebar_layout.addWidget(self.btn_connect)

        sidebar_layout.addSpacing(20)
        
        # MĚŘENÍ
        lbl_meas = QLabel("MĚŘENÍ")
        lbl_meas.setStyleSheet("color: #808080; font-weight: bold; letter-spacing: 1px;")
        sidebar_layout.addWidget(lbl_meas)

        self.combo_type = QComboBox()
        self.combo_type.addItems(list(self._measurement_types.keys()))
        sidebar_layout.addWidget(self.combo_type)

        self.btn_start = QPushButton("START")
        self.btn_start.setObjectName("BtnStart")
        self.btn_start.setFixedHeight(40)
        self.btn_start.clicked.connect(self._start_measurement)
        self.btn_start.setEnabled(False) 
        sidebar_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setObjectName("BtnStop")
        self.btn_stop.clicked.connect(self._stop_measurement)
        self.btn_stop.setEnabled(False)
        sidebar_layout.addWidget(self.btn_stop)

        sidebar_layout.addStretch()
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        sidebar_layout.addWidget(self.progress)

        # === CONTENT ===
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # SCROLL AREA PRO HODNOTY
        scroll_area = QScrollArea()
        scroll_area.setFixedHeight(130)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("background-color: #1e1e1e; border: none;")

        self.values_container = QWidget()
        self.values_container.setStyleSheet("background-color: #1e1e1e;")
        self.values_layout = QHBoxLayout(self.values_container)
        self.values_layout.setContentsMargins(20, 15, 20, 15)
        self.values_layout.setSpacing(15)
        self.values_layout.addStretch()
        
        scroll_area.setWidget(self.values_container)
        
        content_layout.addWidget(scroll_area)
        
        self.plot_widget = RealtimePlotWidget(time_window_s=60.0)
        content_layout.addWidget(self.plot_widget, stretch=1)

        main_layout.addWidget(sidebar)
        main_layout.addLayout(content_layout)

    # --- Logic: Live Values ---

    def _update_live_values(self, values: dict):
        for key, val in values.items():
            str_val = f"{val:.2f} °C"
            if key not in self.live_value_labels:
                self._create_value_card(key, str_val)
            else:
                self.live_value_labels[key].setText(str_val)

    def _create_value_card(self, key: str, initial_val: str):
        # Bereme název z grafu (pro konzistenci s legendou)
        pretty_name = RealtimePlotWidget.format_sensor_name(key)

        frame = QFrame()
        frame.setObjectName("ValueCard")
        frame.setFixedWidth(140)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        
        lbl_title = QLabel(pretty_name)
        lbl_title.setObjectName("ValueTitle")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        lbl_val = QLabel(initial_val)
        lbl_val.setObjectName("ValueNumber")
        lbl_val.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        
        self.live_value_labels[key] = lbl_val
        
        self.values_layout.insertWidget(self.values_layout.count() - 1, frame)

    def _clear_live_values(self):
        while self.values_layout.count() > 1:
            item = self.values_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.live_value_labels.clear()

    # --- Logic: Connection ---

    @Slot()
    def _on_connect_clicked(self):
        port = self.combo_ports.currentText()
        if not port: return
        try:
            self.serial_mgr.open(port)
            self.serial_mgr.set_line_callback(self._wait_for_handshake_callback)
            self.btn_connect.setText("Čekám...")
            self.btn_connect.setEnabled(False)
            self.combo_ports.setEnabled(False)
            self.handshake_timer.start(3000) 
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nelze otevřít port:\n{e}")

    def _wait_for_handshake_callback(self, line: str):
        msg = parse_json_message(line)
        if msg and msg.get("type") == "hello":
            self.handshake_received_signal.emit()

    @Slot()
    def _on_handshake_ok(self):
        self.handshake_timer.stop()
        self.btn_connect.setText("PŘIPOJENO")
        self.btn_connect.setStyleSheet("background-color: #2ea043; color: white;")
        self.btn_start.setEnabled(True) 
        QMessageBox.information(
            self, 
            "Stav systému", 
            "Spojení s měřicí jednotkou bylo úspěšně navázáno.\n"
            "Handshake protokol potvrzen.\n\n"
            "Systém je připraven k zahájení sběru dat."
        )

    @Slot()
    def _on_handshake_timeout(self):
        self.serial_mgr.close()
        self.btn_connect.setText("Připojit k ESP")
        self.btn_connect.setEnabled(True)
        self.combo_ports.setEnabled(True)
        self.btn_start.setEnabled(False)
        QMessageBox.warning(self, "Chyba připojení", "Časový limit vypršel (Timeout).\nOvěřte připojení USB kabelu a správnost COM portu.")

    # --- Logic: Measurement ---

    @Slot()
    def _start_measurement(self):
        type_name = self.combo_type.currentText()
        cls = self._measurement_types.get(type_name)
        if not cls: return

        self._clear_live_values()
        self.current_measurement = cls(self.serial_mgr)
        if hasattr(self.current_measurement, "DURATION_S"):
            self.plot_widget.set_time_window(self.current_measurement.DURATION_S)

        self.current_measurement.set_callbacks(
            on_data=lambda t, v: self.measurement_data_signal.emit(t, v),
            on_progress=lambda f: self.measurement_progress_signal.emit(f),
            on_finished=lambda: self.measurement_finished_signal.emit(),
        )
        self.serial_mgr.set_line_callback(self.current_measurement.handle_line)
        self.plot_widget.clear()
        self.progress.setValue(0)
        self.current_measurement.start()
        self._update_ui_state()

    @Slot()
    def _stop_measurement(self):
        if self.current_measurement:
            self.current_measurement.stop()
        self._update_ui_state()

    @Slot(float, dict)
    def _on_measurement_data_ui(self, t_s: float, values: dict):
        self.plot_widget.add_point(t_s, values)
        self._update_live_values(values)

    @Slot(float)
    def _on_measurement_progress_ui(self, fraction: float):
        val = max(0, min(100, int(fraction * 100)))
        self.progress.setValue(val)

    @Slot()
    def _on_measurement_finished_ui(self):
        self.current_measurement = None
        self._update_ui_state()
        self.btn_start.setEnabled(True)

    def _update_ui_state(self):
        running = self.current_measurement is not None and self.current_measurement.is_running()
        self.btn_start.setEnabled(not running and self.serial_mgr.is_open())
        self.btn_stop.setEnabled(running)
        self.combo_type.setEnabled(not running)