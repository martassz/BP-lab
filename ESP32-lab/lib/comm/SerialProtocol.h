#pragma once
#include <Arduino.h>
#include "../sensors/DallasSensor.h"

enum class CommandType {
    None, Start, Stop, SetRate, SetPwm 
};

struct Command {
    CommandType type = CommandType::None;
    float rateHz = 0.0f;
    int pwmChannel = 0;    // 0 = Topení, 1 = Chlazení
    float pwmValue = 0.0f; // 0-100 %
};

class SerialProtocol {
public:
    void begin(unsigned long baud);
    bool readCommand(Command& cmd);

    void sendAck(const char* cmd);
    void sendAckSetRate(float rateHz);
    void sendError(const char* msg);

    // Odesílání dat (upraveno na T_TMP a mV)
    void sendData(uint32_t t_ms,
                  float t_bme,
                  DallasBus& dallas,
                  float mv_ads_res, float mv_ads_ntc,
                  float mv_esp_res, float mv_esp_ntc,
                  float t_tmp);

private:
    String _buffer;
    static const size_t MAX_BUFFER = 256;
    void processLine(const String& line, Command& cmd);
};