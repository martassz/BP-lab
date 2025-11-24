#include "BmeSensor.h"

bool BmeSensor::beginAuto() {
    const uint8_t candidates[] = {0x76, 0x77};

    initialized = false;
    usedAddress = 0;

    for (uint8_t addr : candidates) {
        if (bme.begin(addr)) {
            initialized = true;
            usedAddress = addr;
            break;
        }
    }

    return initialized;
}

bool BmeSensor::begin(uint8_t i2cAddress) {
    initialized = bme.begin(i2cAddress);
    if (initialized) {
        usedAddress = i2cAddress;
    } else {
        usedAddress = 0;
    }
    return initialized;
}

float BmeSensor::readTemperatureC() {
    if (!initialized) {
        return NAN;
    }
    // BME280 vrací přímo teplotu v °C
    return bme.readTemperature();
}
