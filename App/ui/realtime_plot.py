from typing import Dict, List
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
import pyqtgraph as pg

# Čistý import z centrálního souboru
from core.sensors import get_sensor_name

class RealtimePlotWidget(QWidget):
    def __init__(self, time_window_s: float = 60.0, parent=None):
        super().__init__(parent)

        pg.setConfigOption('foreground', 'w') 
        pg.setConfigOption('background', '#202020')
        pg.setConfigOptions(antialias=True)

        self._time_window = time_window_s
        
        # Slovníky pro data a křivky
        self._curves: Dict[str, pg.PlotDataItem] = {}
        self._data_x: Dict[str, List[float]] = {}
        self._data_y: Dict[str, List[float]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 20, 10) 

        self._plot_widget = pg.PlotWidget()
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)

        self._plot_item = self._plot_widget.getPlotItem()
        self._plot_item.setClipToView(True) 
        
        label_style = {"color": "#e0e0e0", "font-size": "14px", "font-weight": "bold"}
        self._plot_item.setLabel("bottom", "Čas [s]", **label_style)
        self._plot_item.setLabel("left", "Teplota [°C]", **label_style)
        
        self._plot_widget.setMouseEnabled(x=False, y=False)
        self._plot_widget.hideButtons()
        
        # Nastavení výchozího rozsahu osy X
        self._plot_widget.setXRange(0, self._time_window, padding=0.02)

        # --- Druhá osa Y (Napětí) ---
        self._view_voltage = pg.ViewBox()
        self._view_voltage.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
        self._plot_item.scene().addItem(self._view_voltage)
        self._plot_item.getAxis('right').linkToView(self._view_voltage)
        self._view_voltage.setXLink(self._plot_item)
        
        voltage_axis_style = dict(label_style)
        voltage_axis_style["color"] = "#ffffff"
        self._plot_item.getAxis('right').setLabel("Napětí [mV]", **voltage_axis_style)
        
        self._plot_item.vb.sigResized.connect(self._update_views)
        
        self._plot_item.showAxis('right', False)
        self._dual_axis_enabled = False

        # --- Legenda ---
        self._legend = self._plot_item.addLegend(offset=(10, 10))
        self._legend.setBrush(pg.mkBrush(0, 0, 0, 150))
        self._legend.setLabelTextColor("#FFFFFF")

        layout.addWidget(self._plot_widget)

    def set_dual_axis_mode(self, enabled: bool):
        self._dual_axis_enabled = enabled
        self._plot_item.showAxis('right', enabled)
        self._update_views()

    def _update_views(self):
        self._view_voltage.setGeometry(self._plot_item.vb.sceneBoundingRect())
        self._view_voltage.linkedViewChanged(self._plot_item.vb, self._view_voltage.XAxis)

    def clear(self):
        """Kompletní vyčištění grafu."""
        self._plot_item.clear() 
        self._view_voltage.clear()
        self._curves.clear()
        self._data_x.clear()
        self._data_y.clear()

        # Reset legendy
        if self._legend:
            try:
                if self._legend.scene():
                    self._legend.scene().removeItem(self._legend)
            except Exception:
                pass
            
            self._legend = self._plot_item.addLegend(offset=(10, 10))
            self._legend.setBrush(pg.mkBrush(0, 0, 0, 150))
            self._legend.setLabelTextColor("#FFFFFF")

        self._plot_widget.setXRange(0, self._time_window, padding=0.02)

    def add_point(self, t_s: float, values: Dict[str, float]):
        current_max_time = 0.0

        for sensor_key, val in values.items():
            # Pokud křivka pro daný senzor neexistuje, vytvoříme ji
            if sensor_key not in self._curves:
                self._create_curve(sensor_key)

            self._data_x[sensor_key].append(t_s)
            self._data_y[sensor_key].append(val)
            current_max_time = max(current_max_time, t_s)

        for sensor_key, curve in self._curves.items():
            xs = self._data_x[sensor_key]
            ys = self._data_y[sensor_key]
            if not xs: continue
            
            # Bez scrollingu - data se jen přidávají a graf se natahuje
            curve.setData(xs, ys)

        # Osa X - roztahování
        view_max = max(self._time_window, current_max_time)
        self._plot_widget.setXRange(0, view_max, padding=0.02)

        # Auto-scale pro Y osy
        temp_vals = []
        volt_vals = []
        for key, ys in self._data_y.items():
            if not ys: continue
            
            is_voltage = key.startswith("V_") or key.startswith("ADC") or key.startswith("ESP")
            if is_voltage:
                volt_vals.extend(ys)
            else:
                temp_vals.extend(ys)

        if temp_vals:
            mi, ma = min(temp_vals), max(temp_vals)
            diff = ma - mi if ma != mi else 1.0
            self._plot_item.setYRange(mi - diff*0.1, ma + diff*0.1, padding=0.02)
        
        if self._dual_axis_enabled and volt_vals:
            mi, ma = min(volt_vals), max(volt_vals)
            diff = ma - mi if ma != mi else 1.0
            self._view_voltage.setYRange(mi - diff*0.1, ma + diff*0.1, padding=0.02)

    def set_time_window(self, seconds: float):
        if seconds <= 0: return
        self._time_window = seconds

    def _create_curve(self, key: str):
        # Použití centrální funkce
        pretty_name = get_sensor_name(key)
        
        color = self._assign_color(len(self._curves))
        
        self._data_x[key] = []
        self._data_y[key] = []

        use_right_axis = self._dual_axis_enabled and (
            key.startswith("V_") or key.startswith("ADC") or key.startswith("ESP")
        )
        
        if self._dual_axis_enabled:
            if use_right_axis:
                pen = pg.mkPen(color=color, width=2, style=Qt.SolidLine)
                symbol = 'o'
                sym_size = 5
            else:
                pen = pg.mkPen(color=color, width=2, style=Qt.DashLine)
                symbol = 'x'
                sym_size = 7
        else:
            pen = pg.mkPen(color=color, width=2, style=Qt.SolidLine)
            symbol = 'x'
            sym_size = 7

        if use_right_axis:
            # Křivka pro druhou osu (manuální přidání do legendy)
            curve = pg.PlotDataItem(
                name=pretty_name, pen=pen, symbol=symbol, symbolSize=sym_size, symbolBrush=color, antialias=True
            )
            self._view_voltage.addItem(curve)
            
            if self._legend:
                self._legend.addItem(curve, pretty_name)
        else:
            # Křivka pro hlavní osu (automatická legenda)
            curve = self._plot_widget.plot(
                name=pretty_name, pen=pen, symbol=symbol, symbolSize=sym_size, symbolBrush=color, antialias=True
            )
        
        self._curves[key] = curve

    def _assign_color(self, index: int):
        colors = [
            "#00FF00", "#FF4500", "#00FFFF", "#FFFF00", 
            "#FF00FF", "#1E90FF", "#FFFFFF", "#FFA500"
        ]
        return pg.mkColor(colors[index % len(colors)])