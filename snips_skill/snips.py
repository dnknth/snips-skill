#!/usr/bin/env python3

import json
import logging
import os
import uuid
from argparse import Namespace
from functools import partial, wraps
from typing import Any, Iterable

import toml
from decouple import config
from typing_extensions import Self

from .dialogue import (
    ActionInit,
    ContinueSession,
    EndSession,
    NotififationInit,
    StartSession,
)
from .mqtt import MqttClient, MQTTv311, topic

__all__ = (
    "SnipsClient",
    "debug_json",
    "on_continue_session",
    "on_end_session",
    "on_hotword_detected",
    "on_intent",
    "on_play_finished",
    "on_session_ended",
    "on_session_started",
    "on_start_session",
)


def serialize_custom_data(custom_data: Any) -> str | None:
    if type(custom_data) in (dict, list, tuple):
        return json.dumps(custom_data)
    elif custom_data is not None:
        return str(custom_data)


class SnipsClient(MqttClient):
    "Snips client with auto-configuration"

    CONFIG: str = config("SNIPS_CONFIG", default="/etc/snips.toml")  # pyright: ignore[reportAssignmentType]

    INTENT_PREFIX = "hermes/intent/"
    DIALOGUE = "hermes/dialogueManager"

    # Session life cycle messages
    HOTWORD_DETECTED = "hermes/hotword/+/detected"
    START_SESSION = f"{DIALOGUE}/startSession"
    SESSION_QUEUED = f"{DIALOGUE}/sessionQueued"
    SESSION_STARTED = f"{DIALOGUE}/sessionStarted"
    CONTINUE_SESSION = f"{DIALOGUE}/continueSession"
    END_SESSION = f"{DIALOGUE}/endSession"
    SESSION_ENDED = f"{DIALOGUE}/sessionEnded"

    # Misc
    PLAY_BYTES = "hermes/audioServer/{site_id}/playBytes/{request_id}"
    PLAY_FINISHED = "hermes/audioServer/%s/playFinished"
    REGISTER_SOUND = "hermes/tts/registerSound/%s"

    options: Namespace

    def __init__(
        self,
        client_id=None,
        clean_session=True,
        userdata=None,
        protocol=MQTTv311,
        transport=MqttClient.TCP,
        config: str = CONFIG,
    ):
        if client_id is None:
            client_id = "snips-%s-%s" % (self.__class__.__name__.lower(), os.getpid())

        super(SnipsClient, self).__init__(
            client_id, clean_session, userdata, protocol, transport
        )

        self.log.debug("Loading config: %s", config)
        self.config = toml.load(config)

    @property
    def site_id(self) -> str:
        return (
            self.config.get("snips-audio-server", {})
            .get("bind", "default@mqtt")
            .split("@")[0]
        )

    def connect(self) -> Self:  # pyright: ignore[reportIncompatibleMethodOverride]
        "Connect to the MQTT broker and invoke callback methods"
        common = self.config.get("snips-common", {})

        host_port = common.get("mqtt", "localhost:1883")
        if ":" in host_port:
            host, port = host_port.split(":")
            port = int(port)
        else:
            host = host_port
            port = MqttClient.DEFAULT_PORT

        password = None
        username = common.get("mqtt_username")
        if username:
            password = common.get("mqtt_password")

        ca_file = common.get("mqtt_tls_cafile")
        cert = common.get("mqtt_tls_client_cert")
        key = None if not cert else common.get("mqtt_tls_client_key")

        self._tls_initialized = False
        if ca_file or cert or port == self.DEFAULT_TLS_PORT:
            assert not common.get("mqtt_tls_hostname"), (
                "mqtt_tls_hostname not supported"
            )
            self.tls_set(ca_certs=ca_file, certfile=cert, keyfile=key)
            self._tls_initialized = True

        return super().connect(
            host=host, port=port, username=username, password=password
        )

    # See: https://docs.snips.ai/reference/dialogue#start-session
    def start_session(
        self,
        site_id: str,
        init: ActionInit | NotififationInit,
        custom_data: Any = None,
        qos: int = 1,
        **kw,
    ) -> None:
        "End the session with an optional message"
        payload = StartSession(
            site_id=site_id, init=init, custom_data=serialize_custom_data(custom_data)
        )

        self.log.debug("Starting %s session on site '%s'", init.type, site_id)
        self.publish(
            self.START_SESSION,
            payload.model_dump_json(exclude_none=True),
            qos=qos,
            **kw,
        )

    def speak(self, site_id: str, text: str, **kw) -> None:
        "Say a one-time notification"
        self.start_session(site_id, init=NotififationInit(text=text), **kw)

    # See: https://docs.snips.ai/reference/dialogue#end-session
    def end_session(
        self,
        session_id: str,
        text: str | None = None,
        qos: int = 1,
        **kw,
    ) -> None:
        "End the session with an optional message"

        if text:
            text = " ".join(text.split())

        payload = EndSession(session_id=session_id, text=text)
        self.log.debug("Ending session %s with '%s'", session_id, text)
        self.publish(
            self.END_SESSION, payload.model_dump_json(exclude_none=True), qos=qos, **kw
        )

    # See: https://docs.snips.ai/reference/dialogue#continue-session
    def continue_session(
        self,
        session_id: str,
        text: str,
        intent_filter: list[str] | None = None,
        slot: str | None = None,
        send_intent_not_recognized: bool = False,
        custom_data: Any = None,
        qos: int = 1,
        **kw,
    ) -> None:
        "Continue the session with a question"

        payload = ContinueSession(
            text=" ".join(text.split()),
            session_id=session_id,
            intent_filter=intent_filter,
            slot=slot,
            send_intent_not_recognized=bool(send_intent_not_recognized),
            custom_data=serialize_custom_data(custom_data),
        )

        self.log.debug("Continuing session %s with '%s'", session_id, text)
        self.publish(
            self.CONTINUE_SESSION,
            payload.model_dump_json(exclude_none=True),
            qos=qos,
            **kw,
        )

    # See: https://docs.snips.ai/reference/dialogue#start-session
    def play_sound(
        self, site_id: str, wav_data: bytes, request_id: str | None = None, **kw
    ) -> str:
        "Play a WAV sound at the given site"
        if not request_id:
            request_id = str(uuid.uuid4())
        self.publish(
            self.PLAY_BYTES.format(site_id=site_id, request_id=request_id),
            payload=wav_data,
            **kw,
        )
        return request_id

    def register_sound(self, name: str, wav_data: bytes, **kw) -> Self:
        self.publish(self.REGISTER_SOUND % name, wav_data, **kw)
        return self

    def run(self) -> None:
        "Connect to MQTT and handle incoming messages"
        try:
            with self.connect():
                self.loop_forever()
        except:
            if self.options.log_file:
                self.log.exception("Fatal error")
            raise


