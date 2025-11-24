import threading
import time
from typing import Optional

from measurements.base import BaseMeasurement
from core.parser import parse_json_message, extract_data_values


class StreamingTempMeasurement(BaseMeasurement):
    """
    Měření přes JSON protokol.
    Start: Pošle "START".
    Stop: Pošle "STOP".
    Data: Parsuje JSON a posílá do grafu.
    """

    DURATION_S = 10.0  # Délka měření v sekundách
    NO_DATA_TIMEOUT_S = 5.0

    def __init__(self, serial_mgr):
        super().__init__(serial_mgr)
        self._stop_flag = False
        self._worker_thread: Optional[threading.Thread] = None
        self._t0_ms: Optional[float] = None
        self._last_data_time = 0.0

    def on_start(self):
        """
        Volá se, když uživatel klikne na tlačítko START.
        Zde skutečně posíláme příkaz do ESP.
        """
        if not self.serial.is_open():
            self.stop()
            return

        self._stop_flag = False
        self._t0_ms = None
        self._last_data_time = time.time()

        # === ZDE SE DĚJE STARTOVÁNÍ MĚŘENÍ ===
        print("Odesílám příkaz START...")
        self.serial.write_line("START")
        
        # Spustíme hlídacího psa (watchdog), který kontroluje timeouty
        self._worker_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._worker_thread.start()

    def on_stop(self):
        """
        Volá se při stisku STOP nebo po uplynutí času.
        """
        self._stop_flag = True
        if self.serial.is_open():
            print("Odesílám příkaz STOP...")
            self.serial.write_line("STOP")

    def handle_line(self, line: str):
        """
        Zpracovává řádky během běžícího měření.
        """
        # --- DIAGNOSTIKA START ---
        clean_line = line.strip()
        print(f"RAW DATA Z ESP: '{clean_line}'") # Uvidíme přesně, co chodí
        # --- DIAGNOSTIKA END ---

        # 1. Parsování JSON
        msg = parse_json_message(line)
        
        # Pokud parsování selhalo (msg je None), vypíšeme proč
        if msg is None:
            if clean_line: # Ignorujeme prázdné řádky
                print("-> Chyba: Toto není platný JSON!")
            return

        # Pokud je to potvrzení příkazu
        if msg.get("type") == "ack":
            print(f"-> ESP POTVRDILO PŘÍKAZ: {msg.get('cmd')}")
            return
        
        if msg.get("type") == "error":
            print(f"-> ESP HLÁSÍ CHYBU: {msg.get('msg')}")
            return

        # 2. Extrakce dat
        data = extract_data_values(msg)
        
        # Pokud se nepovedlo vytáhnout data
        if not data:
            print(f"-> JSON OK, ale žádná data k vykreslení. Obsah: {msg}")
            return

        # Data přišla, aktualizujeme čas watchdogu
        self._last_data_time = time.time()

        # 3. Výpočet času pro graf
        t_ms = msg.get("t_ms")
        if isinstance(t_ms, (int, float)):
            if self._t0_ms is None:
                self._t0_ms = float(t_ms)
            t_s = max(0.0, (float(t_ms) - self._t0_ms) / 1000.0)
        else:
            t_s = self.now_s()

        # 4. Odeslání do UI
        print(f"-> DATA OK: Čas={t_s:.2f}s, Hodnoty={data}")
        self.emit_data(t_s, data)

    def _watchdog_loop(self):
        while not self._stop_flag and self.is_running():
            now = time.time()
            
            # Aktualizace Progress baru
            elapsed = self.now_s()
            self.emit_progress(min(1.0, elapsed / self.DURATION_S))
            
            # Timeout detekce (pokud data dlouho nechodí)
            if (now - self._last_data_time) > self.NO_DATA_TIMEOUT_S:
                print(f"TIMEOUT: Žádná data více než {self.NO_DATA_TIMEOUT_S}s!")
                # self.stop() # Volitelné: automaticky zastavit měření
            
            # Konec měření po uplynutí času
            if elapsed >= self.DURATION_S:
                self.stop()
                break
                
            time.sleep(0.1)