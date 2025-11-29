#pragma once
#include <Arduino.h>
#include "../sensors/DallasSensor.h"

enum class CommandType {
    None, Start, Stop, SetRate, SetPwm, Ping // <-- NOVÝ PŘÍKAZ
};

struct Command {
    CommandType type = CommandType::None;
    float rateHz = 0.0f;
    int pwmChannel = 0;    
    float pwmValue = 0.0f; 
};

class SerialProtocol {
public:
    void begin(unsigned long baud);
    void sendHello(bool bme_ok, uint8_t dallas_count, bool adc_ok, bool tmp_ok);
    bool readCommand(Command& cmd);
    void sendAck(const char* cmd);
    void sendAckSetRate(float rateHz);
    void sendError(const char* msg);
    void sendData(uint32_t t_ms, float t_bme, DallasBus& dallas, float v1, float v2, float v3, float v4, float t_tmp);

private:
    String _buffer;
    static const size_t MAX_BUFFER = 256;
    void processLine(const String& line, Command& cmd);
};