# snips-skill

Helpers to keep [Snips](https://snips.ai) skills in Python3 free of boilerplate code.

Snips used to be a French company with a decent voice assistant.
They were bought by [Sonos](https://www.sonos.com/) and discontinued all services.
Snips also created the [Hermes](https://github.com/snipsco/hermes-protocol) MQTT protocol,
which is compatible with the [Rhasspy](https://github.com/rhasspy/rhasspy) voice assistant.

A "skill" (in Snips parlance) is an MQTT client that may read sensors,
do computations, or trigger devices.

## Installation

```sh
pip install snips-skill
```

Requires Python 3.10+. Dependencies: `paho-mqtt`, `pydantic`, `ply`, `croniter`, `toml`, `basecmd`, `decouple`.

## Contents

- **Clients**: `MqttClient`, `CommandLineClient`, `SnipsClient`, `Skill`
- **Decorators**: `@topic`, `@intent`, `@min_confidence`, `@require_slot`, `@on_*` session events
- **State tracking**: `StateAwareMixin`, `@when`, `@conditional`
- **Scheduling**: `Scheduler`, `@cron`, `@delay`
- **Multi-room**: `MultiRoomConfig`
- **i18n**: `get_translations`, `room_with_article`, `room_with_preposition`
- **Utilities**: `expr` (boolean expression parser)

---

## Plain MQTT clients

`MqttClient` is a thin wrapper around [paho-mqtt](https://www.eclipse.org/paho/clients/python/docs/).
`CommandLineClient` adds argument parsing for connection settings (`-H`, `-P`, `-T`, `-u`, `-p`) and standard logging.

### Usage

```python
from snips_skill import CommandLineClient, topic

class Logger(CommandLineClient):
    @topic('#')
    def print_msg(self, userdata, msg):
        self.log.info("%s: %s", msg.topic, msg.payload[:64])

if __name__ == '__main__':
    Logger().run()
```

### `@topic` decorator

Registers a callback for an MQTT topic (supports wildcards). Methods receive `(self, userdata, msg)`; standalone functions receive `(client, userdata, msg)`.

```python
@topic("hermes/intent/#", qos=0, payload_converter=decode_json)
def handler(client, userdata, msg):
    ...
```

---

## Snips clients

### `SnipsClient`

Reads connection parameters from `/etc/snips.toml` (or `$SNIPS_CONFIG`). Provides session lifecycle methods:

| Method | Description |
|--------|-------------|
| `start_session(site_id, init)` | Start a session (action or notification) |
| `speak(site_id, text)` | Say a one-time notification |
| `end_session(session_id, text)` | End the session with an optional message |
| `continue_session(session_id, text, ...)` | Continue with a question |
| `play_sound(site_id, wav_data)` | Play a WAV sound |
| `register_sound(name, wav_data)` | Register a TTS sound |

### `Skill`

Base class for Snips actions. Extends `SnipsClient` with `config.ini` support:

```python
from snips_skill import Skill, intent

class HelloSkill(Skill):
    @intent('example:hello')
    def say_hello(self, userdata, msg):
        return 'Hello, there'

if __name__ == '__main__':
    HelloSkill().run()
```

---

## Session event decorators

All decorators can be used on methods (expect `self, userdata, msg`) or standalone functions (expect `client, userdata, msg`). Multiple decorators on the same method are supported; set `log_level=None` on all but one to avoid duplicate logs.

| Decorator | Topic |
|-----------|-------|
| `@on_intent("intent_name")` | `hermes/intent/...` |
| `@on_start_session()` | `hermes/dialogueManager/startSession` |
| `@on_session_started()` | `hermes/dialogueManager/sessionStarted` |
| `@on_continue_session()` | `hermes/dialogueManager/continueSession` |
| `@on_end_session()` | `hermes/dialogueManager/endSession` |
| `@on_session_ended()` | `hermes/dialogueManager/sessionEnded` |
| `@on_hotword_detected()` | `hermes/hotword/+/detected` |
| `@on_play_finished("site")` | `hermes/audioServer/.../playFinished` |

---

## `@intent` decorator

`@intent`-decorated callbacks receive `msg.payload` as an `IntentPayload` object — a parsed version of the JSON intent data. Slot values are converted to appropriate Python types.

The session outcome depends on the return value or exception:

| Outcome | How |
|---------|-----|
| Session ends with message | Return a string or raise `SnipsError` |
| Session ends silently | Return `None` |
| Continue with question | Raise `SnipsClarificationError` |

### `@min_confidence(threshold, prompt)`

Rejects intents below a confidence threshold. If the confidence score is lower than `threshold`, the user is asked `prompt` to confirm. Default prompt: `"Pardon?"`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `threshold` | `float` | Minimum confidence score (0.0 – 1.0) |
| `prompt` | `str` | Question to re-ask when confidence is too low |

### `@require_slot(slot, prompt, kind)`

Ensures a required slot is present in the intent. If missing, the user is asked `prompt`. Optionally checks that the slot matches a specific `kind`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `slot` | `str` | Slot name to check |
| `prompt` | `str` | Question to re-ask when slot is missing |
| `kind` | `str` or `None` | Expected slot kind (optional) |

### Example

```python
@intent('example:set-temperature')
@min_confidence(0.5)
@require_slot('temperature', 'Which temperature?')
def set_temp(self, userdata, msg):
    temp = msg.payload.slot_values['temperature'].value
    return f"Setting temperature to {temp}"
```

---

## State tracking

`StateAwareMixin` tracks the last known state of MQTT topics in `self.current_state`. Configure a `status_topic` in `config.ini` under the `[global]` section:

```ini
[global]
status_topic = status/#
```

Subscribes to that topic with JSON decoding; every message updates `self.current_state` and triggers any matching `@when`/`@conditional` handlers. The `publish()` method also avoids redundant updates — if the payload matches the current state, the message is suppressed.

### Usage

```python
from snips_skill import Skill, StateAwareMixin, when

class MotionLight(StateAwareMixin, Skill):
    @when('sensor/motion > 0')
    def light_on(self):
        self.publish('cmd/light', 'on')
```

### `@when` decorator

Triggers the handler whenever a boolean condition becomes true:

```python
@when('sensor/motion > 0')
def motion_detected(self):
    ...  # switch light on
```

### `@conditional` decorator

Triggers the handler whenever a relevant topic changes, passing `True`/`False`:

```python
@conditional('sensor/temperature > 25 or sensor/humidity > 80')
def uncomfortable(self, on):
    if on:
        ...  # turn on AC
    else:
        ...  # turn off AC
```

Boolean expressions support comparisons (`<`, `>`, `<=`, `>=`, `==`, `!=`, `~=` regex), `and`, `or`, `not`, and parentheses.

### Boolean expression grammar

The expression parser (`expr.py`) supports a simple grammar for use with `@when` and `@conditional`:

```
expr       → term
           | expr AND expr
           | expr OR expr
           | NOT expr
           | LPAREN expr RPAREN

term       → TOPIC LESS NUMBER
           | TOPIC LESS_EQUAL NUMBER
           | TOPIC GREATER_EQUAL NUMBER
           | TOPIC GREATER NUMBER
           | TOPIC EQUAL literal
           | TOPIC NOT_EQUAL literal
           | TOPIC REGEX_MATCH STRING

literal    → NUMBER | STRING
```

Precedence (highest to lowest): `NOT` > comparisons > `AND` > `OR`. See `snips_skill/test_expr.py` for examples.

---

## Task scheduling

`Scheduler` mixin adds cron-style and delayed task execution.

### `@cron` decorator

Run a method on a cron schedule:

```python
from snips_skill import Skill, Scheduler, cron

class MySkill(Scheduler, Skill):
    @cron("0 6 * * *")   # every day at 6:00
    def morning_routine(self):
        ...
```

### `@delay` decorator

Delay method execution by a duration (with optional randomization):

```python
from snips_skill import delay

@delay(minutes=5, randomize=True)
def deferred_action(self):
    ...
```

---

## Multi-room support

`MultiRoomConfig` maps site IDs to room names from `config.ini` sections. Each section with a `site_id` option (except `[global]` and other standard sections) becomes a named room:

```ini
[global]
status_topic = status/#      # not related to rooms; used by StateAwareMixin

[kitchen]
site_id = main
some_option = value

[bedroom]
site_id = bedroom
another_option = 42
```

```python
from snips_skill import MultiRoomConfig

class MultiRoomSkill(MultiRoomConfig, Skill):
    LOCATION_SLOT = 'room'

    def handle_intent(self, payload):
        room = self.get_room(payload)
        config = self.get_room_config(payload)
        site = self.get_site_id(payload)
```

Key methods: `get_room()`, `get_current_room()`, `get_room_name()`, `get_room_config()`, `get_site_id()`, `all_rooms()`, `in_current_room()`.

---

## Internationalization

Internationalization uses Python's standard `gettext` module. Run `xgettext` on your Python sources to produce a `.pot` template file, then create `.po` files for each locale and compile them to `.mo` files:

```
your-skill/
├── locale/
│   ├── my_skill.pot                 # template (generated by xgettext)
│   ├── de_DE/
│   │   └── LC_MESSAGES/
│   │       └── my_skill.mo         # compiled from my_skill.po
│   └── fr_FR/
│       └── LC_MESSAGES/
│           └── my_skill.mo
└── skill.py                         # calls get_translations(__file__, "my_skill")
```

The `.po` file format follows standard gettext conventions:

```po
# my_skill.po
msgid "the kitchen"
msgstr "die Küche"

msgid "in the kitchen"
msgstr "in der Küche"
```

See the [Makefile](Makefile) for the workflow used by this library: `make messages` generates the `.pot` file from source, and `make dist` compiles `.po` to `.mo` before building.

After installing translations with `get_translations(__file__, "my_skill")`, helper functions provide translated room names with articles and prepositions (supports gendered languages like German):

```python
from snips_skill import room_with_article, room_with_preposition

room_with_article("kitchen")       # "the kitchen" / "die Küche"
room_with_preposition("kitchen")   # "in the kitchen" / "in der Küche"
```
