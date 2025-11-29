#include <Arduino.h>
#include <Wire.h>

#include "BmeSensor.h"
#include "DallasSensor.h"
#include "AdcSensor.h"
#include "TmpSensor.h"
#include "SerialProtocol.h"
#include "../lib/actuators/ActuatorController.h"
#include "../lib/logic/CommandDispatcher.h"

// Piny
static const uint8_t I2C_SDA = 21;
static const uint8_t I2C_SCL = 22;
static const uint8_t PIN_ONEWIRE = 4;

BmeSensor bme;
DallasBus dallas(PIN_ONEWIRE);
AdcSensor adc;
TmpSensor tmp;
ActuatorController actuators;
SerialProtocol proto;

CommandDispatcher dispatcher(proto, actuators);

static uint32_t g_last_ms = 0;

void setup() {
    Serial.begin(115200);
    while(!Serial) delay(10);
    delay(1000); 
    
    // I2C 100kHz
    Wire.begin(I2C_SDA, I2C_SCL, 100000); 

    // HW Init
    actuators.begin();
    dallas.begin();
    bool bme_ok = bme.beginAuto();
    bool adc_ok = adc.begin();
    bool tmp_ok = tmp.begin(); 
    uint8_t dallas_count = dallas.getSensorCount();

    proto.sendHello(bme_ok, dallas_count, adc_ok, tmp_ok);
    Serial.println("=== Temp-Lab ESP32 Ready ===");
}

void loop() {
    // 1. Příkazy
    Command cmd;
    if (proto.readCommand(cmd)) {
        dispatcher.apply(cmd);
    }

    // 2. Bezpečnost (Watchdog)
    dispatcher.checkSafetyTimeout();

    // 3. Měření
    if (dispatcher.isRunning() && dispatcher.getRateHz() > 0.0f) {
        uint32_t now = millis();
        uint32_t period = (uint32_t)(1000.0f / dispatcher.getRateHz());
        if (period == 0) period = 1;

        if (now - g_last_ms >= period) {
            g_last_ms = now;

            float t_bme = bme.readTemperatureC();
            float t_tmp = tmp.readTemperatureC();
            float mv_ads_r   = adc.readAdsMilliVolts(AdcSensor::ADS_CH_RESISTOR);
            float mv_ads_ntc = adc.readAdsMilliVolts(AdcSensor::ADS_CH_NTC);
            float mv_esp_r   = adc.readEspMilliVolts(AdcSensor::PIN_ESP_RESISTOR);
            float mv_esp_ntc = adc.readEspMilliVolts(AdcSensor::PIN_ESP_NTC);

            proto.sendData(now, t_bme, dallas, 
                           mv_ads_r, mv_ads_ntc, 
                           mv_esp_r, mv_esp_ntc, 
                           t_tmp);
        }
    }
    delay(1);
}