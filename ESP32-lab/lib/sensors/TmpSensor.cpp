#include "TmpSensor.h"

bool TmpSensor::begin() {
    // Adafruit TMP117 má defaultně adresu 0x48.
    // Zkusíme ji inicializovat.
    if (!tmp117.begin(0x48)) {
        // Pokud to selže, zkusíme to bez adresy (knihovna zkusí defaultní)
        // a vypíšeme chybu do Serial (pokud je inicializovaný v main.cpp)
        return tmp117.begin();
    }
    return true;
}

float TmpSensor::readTemperatureC() {
    sensors_event_t temp;
    tmp117.getEvent(&temp);
    return temp.temperature;
}