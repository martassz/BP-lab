#pragma once

#include <Arduino.h>
#include "../sensors/DallasSensor.h"  // kvůli DallasBus

enum class CommandType {
    None,
    Start,
    Stop,
    SetRate
};

struct Command {
    CommandType type = CommandType::None;
    float rateHz = 0.0f;  // platné jen pro SetRate
};

class SerialProtocol {
public:
    void begin(unsigned long baud);

    // Přečte z příchozího seriáku jeden příkaz (pokud je k dispozici).
    // Vrací true, pokud naplnil 'cmd' něčím jiným než CommandType::None.
    bool readCommand(Command& cmd);

    // Potvrzení nastavení vzorkovací frekvence
    void sendAckSetRate(float rateHz);

    // Obecné ACK na příkaz (START/STOP/...)
    void sendAck(const char* cmd);

    // Chybová zpráva
    void sendError(const char* msg);

    // Datová zpráva s měřením (JSON)
    void sendData(uint32_t t_ms,
                  float t_bme,
                  DallasBus& dallas);

private:
    String _buffer;
    static const size_t MAX_BUFFER = 256; // ochrana proti přetečení

    void processLine(const String& line, Command& cmd);
};
