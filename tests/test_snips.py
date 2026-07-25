import json
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

from snips_skill import mqtt, snips
from snips_skill.dialogue import ActionInit


class SerializeCustomDataTest(unittest.TestCase):
    def test_dict(self):
        self.assertEqual(snips.serialize_custom_data({"a": 1}), '{"a": 1}')

    def test_list(self):
        self.assertEqual(snips.serialize_custom_data([1, 2]), "[1, 2]")

    def test_tuple(self):
        self.assertEqual(snips.serialize_custom_data((1, 2)), "[1, 2]")

    def test_other(self):
        self.assertEqual(snips.serialize_custom_data(42), "42")

    def test_none(self):
        self.assertIsNone(snips.serialize_custom_data(None))


def make_client(config):
    with (
        patch.object(snips.SnipsClient, "log", MagicMock(), create=True),
        patch.object(snips.toml, "load", return_value=config),
    ):
        client = snips.SnipsClient(config=config)
    client.log = MagicMock()
    return client


class SnipsClientInitTest(unittest.TestCase):
    def test_generates_client_id_and_loads_config(self):
        with (
            patch.object(snips.SnipsClient, "log", MagicMock(), create=True),
            patch.object(snips.toml, "load", return_value={}) as load,
        ):
            client = snips.SnipsClient()

        self.assertEqual(
            client._client_id,
            b"snips-snipsclient-%d" % __import__("os").getpid(),
        )
        load.assert_called_once()

    def test_custom_client_id(self):
        with (
            patch.object(snips.SnipsClient, "log", MagicMock(), create=True),
            patch.object(snips.toml, "load", return_value={}),
        ):
            client = snips.SnipsClient(client_id="custom")
        self.assertEqual(client._client_id, b"custom")


class SiteIdTest(unittest.TestCase):
    def test_from_bind(self):
        client = make_client({"snips-audio-server": {"bind": "kitchen@mqtt"}})
        self.assertEqual(client.site_id, "kitchen")

    def test_default(self):
        client = make_client({})
        self.assertEqual(client.site_id, "default")


class SnipsConnectTest(unittest.TestCase):
    def setUp(self):
        self.client = make_client(
            {
                "snips-common": {
                    "mqtt": "broker:1884",
                    "mqtt_username": "alice",
                    "mqtt_password": "secret",
                }
            }
        )

    def test_parses_host_port_and_credentials(self):
        with (
            patch.object(mqtt.PahoClient, "connect") as connect,
            patch.object(self.client, "username_pw_set") as set_pw,
        ):
            self.client.connect()

        connect.assert_called_once_with("broker", 1884, 60, "")
        set_pw.assert_called_once_with("alice", "secret")

    def test_plain_host_uses_default_port(self):
        self.client.config = {"snips-common": {"mqtt": "broker"}}
        with (
            patch.object(mqtt.PahoClient, "connect") as connect,
            patch.object(self.client, "username_pw_set") as set_pw,
        ):
            self.client.connect()
        connect.assert_called_once_with("broker", 1883, 60, "")
        set_pw.assert_not_called()

    def test_tls_with_cafile(self):
        self.client.config = {"snips-common": {"mqtt_tls_cafile": "ca.pem"}}
        with (
            patch.object(mqtt.PahoClient, "connect"),
            patch.object(snips.ssl, "create_default_context") as ctx,
            patch.object(self.client, "tls_set_context") as tls_set,
        ):
            self.client.connect()
        ctx.assert_called_once_with(cafile="ca.pem")
        tls_set.assert_called_once()
        self.assertTrue(self.client._tls_initialized)

    def test_tls_with_cert_loads_key(self):
        self.client.config = {
            "snips-common": {
                "mqtt_tls_cafile": "ca.pem",
                "mqtt_tls_client_cert": "cert.pem",
                "mqtt_tls_client_key": "key.pem",
            }
        }
        with (
            patch.object(mqtt.PahoClient, "connect"),
            patch.object(snips.ssl, "create_default_context") as ctx,
        ):
            self.client.connect()
        ctx.return_value.load_cert_chain.assert_called_once_with(
            "cert.pem", "key.pem"
        )

    def test_tls_hostname_unsupported(self):
        self.client.config = {
            "snips-common": {"mqtt_tls_cafile": "ca.pem", "mqtt_tls_hostname": "x"}
        }
        with (
            patch.object(mqtt.PahoClient, "connect"),
            patch.object(snips.ssl, "create_default_context"),
            self.assertRaises(AssertionError),
        ):
            self.client.connect()

    def test_tls_port_forces_tls(self):
        self.client.config = {"snips-common": {"mqtt": "broker:8883"}}
        with (
            patch.object(mqtt.PahoClient, "connect"),
            patch.object(self.client, "tls_set_context") as tls_set,
        ):
            self.client.connect()
        self.assertTrue(self.client._tls_initialized)
        tls_set.assert_called_once()


