import unittest
from pathlib import Path

from intent import IntentPayload
from mqtt import MqttMessage
from pydantic import TypeAdapter

from snips_skill.dialogue import EndSession

MqttMessageList = TypeAdapter(list[MqttMessage])


class SchemaTest(unittest.TestCase):
    messages = list((Path(__file__).parent.parent / "recordings").glob("*.json"))

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


if __name__ == "__main__":
    unittest.main()
