#pragma once
#include <Arduino.h>
#include "../../lib/comm/SerialProtocol.h"
#include "../../lib/actuators/ActuatorController.h"

class CommandDispatcher {
public:
    CommandDispatcher(SerialProtocol& protocol, ActuatorController& actuators)
        : _proto(protocol), _actuators(actuators) {}

    void apply(const Command& cmd);

    bool isRunning() const { return _isRunning; }
    float getRateHz() const { return _rateHz; }

private:
    SerialProtocol& _proto;
    ActuatorController& _actuators;

    bool _isRunning = false;
    float _rateHz = 2.0f;
};