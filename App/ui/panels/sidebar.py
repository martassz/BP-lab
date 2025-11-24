from typing import List
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QComboBox, QPushButton, 
    QProgressBar, QWidget
)
from PySide6.QtCore import Signal, Qt

from core.serial_manager import SerialManager

class Sidebar(QFrame):
    # Signály pro komunikaci s hlavním oknem
    connect_requested = Signal(str)
    disconnect_requested = Signal()
    start_measurement_clicked = Signal(str)
    stop_measurement_clicked = Signal()
    sensor_settings_clicked = Signal()  

    def __init__(self, measurement_types: List[str], parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(260) 
        
        self._init_ui(measurement_types)

    def _init_ui(self, measurement_types: List[str]):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(15)

        # --- SPOLEČNÝ STYL PRO COMBOBOXY ---
        # Definujeme ho zde, abychom ho použili pro oba prvky stejně.
        # Ta "tečka" je definována v sekci ::down-arrow pomocí border triku nebo image.
        COMBO_BOX_STYLE = """
            QComboBox {
                background-color: #333337;
                border: 1px solid #505050;
                padding: 5px;
                border-radius: 4px;
                color: white;
            }
            QComboBox:hover { border: 1px solid #007acc; }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 1px;
                border-left-color: #505050;
                border-left-style: solid; 
            }
            QComboBox::down-arrow {
                /* Tady se kreslí ta šipka/tečka */
                border-left: 2px solid transparent;
                border-right: 2px solid transparent;
                border-top: 5px solid #e0e0e0; /* Barva šipky */
                margin-top: 2px;
                margin-right: 2px;
                width: 0; 
                height: 0;
            }
        """

        # --- SEKCE PŘIPOJENÍ ---
        self._add_section_label(layout, "PŘIPOJENÍ")

        self.combo_ports = QComboBox()
        self.combo_ports.addItems(SerialManager.list_ports())
        self.combo_ports.setStyleSheet(COMBO_BOX_STYLE) # Použití stylu
        layout.addWidget(self.combo_ports)

        self.btn_connect = QPushButton("Připojit k ESP")
        self.btn_connect.setObjectName("BtnConnect")
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.clicked.connect(self._on_connect_click)
        layout.addWidget(self.btn_connect)

        layout.addSpacing(20)

        # --- SEKCE MĚŘENÍ ---
        self._add_section_label(layout, "MĚŘENÍ")

        self.combo_type = QComboBox()
        self.combo_type.addItems(measurement_types)
        self.combo_type.setStyleSheet(COMBO_BOX_STYLE) # Použití stejného stylu i zde
        layout.addWidget(self.combo_type)

        # Tlačítko pro výběr senzorů
        self.btn_sensors = QPushButton(" Výběr senzorů")
        self.btn_sensors.setStyleSheet("""
            QPushButton {
                background-color: #3e3e42;
                border: 1px solid #505050;
                color: #e0e0e0;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:hover { background-color: #505050; border: 1px solid #007acc;}
        """)
        self.btn_sensors.setCursor(Qt.PointingHandCursor)
        self.btn_sensors.clicked.connect(self.sensor_settings_clicked.emit)
        layout.addWidget(self.btn_sensors)

        layout.addSpacing(10)

        # START / STOP
        self.btn_start = QPushButton("START")
        self.btn_start.setObjectName("BtnStart")
        self.btn_start.setFixedHeight(45)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._on_start_click)
        layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setObjectName("BtnStop")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_click)
        layout.addWidget(self.btn_stop)

        layout.addStretch()

        # --- INFO / PROGRESS ---
        self.lbl_status = QLabel("Připraveno")
        self.lbl_status.setStyleSheet("color: #808080; font-size: 11px;")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_status)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet("border: none; background-color: #3e3e42;")
        layout.addWidget(self.progress)

    def _add_section_label(self, layout, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #007acc; font-weight: bold; letter-spacing: 1.2px; font-size: 11px;")
        layout.addWidget(lbl)

    # --- Veřejné metody ---

    def update_ports(self):
        current = self.combo_ports.currentText()
        self.combo_ports.clear()
        self.combo_ports.addItems(SerialManager.list_ports())
        self.combo_ports.setCurrentText(current)

    def set_connected_state(self, connected: bool):
        if connected:
            self.btn_connect.setText("ODPOJIT")
            self.btn_connect.setStyleSheet("background-color: #da3633; color: white;")
            self.combo_ports.setEnabled(False)
            self.btn_connect.clicked.disconnect()
            self.btn_connect.clicked.connect(self._on_disconnect_click)
            self.btn_start.setEnabled(True)
            self.lbl_status.setText("Připojeno k ESP32")
            self.btn_connect.setEnabled(True) 
        else:
            self.btn_connect.setText("Připojit k ESP")
            self.btn_connect.setStyleSheet("")
            
            self.btn_connect.setEnabled(True)
            self.combo_ports.setEnabled(True)
            
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(False)
            try: self.btn_connect.clicked.disconnect()
            except: pass
            self.btn_connect.clicked.connect(self._on_connect_click)
            self.lbl_status.setText("Odpojeno")

    def set_measurement_running(self, running: bool):
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.combo_type.setEnabled(not running)
        self.btn_sensors.setEnabled(not running)
        
        if running:
            self.lbl_status.setText("Měření probíhá...")
            self.lbl_status.setStyleSheet("color: #2ea043; font-size: 11px;")
        else:
            self.lbl_status.setText("Připraveno")
            self.lbl_status.setStyleSheet("color: #808080; font-size: 11px;")

    def set_waiting_state(self):
        self.btn_connect.setText("Čekám...")
        self.btn_connect.setEnabled(False)
        self.combo_ports.setEnabled(False)

    # --- Handlery ---

    def _on_connect_click(self):
        port = self.combo_ports.currentText()
        if port: self.connect_requested.emit(port)

    def _on_disconnect_click(self):
        self.disconnect_requested.emit()

    def _on_start_click(self):
        m_type = self.combo_type.currentText()
        self.start_measurement_clicked.emit(m_type)

    def _on_stop_click(self):
        self.stop_measurement_clicked.emit()