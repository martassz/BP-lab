import time
from measurements.streaming_measurement import StreamingTempMeasurement

class PartOneMeasurement(StreamingTempMeasurement):
    DISPLAY_NAME = "Část 1: Odporové snímače"
    DURATION_S = 3600.0 
    SAMPLE_RATE_HZ = 1.0

    def __init__(self, serial_mgr, pwm_channel=0, pwm_value=0):
        # Předáme kwargs dál (i když zde je explicitně pwm_channel)
        super().__init__(serial_mgr)
        
        self._pwm_channel = pwm_channel
        self._pwm_value = pwm_value
        
        # Poznámka: self.recorded_data se inicializuje už v StreamingTempMeasurement

    def on_start(self):
        """
        Specifická logika pro start Části 1:
        Nastavíme PWM a pak pustíme standardní měření.
        """
        if self.serial.is_open():
            print(f"PartOne: Nastavuji PWM CH{self._pwm_channel} -> {self._pwm_value}%")
            self.serial.write_line(f"SET PWM {self._pwm_channel} {self._pwm_value}")
            time.sleep(0.1)
            
        super().on_start()