###################################
### Decorators for Snips events ###
###################################


def _load_json(payload) -> Any:
    "Helper to convert JSON to a Python dict"
    # Only convert if this appears to be a JSON payload.
    # Needed for multiple annotations on a method
    return json.loads(payload) if type(payload) is bytes else payload


on_hotword_detected = partial(
    topic, SnipsClient.HOTWORD_DETECTED, payload_converter=_load_json
)

on_start_session = partial(
    topic, SnipsClient.START_SESSION, payload_converter=_load_json
)


def on_intent(
    intent: str, qos: int = 0, payload_converter=_load_json, log_level=logging.NOTSET
):
    return topic(
        f"{SnipsClient.INTENT_PREFIX}{intent}",
        qos=qos,
        payload_converter=payload_converter,
        log_level=log_level,
    )


on_continue_session = partial(
    topic, SnipsClient.CONTINUE_SESSION, payload_converter=_load_json
)

on_session_queued = partial(
    topic, SnipsClient.SESSION_QUEUED, payload_converter=_load_json
)

on_session_started = partial(
    topic, SnipsClient.SESSION_STARTED, payload_converter=_load_json
)

on_end_session = partial(topic, SnipsClient.END_SESSION, payload_converter=_load_json)

on_session_ended = partial(
    topic, SnipsClient.SESSION_ENDED, payload_converter=_load_json
)


def on_play_finished(site: str = "+", qos: int = 0, log_level=logging.NOTSET):
    return topic(
        SnipsClient.PLAY_FINISHED % site,
        qos=qos,
        payload_converter=_load_json,
        log_level=log_level,
    )


def debug_json(keys: Iterable[str] = []):
    "Decorator to debug message payloads"

    def wrapper(method):
        @wraps(method)
        def wrapped(client, userdata, msg):
            if type(msg.payload) is dict:
                data = msg.payload
                if keys:
                    data = {k: v for k, v in data.items() if not keys or k in keys}
                client.log.debug(
                    "Payload: %s", json.dumps(data, sort_keys=True, indent=2)
                )
            return method(client, userdata, msg)

        return wrapped

    return wrapper
