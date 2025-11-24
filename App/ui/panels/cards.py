from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QFrame, QVBoxLayout, 
    QLabel, QScrollArea
)
from PySide6.QtCore import Qt
from ui.realtime_plot import RealtimePlotWidget

class ValueCardsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(130)
        
        # Interní slovník pro rychlý přístup k labelům: { "T_DS0": QLabel_obj }
        self._labels = {} 

        self._init_ui()

    def _init_ui(self):
        # Hlavní layout tohoto widgetu (aby obsahoval scroll area)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area (aby se kartičky vešly vedle sebe)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("background-color: #1e1e1e; border: none;")
        
        # Kontejner uvnitř Scroll Area
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #1e1e1e;")
        
        # Layout pro kartičky (Horizontální)
        self.cards_layout = QHBoxLayout(self.container)
        self.cards_layout.setContentsMargins(20, 15, 20, 15)
        self.cards_layout.setSpacing(15)
        self.cards_layout.addStretch() # Zarovná kartičky doleva
        
        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)

    def update_values(self, values: dict):
        """
        Aktualizuje hodnoty na kartičkách. Pokud kartička neexistuje, vytvoří ji.
        """
        for key, val in values.items():
            text_val = f"{val:.2f} °C"
            
            if key in self._labels:
                # Aktualizace existující
                self._labels[key].setText(text_val)
            else:
                # Vytvoření nové
                self._create_card(key, text_val)

    def clear(self):
        """Smaže všechny kartičky"""
        # Musíme iterovat pozpátku nebo bezpečně mazat widgety
        while self.cards_layout.count() > 1: # Necháváme tam ten stretch na konci
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._labels.clear()

    def _create_card(self, key: str, initial_text: str):
        pretty_name = RealtimePlotWidget.format_sensor_name(key)

        frame = QFrame()
        frame.setObjectName("ValueCard") # Pro CSS stylování
        frame.setFixedWidth(140)
        
        l = QVBoxLayout(frame)
        l.setContentsMargins(10, 8, 10, 8)
        l.setSpacing(2)
        
        lbl_title = QLabel(pretty_name)
        lbl_title.setObjectName("ValueTitle")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        lbl_val = QLabel(initial_text)
        lbl_val.setObjectName("ValueNumber")
        lbl_val.setAlignment(Qt.AlignCenter)
        
        l.addWidget(lbl_title)
        l.addWidget(lbl_val)
        
        # Uložíme referenci
        self._labels[key] = lbl_val
        
        # Vložíme PŘED stretch (který je na konci seznamu)
        idx = self.cards_layout.count() - 1
        self.cards_layout.insertWidget(idx, frame)