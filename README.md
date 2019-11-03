# snips-skill

Helpers to simplify the development of [Snips](https://snips.ai) skills in Python.

## Contents
 - `snips_skill.mqtt`: A thin wrapper around [paho-mqtt](https://www.eclipse.org/paho/clients/python/docs/)
 - `snips_skill.snips`: Auto-configuration from `/etc/snips/toml`, plus Snips-specific decorators for callbacks.
 - `snips_skill.intent`: Parse `hermes/intent/#` messages into a pythonic format.
 - `snips_skill.multi_room`: Utilities for multi-room setups.
 - `snips_skill.skill`: Base class for Snips actions.
