#!/usr/bin/env python3

"""
Simplistic wrapper for the Paho MQTT client.
"""

import json
import logging
import sys
from datetime import datetime
from functools import wraps
from getpass import getpass
from shutil import get_terminal_size
from types import FunctionType
from typing import Any, Callable, Tuple

from basecmd import BaseCmd
from colors import cyan
from paho.mqtt.client import Client as PahoClient
from paho.mqtt.client import MQTTMessageInfo, MQTTv311
from pydantic import BaseModel
from typing_extensions import Self

__all__ = ("MqttClient", "topic", "CommandLineClient", "decode_json")


def decode_json(payload) -> Any:
    "Try to decode a message payload as JSON"
    try:
        return json.loads(payload)
    except ValueError:
        return payload


class MqttMessage(BaseModel):
    time: datetime
    topic: str
    payload: Any


class MqttClient(PahoClient):
    "MQTT client"

    TCP = "tcp"
    WEBSOCKETS = "websockets"
    DEFAULT_PORT = 1883
    DEFAULT_TLS_PORT = 8883
    SUBSCRIPTIONS: dict[str, Tuple[Callable, int]] = {}

    _tls_initialized: bool = False
    log: logging.Logger

    def __init__(
        self,
        client_id: str = "",
        clean_session: bool = True,
        userdata=None,
        protocol: int = MQTTv311,
        transport: str = TCP,
    ):
        super(MqttClient, self).__init__(
            client_id, clean_session or not client_id, userdata, protocol, transport
        )
        self._tls_initialized = False
        self.on_connect = MqttClient._on_connect

    @staticmethod
    def _on_connect(client, userdata, flags: dict, rc: int) -> None:
        "Subscribe to MQTT topics"

        assert rc == 0, "Connection failed"
        client.log.debug("Connected to MQTT broker")

        # Register @topic callbacks
        for topic, (callback, qos) in client.SUBSCRIPTIONS.items():
            client.subscribe(topic, qos)
            client.message_callback_add(topic, callback)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info):
        self.disconnect()

    def connect(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        host: str = "localhost",
        port: int = DEFAULT_PORT,
        username: str | None = None,
        password: str | None = None,
        keepalive: int = 60,
        bind_address: str = "",
        use_tls: bool = False,
    ) -> Self:
        "Connect to the MQTT broker"

        if username:
            self.username_pw_set(username, password)
        if use_tls or port == self.DEFAULT_TLS_PORT:
            if not self._tls_initialized:
                self.tls_set()
        if username:
            self.log.debug("Connecting to MQTT broker %s as user '%s'", host, username)
        else:
            self.log.debug("Connecting to MQTT broker %s", host)
        super().connect(host, port, keepalive, bind_address)
        return self

    def disconnect(self) -> None:
        super().disconnect()
        self.log.debug("Disconnected from MQTT broker")

    def reconnect(self) -> None:
        self.log.debug("Reconnecting to MQTT broker")
        super().reconnect()

    def loop_forever(self, *args, **kw) -> None:
        "Wait for messages and invoke callbacks until interrupted"
        try:
            super().loop_forever(*args, **kw)

        except KeyboardInterrupt:
            self.log.info("Interrupted by user")

    def subscribe(self, topic: str, qos: int = 0) -> Tuple:
        "Subscribe to a MQTT topic"
        result = super().subscribe(topic, qos)
        self.log.debug("Subscribed to MQTT topic: %s", topic)
        return result

    def publish(
        self,
        topic: str,
        payload=None,
        qos: int = 0,
        retain: bool = False,
        log_level: int = logging.NOTSET,
    ) -> MQTTMessageInfo:
        "Send an MQTT message"

        self.log.log(log_level, "Publishing: %s = %.20s", topic, payload)
        return super().publish(topic, payload, qos, retain)


