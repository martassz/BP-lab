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

    DURATION_S = 10.0  # Délka měření v sekundách (pro progress bar)
    NO_DATA_TIMEOUT_S = 5.0

    def __init__(self, serial_mgr):
        super().__init__(serial_mgr)
        self._stop_flag = False
        self._worker_thread: Optional[threading.Thread] = None
        self._t0_ms: Optional[float] = None
        self._last_data_time = 0.0
        # Čas posledního odeslaného pingu (pro heartbeat)
        self._last_ping_time = 0.0 

    def on_start(self):
        """
        Volá se, když uživatel klikne na tlačítko START.
        """
        if not self.serial.is_open():
            self.stop()
            return

        self._stop_flag = False
        
        # --- RESET ČASOVAČE ---
        # Zajistí, že graf začne kreslit od 0.0s při každém startu
        self._t0_ms = None 
        
        self._last_data_time = time.time()
        self._last_ping_time = time.time()

        print("Odesílám příkaz START...")
        self.serial.write_line("START")
        
        # Spustíme hlídacího psa ve vedlejším vlákně
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
        Zpracovává řádky (JSON) během běžícího měření.
        """
        # 1. Parsování JSON
        msg = parse_json_message(line)
        if msg is None:
            return

        # Pokud je to chyba, vypíšeme ji
        if msg.get("type") == "error":
            print(f"-> ESP HLÁSÍ CHYBU: {msg.get('msg')}")
            return
        
        # Ignorujeme potvrzovací zprávy (ACK)
        if msg.get("type") == "ack":
            return

        # 2. Extrakce dat
        data = extract_data_values(msg)
        if not data:
            return

        # Data přišla, aktualizujeme čas posledních dat (pro timeout)
        self._last_data_time = time.time()

        # 3. Výpočet času pro graf
        # Klíčová logika pro relativní čas od nuly
        t_ms = msg.get("t_ms")
        
        if isinstance(t_ms, (int, float)):
            # První vzorek v měření určí "nulu"
            if self._t0_ms is None:
                self._t0_ms = float(t_ms)
            
            # Čas od začátku měření v sekundách
            t_s = max(0.0, (float(t_ms) - self._t0_ms) / 1000.0)
        else:
            # Fallback (nemělo by nastat, pokud ESP funguje správně)
            t_s = self.now_s()

        # 4. Odeslání do UI (grafu a kartiček)
        self.emit_data(t_s, data)

    def _watchdog_loop(self):
        """
        Běží na pozadí:
        - hlídá čas (progress bar)
        - posílá PING (heartbeat)
        - hlídá timeout (ztráta spojení)
        """
        while not self._stop_flag and self.is_running():
            now = time.time()
            elapsed = self.now_s()
            
            # Aktualizace Progress baru v UI
            self.emit_progress(min(1.0, elapsed / self.DURATION_S))
            
            # --- PING (HEARTBEAT) ---
            # Posíláme PING každou 1 sekundu, aby ESP vědělo, že žijeme
            if now - self._last_ping_time > 1.0:
                self.serial.write_line("PING")
                self._last_ping_time = now
            # ------------------------

            # Detekce Timeoutu (pokud dlouho nepřišla data)
            if (now - self._last_data_time) > self.NO_DATA_TIMEOUT_S:
                # Zde bychom mohli měření zastavit, zatím jen logujeme
                # print(f"TIMEOUT: Žádná data více než {self.NO_DATA_TIMEOUT_S}s!")
                pass
            
            # Automatický konec po uplynutí doby měření
            if elapsed >= self.DURATION_S:
                self.stop()
                break
                
            time.sleep(0.1)