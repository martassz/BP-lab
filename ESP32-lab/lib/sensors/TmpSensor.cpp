#include "TmpSensor.h"

bool TmpSensor::begin() {
    return tmp117.begin();
}

float TmpSensor::readTemperatureC() {
    sensors_event_t temp;
    tmp117.getEvent(&temp);
    return temp.temperature;
}