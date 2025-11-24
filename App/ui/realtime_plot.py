from typing import Dict, List

from PySide6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg


class FixedAxis(pg.AxisItem):
    """
    Vlastní osa X, která se snaží vždy zobrazovat 0 a konec (max_time).
    """
    def __init__(self, orientation, max_time: float, parent=None):
        super().__init__(orientation, parent)
        self._max_time = max_time

    def set_max_time(self, max_time: float):
        self._max_time = max_time
        self.picture = None
        self.update()

    def tickValues(self, minVal, maxVal, size):
        max_t = max(self._max_time, 0.0)
        if max_t <= 0:
            return []

        candidates = [0.5, 1, 2, 5, 10, 20, 30, 60, 120, 300, 600]
        step = max_t
        for c in candidates:
            if max_t / c <= 8:
                step = c
                break

        ticks = []
        x = 0.0
        while x <= max_t * 1.1:
            ticks.append(x)
            x += step

        if ticks and abs(ticks[-1] - max_t) > 1e-3:
             ticks.append(max_t)
             
        return [(step, ticks)]

    def tickStrings(self, values, scale, spacing):
        labels = []
        for v in values:
            if abs(v - round(v)) < 1e-6:
                labels.append(str(int(round(v))))
            else:
                labels.append(f"{v:.1f}")
        return labels


class RealtimePlotWidget(QWidget):
    def __init__(self, time_window_s: float = 60.0, parent=None):
        super().__init__(parent)

        # Globální config
        pg.setConfigOption('foreground', 'w') 
        pg.setConfigOption('background', '#202020')
        pg.setConfigOptions(antialias=True)

        self._time_window = time_window_s
        self._curves: Dict[str, pg.PlotDataItem] = {}
        self._data_x: Dict[str, List[float]] = {}
        self._data_y: Dict[str, List[float]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Osa X ---
        self._bottom_axis = FixedAxis("bottom", max_time=self._time_window)
        self._plot_widget = pg.PlotWidget(axisItems={"bottom": self._bottom_axis})
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Popisky os
        label_style = {"color": "#e0e0e0", "font-size": "16px", "font-weight": "bold"}
        self._plot_widget.setLabel("bottom", "Čas [s]", **label_style)
        self._plot_widget.setLabel("left", "Teplota [°C]", **label_style)

        self._plot_widget.setMouseEnabled(x=False, y=False)
        self._plot_widget.hideButtons()

        self._plot_widget.setXRange(0, self._time_window)
        self._plot_widget.enableAutoRange(x=False, y=True)

        self._plot_item = self._plot_widget.getPlotItem()

        # Legenda
        self._legend = self._plot_item.addLegend(offset=(10, 10))
        self._legend.setBrush(pg.mkBrush(0, 0, 0, 150))
        self._legend.setLabelTextColor("#FFFFFF")

        layout.addWidget(self._plot_widget)

    # ---------- Veřejná Statická Metoda (CENTRÁLNÍ MOZEK NÁZVŮ) ----------

    @staticmethod
    def format_sensor_name(key: str) -> str:
        """
        Převede systémový klíč (T_DS0, T_DS5...) na hezký název.
        Toto používá jak graf, tak hlavní okno pro kartičky.
        """
        # 1. BME senzor
        if key in ("T_BME", "T_BME280"):
            return "BME280"
        
        # 2. Dallas senzory (T_DS0 až T_DS999...)
        # Logika je univerzální: vezme číslo za "T_DS" a přičte 1.
        if key.startswith("T_DS"):
            try:
                # Odstraní "T_DS" a zbytek převede na číslo
                idx_str = key.replace("T_DS", "")
                if idx_str.isdigit():
                    idx = int(idx_str)
                    return f"DS18B20 #{idx + 1}"
            except:
                pass
        
        # 3. Pokud neznáme, vrátíme původní klíč
        return key

    # ---------- Veřejné metody ----------

    def clear(self):
        self._plot_item.clear() 
        self._curves.clear()
        self._data_x.clear()
        self._data_y.clear()

        if self._legend:
            self._legend.items = [] 

        self._plot_widget.setXRange(0, self._time_window)
        self._bottom_axis.set_max_time(self._time_window)

    def add_point(self, t_s: float, values: Dict[str, float]):
        current_max_time = 0.0

        for sensor_key, val in values.items():
            if sensor_key not in self._curves:
                self._create_curve(sensor_key)

            self._data_x[sensor_key].append(t_s)
            self._data_y[sensor_key].append(val)
            current_max_time = max(current_max_time, t_s)

        for sensor_key, curve in self._curves.items():
            xs = self._data_x[sensor_key]
            ys = self._data_y[sensor_key]
            
            if not xs: continue

            cutoff = max(0.0, xs[-1] - self._time_window - 5.0)
            while xs and xs[0] < cutoff:
                xs.pop(0)
                ys.pop(0)

            curve.setData(xs, ys)

        if current_max_time > self._time_window:
             self._plot_widget.setXRange(current_max_time - self._time_window, current_max_time)

        self._update_y_range()

    def set_time_window(self, seconds: float):
        if seconds <= 0: return
        self._time_window = seconds
        self._plot_widget.setXRange(0, self._time_window)
        self._bottom_axis.set_max_time(self._time_window)

    # ---------- Pomocné metody ----------

    def _create_curve(self, key: str):
        # ZDE VOLÁME TU NOVOU STATICKOU METODU
        pretty_name = RealtimePlotWidget.format_sensor_name(key)
        
        color = self._assign_color(len(self._curves))
        
        self._data_x[key] = []
        self._data_y[key] = []

        curve = self._plot_widget.plot(
            name=pretty_name,
            pen=pg.mkPen(color=color, width=2),
            symbol='x',         
            symbolSize=7,
            symbolBrush=color,
            antialias=True
        )
        self._curves[key] = curve

    def _update_y_range(self):
        all_vals = []
        for ys in self._data_y.values():
            all_vals.extend(ys)
            
        if not all_vals: return

        y_min = min(all_vals)
        y_max = max(all_vals)
        
        diff = y_max - y_min
        if diff < 1.0: diff = 1.0 
        
        self._plot_widget.setYRange(y_min - diff*0.1, y_max + diff*0.1)

    def _assign_color(self, index: int):
        colors = [
            "#00FF00", "#FF4500", "#00FFFF", "#FFFF00", 
            "#FF00FF", "#1E90FF", "#FFFFFF"
        ]
        return pg.mkColor(colors[index % len(colors)])