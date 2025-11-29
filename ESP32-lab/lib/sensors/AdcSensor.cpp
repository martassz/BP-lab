#include "AdcSensor.h"

bool AdcSensor::begin() {
    analogReadResolution(12); // ESP32 interně 12 bitů
    
    if (!ads.begin(0x49)) {
        return false;
    }
    // GAIN_TWOTHIRDS: +/- 6.144V (1 bit = 0.1875 mV)
    ads.setGain(GAIN_TWOTHIRDS);
    return true;
}

float AdcSensor::readAdsMilliVolts(uint8_t channel) {
    int16_t raw = ads.readADC_SingleEnded(channel);
    // computeVolts vrací V, násobíme 1000 na mV
    return ads.computeVolts(raw) * 1000.0f;
}

float AdcSensor::readEspMilliVolts(uint8_t pin) {
    // Vrací kalibrovanou hodnotu v mV
    return (float)analogReadMilliVolts(pin);
}