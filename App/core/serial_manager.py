import threading
import time
from typing import Callable, Optional, List

import serial
from serial.tools import list_ports


class SerialManager:
    def __init__(self):
        self._ser: Optional[serial.Serial] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self._line_callback: Optional[Callable[[str], None]] = None

    @staticmethod
    def list_ports() -> List[str]:
        return [p.device for p in list_ports.comports()]

    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def open(self, port: str, baudrate: int = 115200, timeout: float = 0.1):
        self.close()
        
        # 1. Otevření portu
        self._ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)

        # 2. HARD RESET ESP32 (Agresivní metoda ala esptool)
        # Mnoho desek potřebuje specifickou sekvenci DTR/RTS
        self._ser.dtr = False
        self._ser.rts = False
        time.sleep(0.1)
        
        self._ser.dtr = True
        self._ser.rts = True
        time.sleep(0.1)
        
        self._ser.dtr = False
        self._ser.rts = False
        time.sleep(0.2)  # Chvilku počkáme, než ESP nastartuje

        self._start_reader()

    def close(self):
        self._running = False
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
        self._reader_thread = None

        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None

    def set_line_callback(self, cb: Optional[Callable[[str], None]]):
        self._line_callback = cb

    def write(self, data: str):
        if not self.is_open():
            return
        try:
            self._ser.write(data.encode("utf-8"))
        except Exception:
            pass

    def write_line(self, line: str):
        self.write(line + "\n")

    def _start_reader(self):
        if not self._ser:
            return
        self._running = True
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def _reader_loop(self):
        buffer = b""
        while self._running and self._ser and self._ser.is_open:
            try:
                chunk = self._ser.read(128)
                if not chunk:
                    continue
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    text = line.decode(errors="ignore").strip()
                    if text and self._line_callback:
                        self._line_callback(text)
            except Exception:
                # V případě odpojení USB za chodu
                self._running = False
                break