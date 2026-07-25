import argparse
import logging
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from snips_skill import mqtt


class DecodeJsonTest(unittest.TestCase):
    def test_valid_json(self):
        self.assertEqual(mqtt.decode_json(b'{"a": 1}'), {"a": 1})

    def test_invalid_json(self):
        payload = b"not json"
        self.assertEqual(mqtt.decode_json(payload), payload)

    def test_non_bytes_returns_payload(self):
        payload = {"already": "dict"}
        self.assertEqual(mqtt.decode_json(payload), payload)


class TopicTest(unittest.TestCase):
    def setUp(self):
        self.added = set()

    def tearDown(self):
        for topic in self.added:
            mqtt.MqttClient.SUBSCRIPTIONS.pop(topic, None)
        self.added.clear()

    def test_registers_callback(self):
        @mqtt.topic("test/register")
        def handler(client, userdata, msg):
            pass

        self.added.add("test/register")

        wrapped, qos = mqtt.MqttClient.SUBSCRIPTIONS["test/register"]
        self.assertEqual(qos, 0)
        self.assertTrue(callable(wrapped))

    def test_duplicate_topic_asserts(self):
        @mqtt.topic("test/duplicate")
        def handler(client, userdata, msg):
            pass

        self.added.add("test/duplicate")

        with self.assertRaises(AssertionError):
            mqtt.topic("test/duplicate")

    def test_plain_function_dispatch(self):
        called = []

        @mqtt.topic("test/plain")
        def handler(client, userdata, msg):
            called.append((client, userdata, msg))
            return 42

        self.added.add("test/plain")

        wrapped = mqtt.MqttClient.SUBSCRIPTIONS["test/plain"][0]
        result = wrapped("client", "userdata", "msg")
        self.assertEqual(called, [("client", "userdata", "msg")])
        self.assertEqual(result, 42)

    def test_bound_method_dispatch(self):
        class Handler:
            def __init__(self):
                self.called = None

            def handle(self, userdata, msg):
                self.called = (userdata, msg)

        handler = Handler()
        mqtt.topic("test/bound")(handler.handle)
        self.added.add("test/bound")

        wrapped = mqtt.MqttClient.SUBSCRIPTIONS["test/bound"][0]
        wrapped(None, "userdata", "msg")
        self.assertEqual(handler.called, ("userdata", "msg"))

    def test_payload_converter(self):
        @mqtt.topic("test/convert", payload_converter=lambda p: "converted")
        def handler(client, userdata, msg):
            return msg.payload

        self.added.add("test/convert")

        wrapped = mqtt.MqttClient.SUBSCRIPTIONS["test/convert"][0]
        msg = MagicMock()
        msg.payload = "raw"
        self.assertEqual(wrapped(None, None, msg), "converted")


class MqttClientConnectTest(unittest.TestCase):
    def setUp(self):
        self.client = mqtt.MqttClient()
        self.client.log = logging.getLogger("test")

    def test_tls_on_tls_port(self):
        with (
            patch.object(mqtt.PahoClient, "connect") as connect,
            patch("snips_skill.mqtt.ssl.create_default_context") as context,
            patch.object(self.client, "tls_set_context") as tls_set,
        ):
            self.client.connect(port=mqtt.MqttClient.DEFAULT_TLS_PORT)

        self.assertTrue(self.client._tls_initialized)
        context.assert_called_once()
        tls_set.assert_called_once()
        connect.assert_called_once()

    def test_no_tls_on_default_port(self):
        with (
            patch.object(mqtt.PahoClient, "connect") as connect,
            patch("snips_skill.mqtt.ssl.create_default_context") as context,
        ):
            self.client.connect(port=mqtt.MqttClient.DEFAULT_PORT)

        self.assertFalse(self.client._tls_initialized)
        context.assert_not_called()
        connect.assert_called_once()


