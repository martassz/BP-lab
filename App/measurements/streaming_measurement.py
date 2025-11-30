import threading
import time
from typing import Optional

from measurements.base import BaseMeasurement
from core.parser import parse_json_message, extract_data_values


class StreamingTempMeasurement(BaseMeasurement):
    """
    Měření přes JSON protokol.
    Start: Pošle "SET RATE" a pak "START".
    Stop: Pošle "STOP".
    Data: Parsuje JSON, posílá do grafu a UKLÁDÁ PRO EXPORT.
    """

    DURATION_S = 10.0
    SAMPLE_RATE_HZ = 2.0  # Defaultní frekvence (lze přepsat v potomcích)
    NO_DATA_TIMEOUT_S = 5.0

    def __init__(self, serial_mgr, **kwargs):
        super().__init__(serial_mgr)
        self._stop_flag = False
        self._worker_thread: Optional[threading.Thread] = None
        self._t0_ms: Optional[float] = None
        self._last_data_time = 0.0
        self._last_ping_time = 0.0 
        
        self.recorded_data = []

    def on_start(self):
        """
        Nastaví vzorkovací frekvenci a pošle příkaz START.
        """
        if not self.serial.is_open():
            self.stop()
            return

        self._stop_flag = False
        self.recorded_data = [] 
        
        self._t0_ms = None 
        self._last_data_time = time.time()
        self._last_ping_time = time.time()

        # --- NOVÉ: Odeslání vzorkovací frekvence ---
        if hasattr(self, "SAMPLE_RATE_HZ") and self.SAMPLE_RATE_HZ > 0:
            print(f"Nastavuji vzorkovací frekvenci: {self.SAMPLE_RATE_HZ} Hz")
            self.serial.write_line(f"SET RATE {self.SAMPLE_RATE_HZ}")
            time.sleep(0.1) # Krátká pauza pro zpracování
        # -------------------------------------------

        print("Odesílám příkaz START...")
        self.serial.write_line("START")
        
        self._worker_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._worker_thread.start()

    def on_stop(self):
        self._stop_flag = True
        if self.serial.is_open():
            print("Odesílám příkaz STOP...")
            self.serial.write_line("STOP")

    def handle_line(self, line: str):
        msg = parse_json_message(line)
        if msg is None: return

        if msg.get("type") == "error":
            print(f"-> ESP HLÁSÍ CHYBU: {msg.get('msg')}")
            return
        
        if msg.get("type") == "ack": return

        data = extract_data_values(msg)
        if not data: return

        self._last_data_time = time.time()

        t_ms = msg.get("t_ms")
        if isinstance(t_ms, (int, float)):
            if self._t0_ms is None:
                self._t0_ms = float(t_ms)
            t_s = max(0.0, (float(t_ms) - self._t0_ms) / 1000.0)
        else:
            t_s = self.now_s()

        row = {"t_s": round(t_s, 3), **data}
        self.recorded_data.append(row)

        self.emit_data(t_s, data)

    def _watchdog_loop(self):
        while not self._stop_flag and self.is_running():
            now = time.time()
            elapsed = self.now_s()
            
            self.emit_progress(min(1.0, elapsed / self.DURATION_S))
            
            if now - self._last_ping_time > 1.0:
                self.serial.write_line("PING")
                self._last_ping_time = now

            if (now - self._last_data_time) > self.NO_DATA_TIMEOUT_S:
                # Timeout logic...
                pass
            
            if elapsed >= self.DURATION_S:
                self.stop()
                break
                
            time.sleep(0.1)