def topic(
    topic: str,
    qos: int = 0,
    payload_converter: Callable[[bytes], Any] | None = None,
    log_level: int = logging.NOTSET,
):
    """Decorator for callback functions.
    Callbacks are invoked with these positional parameters:
     - client: MqttClient instance
     - msg: MQTT message
     - userdata: User-defined extra data
    Return values are not expected.
    :param topic: MQTT topic, may contain wildcards
    :param qos: MQTT quality of service (default: 0)
    :param payload_converter: unary function to transform the message payload
    """

    assert topic not in MqttClient.SUBSCRIPTIONS, (
        f"Topic '{topic}' is already registered"
    )

    def wrapper(method):
        @wraps(method)
        def wrapped(client, userdata, msg):
            "Callback for the Paho MQTT client"
            if log_level:
                client.log.log(log_level, "Received message: %s", msg.topic)
            if payload_converter:
                msg.payload = payload_converter(msg.payload)

            # User-provided callback
            if type(method) is FunctionType:
                return method(client, userdata, msg)
            else:  # bound method
                return method(userdata, msg)

        MqttClient.SUBSCRIPTIONS[topic] = (wrapped, qos)
        return wrapped

    return wrapper


class CommandLineClient(BaseCmd, MqttClient):
    "Simple MQTT command line client"

    password = None

    def add_arguments(self) -> None:
        "Set up arguments for connection parameters"
        self.parser.add_argument(
            "-H", "--host", default="localhost", help="MQTT host (default: localhost)"
        )
        self.parser.add_argument(
            "-P",
            "--port",
            default=MqttClient.DEFAULT_PORT,
            type=int,
            help="MQTT port (default: %d)" % MqttClient.DEFAULT_PORT,
        )
        self.parser.add_argument(
            "-T", "--tls", action="store_true", default=False, help="Use TLS"
        )
        self.parser.add_argument("-u", "--username", nargs="?", help="User name")
        self.parser.add_argument(
            "-p", "--password", action="store_true", help="Prompt for password"
        )

    def parse_args(self, args=None) -> None:
        super().parse_args(args)
        if self.options.username and self.options.password:
            self.password = getpass()
        if self.options.tls and self.options.port == MqttClient.DEFAULT_PORT:
            self.options.port = MqttClient.DEFAULT_TLS_PORT

    def run(self) -> None:
        "Connect to MQTT and handle incoming messages"
        try:
            with self.connect(
                self.options.host,
                self.options.port,
                self.options.username,
                self.password,
                use_tls=self.options.tls,
            ):
                self.loop_forever()
        except:
            if self.options.log_file:
                self.log.exception("Fatal error")
            raise

    def __call__(self):
        "Syntactic sugar for self.run()"
        self.run()


class Logger(CommandLineClient):
    WIDTH = get_terminal_size().columns
    COLOR = cyan if sys.stderr.isatty() else str

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument(
            "-t", "--topic", default="#", help="MQTT topic (default: #)"
        )
        self.parser.add_argument(
            "-w",
            "--width",
            default=self.WIDTH,
            type=int,
            help="Output width (default: %d)" % self.WIDTH,
        )
        self.parser.add_argument(
            "-j", "--json", action="store_true", help="Try to decode JSON payloads"
        )
        self.parser.add_argument(
            "-z", "--clear", action="store_true", help="Clear retained messages"
        )

    def print_msg(self, _userdata, msg):
        if self.options.json:
            payload = decode_json(msg.payload)
            if type(payload) is dict:
                payload = json.dumps(payload, sort_keys=True, indent=2)
            else:
                payload = str(payload)
            self.log.info("%s: %s", self.COLOR(msg.topic), payload)
        else:
            width = self.options.width - len(msg.topic) - 2
            self.log.info("%s: %.*a", self.COLOR(msg.topic), width, str(msg.payload))

        if self.options.clear and msg.retain and msg.payload:
            self.publish(msg.topic, retain=True)


def main():
    client = Logger()
    topic(client.options.topic)(client.print_msg)
    client.run()


if __name__ == "__main__":  # Demo code
    main()
