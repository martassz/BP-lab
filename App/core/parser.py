from typing import Dict, Optional
import json


def parse_temp_line(line: str) -> Dict[str, float]:
    """
    Legacy textový formát:
      T_BME=24.1234; T_DS0=23.5000; ...
    Vrací dict { "T_BME": 24.1234, "T_DS0": 23.5, ... }
    Hodnoty 'nan' vynechá.
    """
    result: Dict[str, float] = {}

    if "T_BME" not in line:
        # pravděpodobně info text, ne datová zpráva
        return result

    parts = [p.strip() for p in line.split(";") if p.strip()]
    for part in parts:
        if "=" not in part:
            continue
        key, val = [x.strip() for x in part.split("=", 1)]
        if not key:
            continue
        if val.lower() == "nan":
            continue
        try:
            result[key] = float(val.replace(",", "."))
        except ValueError:
            continue

    return result


def parse_json_message(line: str) -> Optional[dict]:
    """
    Pokusí se dekódovat řádek jako JSON objekt.
    Očekává zprávy z SerialProtocol na ESP32.
    """
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    if isinstance(obj, dict):
        return obj
    return None


def extract_data_values(msg: dict) -> Dict[str, float]:
    """
    Z JSON zprávy typu "data" vytáhne numerické hodnoty senzorů.

    Očekávaný tvar:
      {
        "type": "data",
        "t_ms": 12345,
        "T_BME": 24.12,
        "T_DS0": 23.5,
        ...
      }
    """
    if msg.get("type") != "data":
        return {}

    result: Dict[str, float] = {}
    for key, val in msg.items():
        if key in ("type", "t_ms"):
            continue
        if isinstance(val, (int, float)):
            result[key] = float(val)

    return result
