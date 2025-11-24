#pragma once

#include <Arduino.h>
#include <Adafruit_BME280.h>

class BmeSensor {
public:
    // Automaticky otestuje běžné adresy (0x76, 0x77)
    bool beginAuto();

    // Volitelně možnost natvrdo zadat adresu
    bool begin(uint8_t i2cAddress);

    float readTemperatureC();   // vrací NAN, pokud není inicializováno
    bool isOk() const { return initialized; }
    uint8_t getAddress() const { return usedAddress; }

private:
    Adafruit_BME280 bme;
    bool initialized = false;
    uint8_t usedAddress = 0;
};
