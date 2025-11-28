#include "ActuatorController.h"

void ActuatorController::begin() {
    // 1 kHz, 8-bit
    ledcSetup(CH_HEATER, 1000, 8);
    ledcAttachPin(PIN_HEATER, CH_HEATER);

    ledcSetup(CH_COOLER, 1000, 8);
    ledcAttachPin(PIN_COOLER, CH_COOLER);
    
    stopAll();
}

void ActuatorController::setHeater(float percent) {
    if (percent < 0) percent = 0;
    if (percent > 100) percent = 100;
    
    uint32_t duty = (uint32_t)((percent / 100.0f) * 255);
    ledcWrite(CH_COOLER, 0);      // Bezpečnost
    ledcWrite(CH_HEATER, duty);
}

void ActuatorController::setCooler(float percent) {
    if (percent < 0) percent = 0;
    if (percent > 100) percent = 100;

    uint32_t duty = (uint32_t)((percent / 100.0f) * 255);
    ledcWrite(CH_HEATER, 0);      // Bezpečnost
    ledcWrite(CH_COOLER, duty);
}

void ActuatorController::stopAll() {
    ledcWrite(CH_HEATER, 0);
    ledcWrite(CH_COOLER, 0);
}