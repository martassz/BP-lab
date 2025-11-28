import csv
from measurements.streaming_measurement import StreamingTempMeasurement

class PartOneMeasurement(StreamingTempMeasurement):
    DISPLAY_NAME = "Část 1: Odporové snímače"
    DURATION_S = 3600.0 

    def __init__(self, serial_mgr):
        super().__init__(serial_mgr)
        self.recorded_data = [] 

    def handle_line(self, line: str):
        super().handle_line(line)
        
        from core.parser import parse_json_message, extract_data_values
        msg = parse_json_message(line)
        if msg and msg.get("type") == "data":
            data = extract_data_values(msg)
            t_ms = msg.get("t_ms", 0)
            if self._t0_ms is None: self._t0_ms = float(t_ms)
            
            t_s = (float(t_ms) - self._t0_ms) / 1000.0
            if t_s < 0: t_s = 0.0
            
            row = {"t_s": round(t_s, 3), **data}
            self.recorded_data.append(row)

    def export_to_csv(self, filename: str) -> bool:
        if not self.recorded_data: return False
        try:
            fieldnames = list(self.recorded_data[0].keys())
            if "t_s" in fieldnames:
                fieldnames.remove("t_s")
                fieldnames.insert(0, "t_s")
            
            with open(filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
                writer.writeheader()
                writer.writerows(self.recorded_data)
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False