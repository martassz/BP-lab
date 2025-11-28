#pragma once
#include <Arduino.h>

class ActuatorController {
public:
    // Piny pro LR7843 (PWM)
    static const uint8_t PIN_HEATER = 18;
    static const uint8_t PIN_COOLER = 19;

    // PWM kanály (ESP32 LEDC)
    static const uint8_t CH_HEATER = 0;
    static const uint8_t CH_COOLER = 1;

    // Inicializace PWM
    void begin();

    // Nastavení výkonu topení 0-100% (vypne chlazení)
    void setHeater(float percent);

    // Nastavení výkonu chlazení 0-100% (vypne topení)
    void setCooler(float percent);

    // Vypne vše
    void stopAll();
};