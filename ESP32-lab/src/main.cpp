#include <Arduino.h>
#include <Wire.h>

#include "BmeSensor.h"
#include "DallasSensor.h"
#include "SerialProtocol.h"

// Porty
static const uint8_t I2C_SDA_PIN = 21;
static const uint8_t I2C_SCL_PIN = 22;
static const uint8_t DALLAS_PIN  = 4;

BmeSensor bme;
DallasBus dallas(DALLAS_PIN);
SerialProtocol proto;

// Stav měření
static bool     g_running    = false;
static float    g_rate_hz    = 2.0f;      // výchozí frekvence
static uint32_t g_last_ms    = 0;

void applyCommand(const Command& cmd) {
    switch (cmd.type) {
        case CommandType::Start:
            g_running = true;
            proto.sendAck("start");
            break;

        case CommandType::Stop:
            g_running = false;
            proto.sendAck("stop");
            break;

        case CommandType::SetRate:
            if (cmd.rateHz > 0.0f && cmd.rateHz <= 1000.0f) {
                g_rate_hz = cmd.rateHz;
                proto.sendAckSetRate(g_rate_hz);
            } else {
                proto.sendError("invalid_set_rate_range");
            }
            break;

        case CommandType::None:
        default:
            break;
    }
}

void setup() {
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);

    bool bme_ok = bme.beginAuto();
    dallas.begin();

    proto.begin(115200);

    // Info log
    Serial.println("=== Temp-lab ESP32 ready ===");
    Serial.print("BME280: ");
    Serial.println(bme_ok ? "OK" : "NENI");
    Serial.print("Dallas senzoru: ");
    Serial.println(dallas.getSensorCount());
    Serial.println("Ocekava se JSON protokol: HELLO, SET RATE, START, STOP, DATA...");
    Serial.println("=====================================");
}

void loop() {
    // 1) Zpracování příkazů z PC
    Command cmd;
    if (proto.readCommand(cmd)) {
        applyCommand(cmd);
    }

    // 2) Periodické měření a odesílání dat
    if (g_running && g_rate_hz > 0.0f) {
        uint32_t now = millis();
        uint32_t period_ms = (uint32_t)(1000.0f / g_rate_hz);

        if (period_ms == 0) {
            period_ms = 1;
        }

        if (now - g_last_ms >= period_ms) {
            g_last_ms = now;

            float t_bme = bme.readTemperatureC();
            proto.sendData(now, t_bme, dallas);
        }
    }

    delay(1);
}
