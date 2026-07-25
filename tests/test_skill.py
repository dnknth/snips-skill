import json
import logging
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from snips_skill import skill as skill_mod
from snips_skill import snips
from snips_skill.exceptions import SnipsClarificationError
from snips_skill.intent import IntentPayload

INTENT_JSON = json.dumps(
    {
        "sessionId": "s1",
        "input": "turn on",
        "intent": {"intentName": "TurnOn", "confidenceScore": 0.9},
        "siteId": "default",
        "customData": "",
        "asrTokens": [[{"value": "x", "confidence": 1.0, "rangeStart": 0, "rangeEnd": 1, "time": None}]],
        "asrConfidence": 0.9,
        "rawInput": "turn on",
    }
)

LOW_CONF_JSON = json.dumps(
    {
        "sessionId": "s1",
        "input": "turn on",
        "intent": {"intentName": "TurnOn", "confidenceScore": 0.3},
        "siteId": "default",
        "customData": "",
        "asrTokens": [[{"value": "x", "confidence": 1.0, "rangeStart": 0, "rangeEnd": 1, "time": None}]],
        "asrConfidence": 0.3,
        "rawInput": "turn on",
    }
)

SLOT_JSON = json.dumps(
    {
        "sessionId": "s1",
        "input": "turn on",
        "intent": {"intentName": "TurnOn", "confidenceScore": 0.9},
        "siteId": "default",
        "customData": "",
        "asrTokens": [[{"value": "x", "confidence": 1.0, "rangeStart": 0, "rangeEnd": 1, "time": None}]],
        "asrConfidence": 0.9,
        "rawInput": "turn on",
        "slots": [
            {
                "entity": "e",
                "slotName": "device",
                "rawValue": "lamp",
                "confidence": 1.0,
                "range": {"start": 0, "end": 1, "rawStart": 0, "rawEnd": 1},
                "value": {"kind": "Number", "value": 1},
            }
        ],
    }
)


def make_skill(config_dict=None):
    config_dict = config_dict or {}
    with (
        patch.object(sys, "argv", ["prog"]),
        patch.object(snips.toml, "load", return_value=config_dict),
    ):
        return skill_mod.Skill()


class SkillInitTest(unittest.TestCase):
    def test_missing_config_warns(self):
        with (
            patch.object(snips.toml, "load", return_value={}),
            patch.object(sys, "argv", ["prog"]),
        ):
            skill = skill_mod.Skill()
        self.assertEqual(skill.options.config, "config.ini")
        self.assertEqual(list(skill.configuration.sections()), [])


class GetConfigTest(unittest.TestCase):
    def setUp(self):
        self.skill = make_skill()

    def test_existing_section(self):
        self.skill.configuration["global"] = {"key": "value"}
        self.assertEqual(self.skill.get_config("global")["key"], "value")

    def test_missing_section_uses_default(self):
        self.skill.configuration["DEFAULT"]["key"] = "default"
        self.assertEqual(self.skill.get_config("nope")["key"], "default")


class AddArgumentsTest(unittest.TestCase):
    def test_config_argument(self):
        skill = make_skill()
        skill.parse_args(["-c", "custom.ini"])
        self.assertEqual(skill.options.config, "custom.ini")


class ProcessConfigTest(unittest.TestCase):
    def test_called_when_config_file_exists(self):
        class MySkill(skill_mod.Skill):
            def process_config(self):
                self.processed = True

        with tempfile.NamedTemporaryFile(suffix=".ini", delete=False) as f:
            f.write(b"[global]\nkey=value\n")
            path = f.name
        try:
            with (
                patch.object(sys, "argv", ["prog", "-c", path]),
                patch.object(snips.toml, "load", return_value={}),
            ):
                skill = MySkill()
        finally:
            os.remove(path)

        self.assertTrue(skill.processed)
        self.assertEqual(skill.get_config("global")["key"], "value")


