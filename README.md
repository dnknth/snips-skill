# snips-skill

Helpers to keep [Snips](https://snips.ai) skills in Python3 free of boilerplate code.

Snips used to be a French company with a decent voice assistant.
They were bought by [Sonos](https://www.sonos.com/) and discontinued all services.
Snips also created the [Hermes](https://github.com/snipsco/hermes-protocol) MQTT protocol,
which is compatible with the [Rhasspy](https://github.com/rhasspy/rhasspy) voice assistant.

A 'skill' (in Snips parlance) is an MQTT client that may read sensors,
do computations, or trigger devices.

## Contents

- `MqttClient`: A thin wrapper around [paho-mqtt](https://www.eclipse.org/paho/clients/python/docs/)
- `CommandLineClient` skeleton MQTT command line client with connection settings.
- `SnipsClient`: Reads connection parameters from `/etc/snips/toml`
- Snips-specific decorators for callbacks, see below.
- `MultiRoomConfig`: Utilities for multi-room setups.
- `Skill`: Base class for Snips actions.
- `@intent` decorator, see below.
- `StateAwareMixin` with `@when` and `@conditional` decorators for stateful MQTT clients.

## Plain MQTT clients

Plain MQTT is supported via the `MqttClient` and `CommandLineClient` classes
and the `@topic` decorator.

A `CommandLineClient` provides argument parsing for connection parameters and includes
standard logging. For message handling, define a function or method as
above, and decorate it with `@topic`. This registers the method (or function)
as a callback for the given MQTT topic.

### Usage example

```python
from snips_skill import CommandLineClient, topic

class Logger(CommandLineClient):
    'Log all incoming MQTT messages'
    
    @topic('#')
    def print_msg(self, userdata, msg):
        self.log.info("%s: %s", msg.topic, msg.payload[:64])

if __name__ == '__main__':
    Logger().run()
```

## Snips session event decorators

The `Skill` class provides automatic connection configuration via `/etc/snips/toml`.
Also, the following Snips-specific decorators for session events are provided:

- `on_intent`: Handle intents,
- `on_intent_not_recognized`: Handle unknown intents,
- `on_start_session`: Called before session start,
- `on_continue_session`: Called for subsequent session prompts,
- `on_session_started`: Called at session start,
- `on_end_session`: Called before session end,
- `on_session_ended`: Called at session end.

All decorators can be used either on standalone callback functions,
or on methods of the various client classes (including `Skill`).

Methods should expect the parameters `self, userdata, msg`, and
standalone functions should expect `client, userdata, msg`.

Multiple decorators on the same method are possible,
but if they have inconsistent `qos` values, the results will be unpredictable.
Also note that multiple decorators will produce repetitive log lines
with `DEBUG` level. Set `log_level=None` on all but one decorator to fix it.

## The `@intent` decorator

`@intent`-decorated callbacks receive `msg.paylod`
as an `IntentPayload` object, a parsed version of the JSON intent data.
Slot values are converted to appropriate Python types.

The next step in the Snips session depends on the outcome of the decorated function or method:

- If the function returns a string or raises a `SnipsError`, the session ends with a message,
- If it returns en empty string, the session is ended silently.
- If it raises a `SnipsClarificationError`, the session is continued with a question. This can be used to narrow down parameters or to implement question-and-answer sequences.

To require a minimum level of confidence for an intent,
put `@min_confidence` below `@intent`.

To ensure that certain slots are present in the intent,
put `@require_slot` with a slot name below `@intent`.

The `@intent` decorator should not be used in combination with any `on_*` decorators.

### Example usage

```python
from snips_skill import intent, Skill

class HelloSkill(Skill):
    'Snips skill to say hello'
    
    @intent('example:hello')
    def say_hello(self, userdata, msg):
        return 'Hello, there'
        
if __name__ == '__main__':
    HelloSkill().run()
```

## `StateAwareMixin`, `@when` and `@conditional` decorators

These define actions triggered by state changes on MQTT.
Example: _Sensor registers motion -> switch the light on_

Clients can use `StateAwareMixin` to track the last known state
of relevant topics. For that, a `status_topic` needs to be configured
in the global section of `config.ini`.
Topics and payloads are kept in `self.current_state`.

Change handlers should be decorated with either `@when` or `@conditional`.
The former triggers the handler whenever a boolean condition on the current
state is fulfilled, the latter whenever a MQTT topic relevant for the given boolean condition changes.

### Usage

```python

  @when('topic/a > 0')
  def topic_a_handler(self):
    ... # do something
  
  @conditional('topic/a != 0 or topic/b != 0')
  def topic_a_or_b_handler(self, on):
    if on:
      ... # switch something on
    else:
      ... # switch it off
```

Boolean expressions, numeric comparisons, string (in)equality
and string matching with regular expressions are supported.
As usual, parentheses can be used to control the evaluation order.

See `test_expr.py` for the exact grammar.
