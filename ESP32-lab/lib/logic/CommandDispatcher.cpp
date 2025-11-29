#include "CommandDispatcher.h"

void CommandDispatcher::apply(const Command& cmd) {
    // Jakýkoliv příkaz resetuje watchdog
    _lastCommandTime = millis();

    switch (cmd.type) {
        case CommandType::Start:
            _isRunning = true;
            _proto.sendAck("start");
            break;

        case CommandType::Stop:
            _isRunning = false;
            _actuators.stopAll();
            _proto.sendAck("stop");
            break;
        
        case CommandType::Ping:
            // Jen resetuje časovač (už se stalo výše), neposíláme ACK
            break;

        case CommandType::SetRate:
            if (cmd.rateHz > 0.0f && cmd.rateHz <= 10.0f) {
                _rateHz = cmd.rateHz;
                _proto.sendAckSetRate(_rateHz);
            } else {
                _proto.sendError("invalid_rate");
            }
            break;

        case CommandType::SetPwm:
            if (cmd.pwmChannel == 0) {
                _actuators.setHeater(cmd.pwmValue);
            } else if (cmd.pwmChannel == 1) {
                _actuators.setCooler(cmd.pwmValue);
            }
            _proto.sendAck("set_pwm");
            break;
            
        default: break;
    }
}

// --- TOTO JE TA CHYBĚJÍCÍ ČÁST ---
void CommandDispatcher::checkSafetyTimeout() {
    // Pokud běžíme a dlouho nepřišel příkaz (více než 3 sekundy), vypneme to
    if (_isRunning && (millis() - _lastCommandTime > SAFETY_TIMEOUT_MS)) {
        _isRunning = false;
        _actuators.stopAll();
        // Volitelně pošleme error, aby PC vědělo, proč se to vyplo
        // _proto.sendError("safety_timeout"); 
    }
}
// ---------------------------------