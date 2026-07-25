import logging
import unittest

from snips_skill.expr import Parser
from snips_skill.state import StateAwareMixin, conditional, when


class StatusUpdateTest(unittest.TestCase):
    def setUp(self):
        self.state = StateAwareMixin.__new__(StateAwareMixin)
        self.state.current_state = {}
        self.state.log = logging.getLogger("test")
        self.state.update_log_level = logging.DEBUG

    def test_records_changed_value(self):
        path = self.state.on_status_update("status/temp", 21)
        self.assertEqual(path, "status/temp")
        self.assertEqual(self.state.current_state["status/temp"], 21)

    def test_unchanged_value_returns_none(self):
        self.state.current_state["status/temp"] = 21
        path = self.state.on_status_update("status/temp", 21)
        self.assertIsNone(path)
        self.assertEqual(self.state.current_state["status/temp"], 21)


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.dummy = Dummy()
        Parser.Expr.last_state = None

    def tearDown(self):
        StateAwareMixin.conditions.clear()

    def test_redundant_publish_is_suppressed(self):
        self.dummy.current_state["topic"] = 21
        self.assertIsNone(self.dummy.publish("topic", 21))

    def test_type_cast_redundant_is_suppressed(self):
        self.dummy.current_state["topic"] = 21
        self.assertIsNone(self.dummy.publish("topic", "21"))

    def test_changed_publish_reaches_super(self):
        self.dummy.current_state["topic"] = 21
        self.dummy.publish("topic", 22)
        self.assertEqual(self.dummy.published, ("topic", 22, 0, False))

    def test_no_old_state_publishes(self):
        self.dummy.publish("topic", 21)
        self.assertEqual(self.dummy.published, ("topic", 21, 0, False))


class HandlerDispatchTest(unittest.TestCase):
    def setUp(self):
        StateAwareMixin.conditions.clear()
        Parser.Expr.last_state = None

    def tearDown(self):
        StateAwareMixin.conditions.clear()

    def test_when_true_invokes_handler(self):
        class Handler(StateAwareMixin):
            def __init__(self):
                self.calls = 0
                self.current_state = {}
                self.log = logging.getLogger("test")

            @when("status/temp > 20")
            def hot(self):
                self.calls += 1

        handler = Handler()
        handler.current_state["status/temp"] = 25
        handler.invoke_handlers("status/temp", 25)
        self.assertEqual(handler.calls, 1)

    def test_when_false_skips_handler(self):
        class Handler(StateAwareMixin):
            def __init__(self):
                self.calls = 0
                self.current_state = {}
                self.log = logging.getLogger("test")

            @when("status/temp > 20")
            def hot(self):
                self.calls += 1

        handler = Handler()
        handler.current_state["status/temp"] = 10
        handler.invoke_handlers("status/temp", 10)
        self.assertEqual(handler.calls, 0)

    def test_conditional_passes_value(self):
        received = []

        class Handler(StateAwareMixin):
            def __init__(self):
                self.current_state = {}
                self.log = logging.getLogger("test")

            @conditional("status/temp > 20")
            def temp(self, value):
                received.append(value)

        handler = Handler()
        handler.current_state["status/temp"] = 21
        handler.invoke_handlers("status/temp", 21)
        self.assertEqual(received, [True])


class Base:
    published = None

    def publish(
        self, topic, payload=None, qos=0, retain=False, log_level=logging.NOTSET
    ) -> None:
        self.published = (topic, payload, qos, retain)


class Dummy(StateAwareMixin, Base):
    def __init__(self):
        self.current_state = {}


if __name__ == "__main__":
    unittest.main()
