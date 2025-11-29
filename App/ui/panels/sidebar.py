from typing import List
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QComboBox, QPushButton, 
    QProgressBar, QWidget, QSlider, QRadioButton, QButtonGroup, QHBoxLayout
)
from PySide6.QtCore import Signal, Qt

from core.serial_manager import SerialManager

class Sidebar(QFrame):
    # Signály
    connect_requested = Signal(str)
    disconnect_requested = Signal()
    start_measurement_clicked = Signal(str)
    stop_measurement_clicked = Signal()
    sensor_settings_clicked = Signal()
    measurement_type_changed = Signal(str) 
    pwm_changed = Signal(int, int) # (channel, value 0-100)
    export_clicked = Signal()

    def __init__(self, measurement_types: List[str], parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(280) 
        
        # Inicializace referencí na dynamické prvky pro bezpečnost
        self.rb_heater = None
        self.rb_cooler = None
        self.slider_pwm = None # Přidána reference na slider
        
        self._init_ui(measurement_types)

    def _init_ui(self, measurement_types: List[str]):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(15)

        # --- SPOLEČNÝ STYL PRO COMBOBOXY ---
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
                border-left: 2px solid transparent;
                border-right: 2px solid transparent;
                border-top: 5px solid #e0e0e0;
                margin-top: 2px;
                margin-right: 2px;
                width: 0; 
                height: 0;
            }
        """

        # --- PŘIPOJENÍ ---
        self._add_section_label(layout, "PŘIPOJENÍ")
        self.combo_ports = QComboBox()
        self.combo_ports.addItems(SerialManager.list_ports())
        self.combo_ports.setStyleSheet(COMBO_BOX_STYLE)
        layout.addWidget(self.combo_ports)

        self.btn_connect = QPushButton("Připojit k ESP")
        self.btn_connect.setObjectName("BtnConnect")
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.clicked.connect(self._on_connect_click)
        layout.addWidget(self.btn_connect)
        
        layout.addSpacing(10)

        # --- MĚŘENÍ ---
        self._add_section_label(layout, "MĚŘENÍ")
        
        self.combo_type = QComboBox()
        self.combo_type.addItems(measurement_types)
        self.combo_type.setStyleSheet(COMBO_BOX_STYLE)
        self.combo_type.currentTextChanged.connect(self.measurement_type_changed.emit)
        layout.addWidget(self.combo_type)

        self.btn_sensors = QPushButton(" Výběr senzorů")
        self.btn_sensors.setCursor(Qt.PointingHandCursor)
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
        self.btn_sensors.clicked.connect(self.sensor_settings_clicked.emit)
        layout.addWidget(self.btn_sensors)

        layout.addSpacing(5)
        
        # --- DYNAMICKÁ SEKCE ---
        self.dynamic_container = QWidget()
        self.dynamic_layout = QVBoxLayout(self.dynamic_container)
        self.dynamic_layout.setContentsMargins(0, 0, 0, 0)
        self.dynamic_layout.setSpacing(10)
        layout.addWidget(self.dynamic_container)
        
        layout.addSpacing(5)

        # --- START / STOP / EXPORT ---
        self.btn_start = QPushButton("START")
        self.btn_start.setObjectName("BtnStart")
        self.btn_start.setFixedHeight(40)
        self.btn_start.setEnabled(False)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._on_start_click)
        layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setObjectName("BtnStop")
        self.btn_stop.setFixedHeight(40)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.clicked.connect(self._on_stop_click)
        layout.addWidget(self.btn_stop)

        self.btn_export = QPushButton("Exportovat CSV")
        self.btn_export.setStyleSheet("background-color: #d19a66; color: #202020; font-weight: bold;")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_clicked.emit)
        self.btn_export.hide()
        layout.addWidget(self.btn_export)

        layout.addStretch()

        # --- STATUS ---
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

    # --- Metody pro Dynamický Obsah ---

    def clear_dynamic_section(self):
        """Odstraní všechny prvky z dynamické sekce a vyčistí reference"""
        while self.dynamic_layout.count():
            item = self.dynamic_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Vyčistíme reference
        self.rb_heater = None
        self.rb_cooler = None
        self.slider_pwm = None # Reset reference na slider
        
        self.btn_export.hide()

    def show_pwm_controls(self):
        self.clear_dynamic_section()
        
        self._add_section_label(self.dynamic_layout, "OVLÁDÁNÍ VÝKONU")
        
        # Radio buttons
        rb_container = QWidget()
        rb_layout = QVBoxLayout(rb_container)
        rb_layout.setContentsMargins(0,0,0,0)
        
        self.rb_heater = QRadioButton("Topení (Rezistor)")
        self.rb_heater.setStyleSheet("color: #e0e0e0;")
        self.rb_heater.setChecked(True)
        
        self.rb_cooler = QRadioButton("Chlazení (Peltier)")
        self.rb_cooler.setStyleSheet("color: #e0e0e0;")
        
        self.actuator_group = QButtonGroup(self)
        self.actuator_group.addButton(self.rb_heater, 0)
        self.actuator_group.addButton(self.rb_cooler, 1)
        self.actuator_group.idToggled.connect(self._on_actuator_mode_changed)

        rb_layout.addWidget(self.rb_heater)
        rb_layout.addWidget(self.rb_cooler)
        self.dynamic_layout.addWidget(rb_container)
        
        # Slider
        self.lbl_pwm_val = QLabel("Výkon: 0 %")
        self.lbl_pwm_val.setStyleSheet("color: #aaaaaa;")
        self.dynamic_layout.addWidget(self.lbl_pwm_val)
        
        self.slider_pwm = QSlider(Qt.Horizontal)
        self.slider_pwm.setRange(0, 100)
        self.slider_pwm.setValue(0)
        self.slider_pwm.setTickPosition(QSlider.TicksBelow)
        self.slider_pwm.setTickInterval(10)
        self.slider_pwm.valueChanged.connect(self._on_pwm_slider_changed)
        
        self.dynamic_layout.addWidget(self.slider_pwm)
        self.btn_export.show()

    def show_simple_controls(self):
        self.clear_dynamic_section()
        self.btn_export.show()

    # --- Handlery ---

    def _on_pwm_slider_changed(self, val):
        self.lbl_pwm_val.setText(f"Výkon: {val} %")
        channel = self.actuator_group.checkedId()
        self.pwm_changed.emit(channel, val)

    def _on_actuator_mode_changed(self, btn_id, checked):
        if checked:
            self.slider_pwm.setValue(0) 

    def _add_section_label(self, layout, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #007acc; font-weight: bold; letter-spacing: 1.2px; font-size: 11px;")
        layout.addWidget(lbl)

    # --- Původní metody ---
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
            try: self.btn_connect.clicked.disconnect()
            except: pass
            self.btn_connect.clicked.connect(self._on_disconnect_click)
            self.btn_start.setEnabled(True)
            self.lbl_status.setText("Připojeno k ESP32")
            self.btn_connect.setEnabled(True)
        else:
            self.btn_connect.setText("Připojit k ESP")
            self.btn_connect.setStyleSheet("")
            self.combo_ports.setEnabled(True)
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(False)
            try: self.btn_connect.clicked.disconnect()
            except: pass
            self.btn_connect.clicked.connect(self._on_connect_click)
            self.lbl_status.setText("Odpojeno")
            self.btn_connect.setEnabled(True)

    def set_measurement_running(self, running: bool):
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.combo_type.setEnabled(not running)
        self.btn_sensors.setEnabled(not running)
        
        # --- ZMĚNA: Zablokování PWM ovládání ---
        # Bezpečné ovládání Radio Buttonů a Slideru
        try:
            if self.rb_heater and not self.rb_heater.isHidden():
                self.rb_heater.setEnabled(not running)
            if self.rb_cooler and not self.rb_cooler.isHidden():
                self.rb_cooler.setEnabled(not running)
            if self.slider_pwm and not self.slider_pwm.isHidden():
                self.slider_pwm.setEnabled(not running)
        except RuntimeError:
            # Widgety byly smazány C++ stranou, ale Python reference ještě žije
            pass
        
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