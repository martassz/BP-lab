#include "SerialProtocol.h"

void SerialProtocol::begin(unsigned long baud) {
    Serial.begin(baud);

    unsigned long start = millis();
    while (!Serial && (millis() - start < 2000)) {
        ; // některé hosty je potřeba chvilku počkat
    }

    // Úvodní info pro PC
    Serial.println("{\"type\":\"hello\",\"device\":\"temp-lab\",\"version\":\"1.0\"}");
}

bool SerialProtocol::readCommand(Command& cmd) {
    cmd.type = CommandType::None;
    cmd.rateHz = 0.0f;

    while (Serial.available() > 0) {
        char c = static_cast<char>(Serial.read());

        if (c == '\r') {
            continue; // ignorujeme CR
        }

        if (c == '\n') {
            String line = _buffer;
            _buffer = "";

            line.trim();
            if (line.length() == 0) {
                continue;
            }

            processLine(line, cmd);

            if (cmd.type != CommandType::None) {
                return true;
            }
        } else {
            // ochrana proti nekonečné / rozbité zprávě
            if (_buffer.length() < MAX_BUFFER) {
                _buffer += c;
            } else {
                // buffer přetekl, zahodíme a čekáme na nový řádek
                _buffer = "";
            }
        }
    }

    return false;
}

void SerialProtocol::processLine(const String& line, Command& cmd) {
    // case-insensitive zpracování
    String up = line;
    up.trim();
    up.toUpperCase();

    if (up == "START") {
        cmd.type = CommandType::Start;
        return;
    }

    if (up == "STOP") {
        cmd.type = CommandType::Stop;
        return;
    }

    // SET RATE <value>
    if (up.startsWith("SET RATE")) {
        // použijeme původní line kvůli číslům
        int idx = up.indexOf("SET RATE");
        if (idx >= 0) {
            String rest = line.substring(idx + 8); // délka "SET RATE"
            rest.trim();
            float rate = rest.toFloat();
            if (rate > 0.0f) {
                cmd.type = CommandType::SetRate;
                cmd.rateHz = rate;
            }
        }
        return;
    }

    // neznámý příkaz: ignorujeme (PC si může všimnout, že nepřišlo ACK)
}

void SerialProtocol::sendAckSetRate(float rateHz) {
    Serial.print("{\"type\":\"ack\",\"cmd\":\"set_rate\",\"rate_hz\":");
    Serial.print(rateHz, 4);
    Serial.println("}");
}

void SerialProtocol::sendAck(const char* cmd) {
    Serial.print("{\"type\":\"ack\",\"cmd\":\"");
    Serial.print(cmd);
    Serial.println("\"}");
}

void SerialProtocol::sendError(const char* msg) {
    Serial.print("{\"type\":\"error\",\"msg\":\"");
    // jednoduchá sanitizace uvozovek
    for (const char* p = msg; *p; ++p) {
        if (*p == '\"') {
            Serial.print("\\\"");
        } else {
            Serial.print(*p);
        }
    }
    Serial.println("\"}");
}

void SerialProtocol::sendData(uint32_t t_ms,
                              float t_bme,
                              DallasBus& dallas) {
    Serial.print("{\"type\":\"data\"");
    Serial.print(",\"t_ms\":");
    Serial.print(t_ms);

    Serial.print(",\"T_BME\":");
    if (isnan(t_bme)) Serial.print("null");
    else Serial.print(t_bme, 4);

    // Dallas senzory
    uint8_t count = dallas.getSensorCount();
    for (uint8_t i = 0; i < count; ++i) {
        float t = dallas.getTemperatureC(i);
        Serial.print(",\"T_DS");
        Serial.print(i);
        Serial.print("\":");
        if (isnan(t)) Serial.print("null");
        else Serial.print(t, 4);
    }

    Serial.println("}");
}
