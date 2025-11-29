from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QCheckBox, QPushButton, 
    QLabel, QHBoxLayout, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from typing import Set, List, Dict

class SensorConfigDialog(QDialog):
    # ZDE BYLA CHYBA: Chyběl parametr available_sensors v __init__
    def __init__(self, allowed_sensors: Set[str], available_sensors: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Výběr aktivních senzorů")
        self.setFixedSize(350, 450)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #e0e0e0; }
            QCheckBox { spacing: 10px; font-size: 14px; padding: 5px; }
            QCheckBox::indicator { width: 18px; height: 18px; }
            QPushButton { 
                padding: 8px; background-color: #007acc; color: white; border-radius: 4px; border: none; font-weight: bold;
            }
            QPushButton:hover { background-color: #0098ff; }
            QLabel { color: #aaaaaa; }
        """)

        self.result_sensors = set(allowed_sensors)
        self.available_sensors = available_sensors # Seznam klíčů (např. ["T_BME", "T_DS0"...])
        self._checkboxes = {}

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        lbl = QLabel("Vyberte senzory pro zobrazení a logování.\nZobrazují se pouze senzory detekované ESP32.")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #252526; border: 1px solid #3e3e42; border-radius: 4px;")
        
        container = QWidget()
        self.checks_layout = QVBoxLayout(container)
        self.checks_layout.setSpacing(5)
        
        # Mapa hezkých názvů
        PRETTY_NAMES = {
            "T_BME": "Teplota Vzduchu (BME280)",
            "T_TMP": "Referenční (TMP117)",
            "ADC_R": "Napětí Rezistor (ADC)",
            "ADC_NTC": "Napětí NTC (ADC)",
            "ESP_R": "Napětí Rezistor (ESP)",
            "ESP_NTC": "Napětí NTC (ESP)",
        }

        # Pokud nemáme žádné info (např. chyba komunikace), dáme aspoň default
        sensor_list = self.available_sensors if self.available_sensors else ["T_BME", "T_DS0"]

        for key in sensor_list:
            # Zkusíme najít hezký název, jinak vygenerujeme
            name = PRETTY_NAMES.get(key)
            if not name:
                if key.startswith("T_DS"):
                    idx = key.replace("T_DS", "")
                    name = f"Senzor DS18B20 #{int(idx)+1}"
                else:
                    name = key # Fallback

            cb = QCheckBox(name)
            # Pokud je seznam povolených prázdný, bereme to jako "vše povoleno"
            is_checked = (not self.result_sensors) or (key in self.result_sensors)
            cb.setChecked(is_checked)
            self.checks_layout.addWidget(cb)
            self._checkboxes[key] = cb

        self.checks_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Uložit a Zavřít")
        btn_save.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)

    def get_allowed_sensors(self) -> Set[str]:
        allowed = set()
        for key, cb in self._checkboxes.items():
            if cb.isChecked():
                allowed.add(key)
        return allowed