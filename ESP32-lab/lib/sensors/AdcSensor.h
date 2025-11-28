#pragma once
#include <Arduino.h>
#include <Adafruit_ADS1X15.h>

class AdcSensor {
public:
    // --- KONFIGURACE KANÁLŮ ---
    // Piny pro interní ADC (ESP32)
    static const uint8_t PIN_ESP_RESISTOR = 34; 
    static const uint8_t PIN_ESP_NTC      = 35; 

    // Kanály pro externí ADC (ADS1115)
    static const uint8_t ADS_CH_RESISTOR  = 0;  // Vstup A0
    static const uint8_t ADS_CH_NTC       = 1;  // Vstup A1

    bool begin();
    float readAdsMilliVolts(uint8_t channel);
    float readEspMilliVolts(uint8_t pin);

private:
    Adafruit_ADS1115 ads;
};