class SnipsPublishTest(unittest.TestCase):
    def setUp(self):
        self.client = make_client({})

    def test_start_session(self):
        self.client.publish = MagicMock()
        self.client.start_session(
            "kitchen", init=ActionInit(text="hi"), custom_data={"a": 1}
        )

        args = self.client.publish.call_args
        self.assertEqual(args.args[0], snips.SnipsClient.START_SESSION)
        self.assertEqual(args.kwargs["qos"], 1)
        payload = json.loads(args.args[1])
        self.assertEqual(payload["siteId"], "kitchen")
        self.assertEqual(payload["init"]["type"], "action")
        self.assertEqual(payload["init"]["text"], "hi")
        self.assertEqual(payload["customData"], '{"a": 1}')

    def test_speak(self):
        self.client.publish = MagicMock()
        self.client.speak("kitchen", "hello")
        payload = json.loads(self.client.publish.call_args.args[1])
        self.assertEqual(payload["init"]["type"], "notification")
        self.assertEqual(payload["init"]["text"], "hello")

    def test_end_session_normalizes_text(self):
        self.client.publish = MagicMock()
        self.client.end_session("s1", "  hello   world ")
        args = self.client.publish.call_args
        self.assertEqual(args.args[0], snips.SnipsClient.END_SESSION)
        payload = json.loads(args.args[1])
        self.assertEqual(payload["sessionId"], "s1")
        self.assertEqual(payload["text"], "hello world")

    def test_end_session_without_text(self):
        self.client.publish = MagicMock()
        self.client.end_session("s1")
        payload = json.loads(self.client.publish.call_args.args[1])
        self.assertNotIn("text", payload)

    def test_continue_session(self):
        self.client.publish = MagicMock()
        self.client.continue_session(
            "s1",
            "  pick   one?",
            intent_filter=["A", "B"],
            slot="device",
            send_intent_not_recognized=True,
            custom_data=[1, 2],
        )
        args = self.client.publish.call_args
        self.assertEqual(args.args[0], snips.SnipsClient.CONTINUE_SESSION)
        payload = json.loads(args.args[1])
        self.assertEqual(payload["sessionId"], "s1")
        self.assertEqual(payload["text"], "pick one?")
        self.assertEqual(payload["intentFilter"], ["A", "B"])
        self.assertEqual(payload["slot"], "device")
        self.assertEqual(payload["sendIntentNotRecognized"], True)
        self.assertEqual(payload["customData"], "[1, 2]")

    def test_play_sound_generates_request_id(self):
        self.client.publish = MagicMock()
        with patch("snips_skill.snips.uuid.uuid4", return_value="rid"):
            request_id = self.client.play_sound("kitchen", b"data")

        self.assertEqual(request_id, "rid")
        args = self.client.publish.call_args
        self.assertEqual(
            args.args[0], "hermes/audioServer/kitchen/playBytes/rid"
        )
        self.assertEqual(args.kwargs["payload"], b"data")

    def test_play_sound_with_request_id(self):
        self.client.publish = MagicMock()
        with patch("snips_skill.snips.uuid.uuid4") as uuid4:
            self.client.play_sound("kitchen", b"data", request_id="given")
        uuid4.assert_not_called()

    def test_register_sound_returns_self(self):
        self.client.publish = MagicMock()
        result = self.client.register_sound("name", b"data")
        self.assertIs(result, self.client)
        self.assertEqual(
            self.client.publish.call_args.args[0],
            "hermes/tts/registerSound/name",
        )


class SnipsRunTest(unittest.TestCase):
    def setUp(self):
        self.client = make_client({})

    def test_connect_and_loop(self):
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

    def test_raises_on_connect_error(self):
        self.client.options = Namespace(log_file=None)
        with (
            patch.object(self.client, "connect", side_effect=RuntimeError("boom")),
            self.assertRaises(RuntimeError),
        ):
            self.client.run()

    def test_logs_fatal_error(self):
        self.client.options = Namespace(log_file="fatal.log")
        with (
            patch.object(self.client, "connect", side_effect=RuntimeError("boom")),
            patch.object(self.client.log, "exception") as exc,
            self.assertRaises(RuntimeError),
        ):
            self.client.run()
        exc.assert_called_once()


class LoadJsonTest(unittest.TestCase):
    def test_bytes_decodes(self):
        self.assertEqual(snips._load_json(b'{"a": 1}'), {"a": 1})

    def test_non_bytes_passthrough(self):
        self.assertEqual(snips._load_json({"a": 1}), {"a": 1})


class DecoratorTopicTest(unittest.TestCase):
    def tearDown(self):
        snips.SnipsClient.SUBSCRIPTIONS.clear()

    def test_on_intent_registers_prefix(self):
        @snips.on_intent("TestIntent")
        def handler(client, userdata, msg):
            pass

        self.assertIn("hermes/intent/TestIntent", snips.SnipsClient.SUBSCRIPTIONS)

    def test_on_play_finished(self):
        @snips.on_play_finished("kitchen")
        def handler(client, userdata, msg):
            pass

        self.assertIn(
            "hermes/audioServer/kitchen/playFinished",
            snips.SnipsClient.SUBSCRIPTIONS,
        )

    def test_on_hotword_detected(self):
        @snips.on_hotword_detected()
        def handler(client, userdata, msg):
            pass

        self.assertIn("hermes/hotword/+/detected", snips.SnipsClient.SUBSCRIPTIONS)

    def test_on_continue_session(self):
        @snips.on_continue_session()
        def handler(client, userdata, msg):
            pass

        self.assertIn(
            "hermes/dialogueManager/continueSession",
            snips.SnipsClient.SUBSCRIPTIONS,
        )


class DebugJsonTest(unittest.TestCase):
    def tearDown(self):
        snips.SnipsClient.SUBSCRIPTIONS.clear()

    def test_logs_filtered_dict(self):
        client = MagicMock()
        msg = MagicMock()
        msg.payload = {"a": 1, "b": 2, "c": 3}

        @snips.debug_json(["a", "b"])
        def handler(client, userdata, msg):
            return "ok"

        result = handler(client, None, msg)
        self.assertEqual(result, "ok")
        client.log.debug.assert_called_once()

    def test_non_dict_payload_not_logged(self):
        client = MagicMock()
        msg = MagicMock()
        msg.payload = "text"

        @snips.debug_json()
        def handler(client, userdata, msg):
            return "ok"

        handler(client, None, msg)
        client.log.debug.assert_not_called()


if __name__ == "__main__":
    unittest.main()
