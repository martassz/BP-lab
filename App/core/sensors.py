from typing import Dict

# Centrální mapa názvů senzorů
# Klíč: Identifikátor v JSONu z ESP32
# Hodnota: Hezký název pro GUI (Legenda, Checkboxy, Kartičky)
SENSOR_NAMES: Dict[str, str] = {
    "T_BME": "BME280",
    "T_TMP": "TMP117",
    
    # ADC (Externí ADS1115)
    "V_ADS_R": "U R (ADC)",
    "V_ADS_NTC": "U NTC (ADC)",
    
    # ADC (Interní ESP32)
    "V_ESP_R": "U R (ESP)",
    "V_ESP_NTC": "U NTC (ESP)",
    
    # Legacy / Fallback názvy (pokud by ESP poslalo starý formát)
    "ADC_R": "U R (ADC)",
    "ADC_NTC": "U NTC (ADC)",
    "ESP_R": "U R (ESP)",
    "ESP_NTC": "U NTC (ESP)",
}

def get_sensor_name(key: str) -> str:
    """
    Vrátí hezký název pro daný klíč senzoru.
    Řeší i dynamické senzory jako DS18B20.
    """
    # 1. Zkusíme přímou shodu v mapě
    if key in SENSOR_NAMES:
        return SENSOR_NAMES[key]
    
    # 2. Dynamické senzory (DS18B20)
    if key.startswith("T_DS"):
        # Očekáváme formát T_DS0, T_DS1...
        try:
            idx = int(key.replace("T_DS", ""))
            return f"Senzor DS18B20 #{idx + 1}"
        except ValueError:
            return key # Fallback
            
    # 3. Pokud neznáme, vrátíme původní klíč
    return key