class MqttClientInitTest(unittest.TestCase):
    def setUp(self):
        self.client = mqtt.MqttClient()
        self.client.log = MagicMock()

    def test_default_client_id_and_clean_session(self):
        self.assertEqual(self.client._clean_session, True)
        self.assertFalse(self.client._tls_initialized)
        self.assertEqual(self.client.on_connect, mqtt.MqttClient._on_connect)

    def test_clean_session_false_with_client_id(self):
        client = mqtt.MqttClient(client_id="foo", clean_session=False)
        self.assertEqual(client._clean_session, False)

    def test_clean_session_false_forced_without_client_id(self):
        client = mqtt.MqttClient(client_id="", clean_session=False)
        self.assertEqual(client._clean_session, True)


class OnConnectTest(unittest.TestCase):
    def setUp(self):
        self.client = mqtt.MqttClient()
        self.client.log = MagicMock()

    def test_subscribes_to_registered_topics(self):
        subs = {
            "a/b": (lambda *a: None, 0),
            "c/d": (lambda *a: None, 1),
        }
        with (
            patch.object(mqtt.MqttClient, "SUBSCRIPTIONS", subs),
            patch.object(self.client, "subscribe") as subscribe,
            patch.object(self.client, "message_callback_add") as add,
        ):
            mqtt.MqttClient._on_connect(
                self.client, None, {}, 0
            )

        self.client.log.debug.assert_called()
        self.assertEqual(subscribe.call_args_list[0].args, ("a/b", 0))
        self.assertEqual(subscribe.call_args_list[1].args, ("c/d", 1))
        self.assertEqual(add.call_count, 2)

    def test_nonzero_rc_asserts(self):
        with self.assertRaises(AssertionError):
            mqtt.MqttClient._on_connect(self.client, None, {}, 1)


class MqttClientConnectExtraTest(unittest.TestCase):
    def setUp(self):
        self.client = mqtt.MqttClient()
        self.client.log = MagicMock()

    def test_no_tls_on_default_port(self):
        with (
            patch.object(mqtt.PahoClient, "connect") as connect,
            patch("snips_skill.mqtt.ssl.create_default_context") as context,
        ):
            self.client.connect(port=mqtt.MqttClient.DEFAULT_PORT)

        self.assertFalse(self.client._tls_initialized)
        context.assert_not_called()
        connect.assert_called_once()

    def test_use_tls_on_default_port(self):
        with (
            patch.object(mqtt.PahoClient, "connect"),
            patch("snips_skill.mqtt.ssl.create_default_context"),
            patch.object(self.client, "tls_set_context") as tls_set,
        ):
            self.client.connect(port=mqtt.MqttClient.DEFAULT_PORT, use_tls=True)

        self.assertTrue(self.client._tls_initialized)
        tls_set.assert_called_once()

    def test_username_sets_credentials(self):
        with (
            patch.object(mqtt.PahoClient, "connect") as connect,
            patch.object(self.client, "username_pw_set") as set_pw,
        ):
            self.client.connect(username="alice", password="secret")

        set_pw.assert_called_once_with("alice", "secret")
        connect.assert_called_once()


class MqttClientWrapperTest(unittest.TestCase):
    def setUp(self):
        self.client = mqtt.MqttClient()
        self.client.log = MagicMock()

    def test_disconnect(self):
        with patch.object(mqtt.PahoClient, "disconnect") as disconnect:
            self.client.disconnect()
        disconnect.assert_called_once()

    def test_reconnect(self):
        with patch.object(mqtt.PahoClient, "reconnect") as reconnect:
            self.client.reconnect()
        reconnect.assert_called_once()

    def test_subscribe(self):
        with patch.object(mqtt.PahoClient, "subscribe", return_value="result") as sub:
            self.assertEqual(self.client.subscribe("a/b", 1), "result")
        sub.assert_called_once_with("a/b", 1)

    def test_publish(self):
        with patch.object(mqtt.PahoClient, "publish", return_value="info") as pub:
            self.assertEqual(
                self.client.publish("a/b", "payload", qos=1, retain=True, log_level=logging.WARNING),
                "info",
            )
        pub.assert_called_once_with("a/b", "payload", 1, True)
        self.client.log.log.assert_called()

    def test_loop_forever(self):
        with patch.object(mqtt.PahoClient, "loop_forever") as loop:
            self.client.loop_forever()
        loop.assert_called_once()

    def test_loop_forever_keyboard_interrupt(self):
        def boom(*args, **kw):
            raise KeyboardInterrupt

        with patch.object(mqtt.PahoClient, "loop_forever", boom):
            self.client.loop_forever()
        self.client.log.info.assert_called()

    def test_context_manager_disconnects(self):
        with patch.object(self.client, "disconnect") as disconnect, self.client:
            pass
        disconnect.assert_called_once()


