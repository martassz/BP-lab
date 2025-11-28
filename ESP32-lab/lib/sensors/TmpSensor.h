#pragma once
#include <Adafruit_TMP117.h>

class TmpSensor {
public:
    bool begin();
    float readTemperatureC();

private:
    Adafruit_TMP117 tmp117;
};