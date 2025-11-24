from typing import List, Dict
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QComboBox, QPushButton, 
    QProgressBar, QListWidget, QListWidgetItem, QWidget
)
from PySide6.QtCore import Signal, Qt, Slot

from core.serial_manager import SerialManager
from ui.realtime_plot import RealtimePlotWidget  # Pro formátování názvů

class Sidebar(QFrame):
    # Signály pro komunikaci s hlavním oknem
    connect_requested = Signal(str)  # Posílá název portu
    disconnect_requested = Signal()
    start_measurement_clicked = Signal(str) # Posílá typ měření
    stop_measurement_clicked = Signal()
    sensor_visibility_changed = Signal(str, bool) # (klíč senzoru, je_vidět)

    def __init__(self, measurement_types: List[str], parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(250)
        
        self._init_ui(measurement_types)
        
        # Interní stav senzorů (abychom nepřidávali duplicity)
        self._known_sensors = set()

    def _init_ui(self, measurement_types: List[str]):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(15)

        # --- SEKCE PŘIPOJENÍ ---
        lbl_conn = QLabel("PŘIPOJENÍ")
        lbl_conn.setStyleSheet("color: #808080; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(lbl_conn)

        self.combo_ports = QComboBox()
        self.combo_ports.addItems(SerialManager.list_ports())
        layout.addWidget(self.combo_ports)

        self.btn_connect = QPushButton("Připojit k ESP")
        self.btn_connect.setObjectName("BtnConnect")
        self.btn_connect.clicked.connect(self._on_connect_click)
        layout.addWidget(self.btn_connect)

        layout.addSpacing(20)

        # --- SEKCE MĚŘENÍ ---
        lbl_meas = QLabel("MĚŘENÍ")
        lbl_meas.setStyleSheet("color: #808080; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(lbl_meas)

        self.combo_type = QComboBox()
        self.combo_type.addItems(measurement_types)
        layout.addWidget(self.combo_type)

        self.btn_start = QPushButton("START")
        self.btn_start.setObjectName("BtnStart")
        self.btn_start.setFixedHeight(40)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._on_start_click)
        layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setObjectName("BtnStop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_click)
        layout.addWidget(self.btn_stop)

        layout.addSpacing(10)

        # --- SEKCE SENZORY (Dynamický seznam) ---
        lbl_sens = QLabel("AKTIVNÍ SENZORY")
        lbl_sens.setStyleSheet("color: #808080; font-weight: bold; font-size: 12px;")
        layout.addWidget(lbl_sens)

        self.sensor_list = QListWidget()
        self.sensor_list.setStyleSheet("""
            QListWidget { border: none; background-color: #252526; }
            QListWidget::item { padding: 5px; }
        """)
        self.sensor_list.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.sensor_list)

        layout.addStretch()

        # --- PROGRESS BAR ---
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        layout.addWidget(self.progress)

    # --- Veřejné metody pro update UI zvenčí ---

    def update_ports(self):
        current = self.combo_ports.currentText()
        self.combo_ports.clear()
        self.combo_ports.addItems(SerialManager.list_ports())
        self.combo_ports.setCurrentText(current)

    def set_connected_state(self, connected: bool):
        if connected:
            self.btn_connect.setText("PŘIPOJENO")
            self.btn_connect.setStyleSheet("background-color: #2ea043; color: white;")
            self.combo_ports.setEnabled(False)
            self.btn_connect.clicked.disconnect()
            self.btn_connect.clicked.connect(self._on_disconnect_click)
            self.btn_start.setEnabled(True)
        else:
            self.btn_connect.setText("Připojit k ESP")
            self.btn_connect.setStyleSheet("") # Reset stylu (handled by stylesheet)
            self.btn_connect.setObjectName("BtnConnect") # Re-apply ID style
            self.combo_ports.setEnabled(True)
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(False)
            
            # Reset signálů tlačítka
            try: self.btn_connect.clicked.disconnect()
            except: pass
            self.btn_connect.clicked.connect(self._on_connect_click)

    def set_measurement_running(self, running: bool):
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.combo_type.setEnabled(not running)

    def set_waiting_state(self):
        self.btn_connect.setText("Čekám...")
        self.btn_connect.setEnabled(False)
        self.combo_ports.setEnabled(False)

    def update_sensor_list(self, current_data: Dict[str, float]):
        """
        Zavolá se při každém příjmu dat. Pokud objevíme nový senzor, přidáme ho do seznamu.
        """
        for key in current_data.keys():
            if key not in self._known_sensors:
                self._known_sensors.add(key)
                self._add_sensor_item(key)

    def clear_sensors(self):
        self.sensor_list.clear()
        self._known_sensors.clear()

    # --- Interní logiky ---

    def _add_sensor_item(self, key: str):
        pretty_name = RealtimePlotWidget.format_sensor_name(key)
        item = QListWidgetItem(pretty_name)
        item.setData(Qt.UserRole, key) # Uložíme si raw klíč (např T_DS0)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        self.sensor_list.addItem(item)

    # --- Handlery tlačítek (převod na signály) ---

    def _on_connect_click(self):
        port = self.combo_ports.currentText()
        if port:
            self.connect_requested.emit(port)

    def _on_disconnect_click(self):
        self.disconnect_requested.emit()

    def _on_start_click(self):
        m_type = self.combo_type.currentText()
        self.start_measurement_clicked.emit(m_type)

    def _on_stop_click(self):
        self.stop_measurement_clicked.emit()

    def _on_item_changed(self, item):
        key = item.data(Qt.UserRole)
        is_visible = (item.checkState() == Qt.Checked)
        self.sensor_visibility_changed.emit(key, is_visible)