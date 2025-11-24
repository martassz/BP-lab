from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QCheckBox, QPushButton, 
    QLabel, QHBoxLayout, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from typing import Set

class SensorConfigDialog(QDialog):
    def __init__(self, allowed_sensors: Set[str], parent=None):
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

        # Uložíme si, co bylo povoleno při otevření
        self.result_sensors = set(allowed_sensors)
        self._checkboxes = {}

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        lbl = QLabel("Vyberte senzory, které chcete zobrazovat a ukládat.\nOstatní data budou ignorována.")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        
        # Scroll area pro seznam senzorů
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #252526; border: 1px solid #3e3e42; border-radius: 4px;")
        
        container = QWidget()
        self.checks_layout = QVBoxLayout(container)
        self.checks_layout.setSpacing(5)
        
        # --- DEFINICE ZNÁMÝCH SENZORŮ ---
        # Tady definujeme to, co "víme předem"
        known_sensors = [
            ("T_BME", "Teplota Vzduchu (BME280)"),
            ("T_DS0", "Senzor DS18B20 #1"),
            ("T_DS1", "Senzor DS18B20 #2"),
            ("T_DS2", "Senzor DS18B20 #3"),
            ("T_DS3", "Senzor DS18B20 #4"),
        ]

        for key, name in known_sensors:
            cb = QCheckBox(name)
            # Pokud je senzor v povolených (nebo je list prázdný = vše povoleno), zaškrtneme
            is_checked = (not self.result_sensors) or (key in self.result_sensors)
            cb.setChecked(is_checked)
            self.checks_layout.addWidget(cb)
            self._checkboxes[key] = cb

        self.checks_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Tlačítka
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Uložit a Zavřít")
        btn_save.clicked.connect(self.accept) # Zavře dialog s výsledkem Accepted
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)

    def get_allowed_sensors(self) -> Set[str]:
        """Vrátí set klíčů (např. {'T_BME', 'T_DS0'}), které jsou zaškrtnuté"""
        allowed = set()
        for key, cb in self._checkboxes.items():
            if cb.isChecked():
                allowed.add(key)
        return allowed