class MqttMessageTest(unittest.TestCase):
    def test_model_round_trip(self):
        ts = datetime(2020, 1, 1, tzinfo=timezone.utc)
        msg = mqtt.MqttMessage(time=ts, topic="a/b", payload={"k": 1})
        self.assertEqual(msg.topic, "a/b")
        self.assertEqual(msg.payload["k"], 1)
        self.assertEqual(msg.model_dump()["time"], ts)


class TopicLogLevelTest(unittest.TestCase):
    def tearDown(self):
        mqtt.MqttClient.SUBSCRIPTIONS.pop("test/log", None)

    def test_logs_received_message_at_log_level(self):
        client = MagicMock()
        msg = MagicMock()
        msg.topic = "test/log"

        @mqtt.topic("test/log", log_level=logging.WARNING)
        def handler(client, userdata, msg):
            pass

        wrapped = mqtt.MqttClient.SUBSCRIPTIONS["test/log"][0]
        wrapped(client, None, msg)
        client.log.log.assert_called_once_with(logging.WARNING, "Received message: %s", "test/log")


class CommandLineClientTest(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(sys, "argv", ["prog"])
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = mqtt.CommandLineClient()

    def test_default_options(self):
        self.assertEqual(self.client.options.host, "localhost")
        self.assertEqual(self.client.options.port, mqtt.MqttClient.DEFAULT_PORT)
        self.assertFalse(self.client.options.tls)

    def test_add_arguments(self):
        self.client.parser = argparse.ArgumentParser(description="prog")
        self.client.add_arguments()
        actions = self.client.parser._option_string_actions
        for flag in ("-H", "-P", "-T", "-u", "-p"):
            self.assertIn(flag, actions)

    def test_parse_args_prompts_password(self):
        with patch("snips_skill.mqtt.getpass", return_value="secret") as gp:
            self.client.parse_args(["-u", "alice", "-p"])
        gp.assert_called_once()
        self.assertEqual(self.client.password, "secret")

    def test_parse_args_tls_upgrades_default_port(self):
        self.client.parse_args(["-T"])
        self.assertEqual(self.client.options.port, mqtt.MqttClient.DEFAULT_TLS_PORT)

    def test_run_connects_and_loops(self):
        cm = MagicMock()
        cm.__enter__ = MagicMock()
        cm.__exit__ = MagicMock(return_value=False)
        with (
            patch.object(self.client, "connect", return_value=cm) as connect,
            patch.object(self.client, "loop_forever") as loop,
        ):
            self.client.run()
        connect.assert_called_once()
        loop.assert_called_once()

    def test_run_raises_without_log_file(self):
        self.client.options.log_file = None
        with (
            patch.object(self.client, "connect", side_effect=RuntimeError("boom")),
            patch.object(self.client, "loop_forever") as loop,
            self.assertRaises(RuntimeError),
        ):
            self.client.run()
        loop.assert_not_called()

    def test_run_logs_fatal_error_with_log_file(self):
        self.client.options.log_file = "fatal.log"
        with (
            patch.object(self.client, "connect", side_effect=RuntimeError("boom")),
            patch.object(self.client.log, "exception") as exc,
            self.assertRaises(RuntimeError),
        ):
            self.client.run()
        exc.assert_called_once()


if __name__ == "__main__":
    unittest.main()
