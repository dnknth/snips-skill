import unittest
from datetime import timedelta
from pathlib import Path

from pydantic import TypeAdapter

from snips_skill.dialogue import EndSession
from snips_skill.intent import (
    DurationValue,
    IntentPayload,
    NumericValue,
    Slot,
    SlotValue,
    UnknownValue,
)
from snips_skill.mqtt import MqttMessage

MqttMessageList = TypeAdapter(list[MqttMessage])
SlotValueAdapter = TypeAdapter(SlotValue)


class SchemaTest(unittest.TestCase):
    def setUp(self):
        self.messages = list(
            (Path(__file__).parent.parent / "recordings").glob("*.json")
        )

    def test_intent(self):
        for json in self.messages:
            with self.subTest(f"parse-intent-{json}"):
                messages = MqttMessageList.validate_json(json.read_text())
                IntentPayload.model_validate(messages[0].payload)

    def test_end_session(self):
        for json in self.messages:
            with self.subTest(f"end-session-{json}"):
                messages = MqttMessageList.validate_json(json.read_text())
                EndSession.model_validate(messages[1].payload)


class IntentValueTest(unittest.TestCase):
    def test_duration_as_timedelta(self):
        duration = DurationValue(
            kind="Duration",
            precision="Exact",
            weeks=1,
            days=2,
            hours=3,
            minutes=4,
            seconds=5,
        )
        self.assertEqual(
            duration.as_timedelta(),
            timedelta(weeks=1, days=2, hours=3, minutes=4, seconds=5),
        )

    def test_slot_value_discrimination(self):
        numeric = SlotValueAdapter.validate_python({"kind": "Number", "value": 21})
        self.assertIsInstance(numeric, NumericValue)
        unknown = SlotValueAdapter.validate_python({"kind": "Unknown", "value": "foo"})
        self.assertIsInstance(unknown, UnknownValue)

    def test_slot_values_mapping(self):
        payload = IntentPayload(
            sessionId="s",
            input="",
            intent={"intentName": "x", "confidenceScore": 1.0},
            siteId="site",
            slots=[
                Slot(
                    entity="e",
                    slotName="room",
                    rawValue="kitchen",
                    confidence=1.0,
                    range=None,
                    value=UnknownValue(kind="Unknown", value="kitchen"),
                )
            ],
            customData="",
            asrTokens=[],
            asrConfidence=0.0,
            rawInput="",
        )
        self.assertEqual(payload.slot_values["room"].value, "kitchen")
        self.assertEqual(payload["room"].value, "kitchen")


if __name__ == "__main__":
    unittest.main()