class IntentDecoratorTest(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.msg = MagicMock()
        self.msg.payload = INTENT_JSON

    def tearDown(self):
        skill_mod.SnipsClient.SUBSCRIPTIONS.clear()

    def _register(self, intent_name, handler, **kw):
        skill_mod.intent(intent_name, **kw)(handler)
        return skill_mod.SnipsClient.SUBSCRIPTIONS[
            f"{snips.SnipsClient.INTENT_PREFIX}{intent_name}"
        ][0]

    def test_none_result_ends_session(self):
        def handler(client, userdata, msg):
            return None

        wrapped = self._register("TestNone", handler)
        wrapped(self.client, None, self.msg)
        self.client.end_session.assert_called_once_with("s1", qos=1)
        self.assertIsInstance(self.msg.payload, IntentPayload)

    def test_text_result_ends_session(self):
        def handler(client, userdata, msg):
            return "answer"

        wrapped = self._register("TestText", handler)
        wrapped(self.client, None, self.msg)
        self.client.end_session.assert_called_once_with("s1", "answer", qos=1)

    def test_clarification_continues_session(self):
        def handler(client, userdata, msg):
            raise SnipsClarificationError(
                "which?", intent="TurnOn", slot="device", custom_data="cd"
            )

        wrapped = self._register("TestClarify", handler)
        wrapped(self.client, None, self.msg)
        self.client.continue_session.assert_called_once_with(
            "s1", "which?", ["TurnOn"], slot="device", custom_data="cd"
        )

    def test_log_level_logs_intent_and_response(self):
        def handler(client, userdata, msg):
            return "answer"

        wrapped = self._register(
            "TestLog", handler, log_level=logging.DEBUG
        )
        wrapped(self.client, None, self.msg)
        self.client.log_intent.assert_called_once()
        self.client.log_response.assert_called_once_with("answer", level=logging.DEBUG)

    def test_log_level_none_result_no_response_log(self):
        def handler(client, userdata, msg):
            return None

        wrapped = self._register(
            "TestLogNone", handler, log_level=logging.DEBUG
        )
        wrapped(self.client, None, self.msg)
        self.client.log_intent.assert_called_once()
        self.client.log_response.assert_not_called()


class MinConfidenceTest(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.called = []

    def test_above_threshold_calls_handler(self):
        msg = MagicMock()
        msg.payload = IntentPayload.model_validate_json(INTENT_JSON)

        @skill_mod.min_confidence(0.5)
        def handler(client, userdata, msg):
            self.called.append(msg.payload.intent.intent_name)

        handler(self.client, None, msg)
        self.assertEqual(self.called, ["TurnOn"])

    def test_below_threshold_raises(self):
        msg = MagicMock()
        msg.payload = IntentPayload.model_validate_json(LOW_CONF_JSON)

        @skill_mod.min_confidence(0.5)
        def handler(client, userdata, msg):
            self.called.append("x")

        with self.assertRaises(SnipsClarificationError):
            handler(self.client, None, msg)
        self.assertEqual(self.called, [])


class RequireSlotTest(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.called = []

    def test_slot_present_with_kind(self):
        msg = MagicMock()
        msg.payload = IntentPayload.model_validate_json(SLOT_JSON)

        @skill_mod.require_slot("device", "Which device?", kind="Number")
        def handler(client, userdata, msg):
            self.called.append("ok")

        handler(self.client, None, msg)
        self.assertEqual(self.called, ["ok"])

    def test_slot_present_wrong_kind_raises(self):
        msg = MagicMock()
        msg.payload = IntentPayload.model_validate_json(SLOT_JSON)

        @skill_mod.require_slot("device", "Which device?", kind="Duration")
        def handler(client, userdata, msg):
            self.called.append("x")

        with self.assertRaises(SnipsClarificationError) as ctx:
            handler(self.client, None, msg)
        self.assertEqual(self.called, [])
        self.assertEqual(ctx.exception.intent, "TurnOn")
        self.assertEqual(ctx.exception.slot, "device")

    def test_slot_missing_raises(self):
        msg = MagicMock()
        msg.payload = IntentPayload.model_validate_json(INTENT_JSON)

        @skill_mod.require_slot("device", "Which device?")
        def handler(client, userdata, msg):
            self.called.append("x")

        with self.assertRaises(SnipsClarificationError):
            handler(self.client, None, msg)
        self.assertEqual(self.called, [])


if __name__ == "__main__":
    unittest.main()
