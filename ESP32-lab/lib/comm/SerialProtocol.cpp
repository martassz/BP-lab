#include "SerialProtocol.h"

void SerialProtocol::begin(unsigned long baud) {
    Serial.begin(baud);
    unsigned long start = millis();
    while (!Serial && (millis() - start < 2000));
    // Hello posíláme až ručně z main.cpp
}

void SerialProtocol::sendHello(bool bme_ok, uint8_t dallas_count, bool adc_ok, bool tmp_ok) {
    Serial.print("{\"type\":\"hello\",\"device\":\"temp-lab-v2\"");
    Serial.print(",\"bme\":"); Serial.print(bme_ok ? "true" : "false");
    Serial.print(",\"dallas\":"); Serial.print(dallas_count);
    Serial.print(",\"adc\":"); Serial.print(adc_ok ? "true" : "false");
    Serial.print(",\"tmp\":"); Serial.print(tmp_ok ? "true" : "false");
    Serial.println("}");
}

bool SerialProtocol::readCommand(Command& cmd) {
    cmd.type = CommandType::None;
    while (Serial.available() > 0) {
        char c = (char)Serial.read();
        if (c == '\r') continue;
        if (c == '\n') {
            String line = _buffer;
            _buffer = "";
            line.trim();
            if (line.length() > 0) processLine(line, cmd);
            if (cmd.type != CommandType::None) return true;
        } else {
            if (_buffer.length() < MAX_BUFFER) _buffer += c;
            else _buffer = "";
        }
    }
    return false;
}

void SerialProtocol::processLine(const String& line, Command& cmd) {
    String up = line;
    up.trim(); up.toUpperCase();

    if (up == "START") { cmd.type = CommandType::Start; return; }
    if (up == "STOP")  { cmd.type = CommandType::Stop; return; }

    // SET PWM <ch> <val>
    if (up.startsWith("SET PWM")) {
        int idx = up.indexOf("SET PWM");
        if (idx >= 0) {
            String rest = line.substring(idx + 7);
            rest.trim();
            int space = rest.indexOf(' ');
            if (space > 0) {
                cmd.type = CommandType::SetPwm;
                cmd.pwmChannel = rest.substring(0, space).toInt();
                cmd.pwmValue = rest.substring(space + 1).toFloat();
            }
        }
        return;
    }

    // SET RATE <val>
    if (up.startsWith("SET RATE")) {
        int idx = up.indexOf("SET RATE");
        if (idx >= 0) {
            String rest = line.substring(idx + 8);
            rest.trim();
            float rate = rest.toFloat();
            if (rate > 0.0f) {
                cmd.type = CommandType::SetRate;
                cmd.rateHz = rate;
            }
        }
        return;
    }
}

void SerialProtocol::sendAckSetRate(float rateHz) {
    Serial.print("{\"type\":\"ack\",\"cmd\":\"set_rate\",\"rate_hz\":");
    Serial.print(rateHz, 4); Serial.println("}");
}
void SerialProtocol::sendAck(const char* cmd) {
    Serial.print("{\"type\":\"ack\",\"cmd\":\""); Serial.print(cmd); Serial.println("\"}");
}
void SerialProtocol::sendError(const char* msg) {
    Serial.print("{\"type\":\"error\",\"msg\":\""); Serial.print(msg); Serial.println("\"}");
}

void SerialProtocol::sendData(uint32_t t_ms, float t_bme, DallasBus& dallas,
                              float mv_ads_res, float mv_ads_ntc,
                              float mv_esp_res, float mv_esp_ntc,
                              float t_tmp) {
    Serial.print("{\"type\":\"data\"");
    Serial.print(",\"t_ms\":"); Serial.print(t_ms);

    Serial.print(",\"T_BME\":");
    if (isnan(t_bme)) Serial.print("null"); else Serial.print(t_bme, 4);

    // ADS1115 (mV)
    Serial.print(",\"V_ADS_R\":"); Serial.print(mv_ads_res, 2);
    Serial.print(",\"V_ADS_NTC\":"); Serial.print(mv_ads_ntc, 2);

    // ESP32 (mV)
    Serial.print(",\"V_ESP_R\":"); Serial.print(mv_esp_res, 2);
    Serial.print(",\"V_ESP_NTC\":"); Serial.print(mv_esp_ntc, 2);

    // TMP117
    Serial.print(",\"T_TMP\":"); 
    if (isnan(t_tmp)) Serial.print("null"); else Serial.print(t_tmp, 4);

    // Dallas
    uint8_t count = dallas.getSensorCount();
    for (uint8_t i = 0; i < count; ++i) {
        Serial.print(",\"T_DS"); Serial.print(i); Serial.print("\":");
        float t = dallas.getTemperatureC(i);
        if (isnan(t)) Serial.print("null"); else Serial.print(t, 4);
    }
    Serial.println("}");
}