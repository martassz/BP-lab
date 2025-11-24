#include "DallasSensor.h"

DallasBus::DallasBus(uint8_t dataPin)
    : pin(dataPin),
      oneWire(dataPin),
      sensors(&oneWire)
{
}

void DallasBus::begin() {
    sensors.begin();

    uint8_t count = sensors.getDeviceCount();
    if (count > MAX_SENSORS) {
        count = MAX_SENSORS;
    }

    sensorCount = 0;

    for (uint8_t i = 0; i < count; ++i) {
        DeviceAddress addr;
        if (readAddress(i, addr)) {
            memcpy(addresses[sensorCount], addr, sizeof(DeviceAddress));
            sensorCount++;
        }
    }
}

bool DallasBus::readAddress(uint8_t index, DeviceAddress &addr) {
    if (!sensors.getAddress(addr, index)) {
        return false;
    }
    // Volitelně: můžeš si ověřit, že je to opravdu DS18B20 (family code 0x28)
    if (addr[0] != 0x28) {
        return false;
    }
    return true;
}

float DallasBus::getTemperatureC(uint8_t index) {
    if (index >= sensorCount || sensorCount == 0) {
        return NAN;
    }

    sensors.requestTemperatures();
    float t = sensors.getTempC(addresses[index]);

    if (t <= -127.0f) {
        return NAN;
    }
    return t;
}
