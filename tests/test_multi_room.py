import unittest
from configparser import ConfigParser

from snips_skill.exceptions import SnipsClarificationError, SnipsError
from snips_skill.i18n import ALL_ROOMS, DEFAULT_ROOM_NAMES, ROOMS, RoomName, _
from snips_skill.intent import Intent, IntentPayload, Slot, UnknownValue
from snips_skill.multi_room import MultiRoomConfig


def make_payload(
    site_id="default",
    input="",
    slots=None,
    intent_name="TurnOn",
    confidence=0.9,
):
    return IntentPayload(
        sessionId="s1",
        input=input,
        intent=Intent(intentName=intent_name, confidenceScore=confidence),
        siteId=site_id,
        slots=slots,
        customData="",
        asrTokens=[],
        asrConfidence=confidence,
        rawInput=input,
    )


def room_slot(value):
    return [
        Slot(
            entity="room",
            slotName="room",
            rawValue=value,
            confidence=1.0,
            range=None,
            value=UnknownValue(kind="Unknown", value=value),
        )
    ]


def make_config(sections):
    cfg = ConfigParser()
    for name, items in sections.items():
        cfg[name] = items
    return cfg


class RoomMixin(MultiRoomConfig):
    LOCATION_SLOT = "room"


class ProcessConfigTest(unittest.TestCase):
    def setUp(self):
        self.cfg = ConfigParser()
        self.cfg["global"] = {"key": "value"}
        self.cfg["secret"] = {"key": "value"}
        self.cfg["bedroom"] = {"site_id": "bedroom1"}
        self.cfg["kitchen"] = {"site_id": "kitchen1"}
        self.cfg["hall"] = {"key": "value"}
        self.m = MultiRoomConfig()
        self.m.configuration = self.cfg
        self.m.process_config()

    def test_maps_site_ids_to_sections(self):
        self.assertEqual(self.m.sites["bedroom1"], "bedroom")
        self.assertEqual(self.m.sites["kitchen1"], "kitchen")

    def test_excludes_standard_sections(self):
        self.assertNotIn("global", self.m.sites.values())
        self.assertNotIn("secret", self.m.sites.values())

    def test_excludes_sections_without_site_id(self):
        self.assertNotIn("hall", self.m.sites.values())

    def test_excludes_standard_section_even_with_site_id(self):
        self.cfg["global"]["site_id"] = "g1"
        self.m.process_config()
        self.assertNotIn("g1", self.m.sites)


class AddRoomNameTest(unittest.TestCase):
    def setUp(self):
        self.original = dict(ROOMS)

    def tearDown(self):
        ROOMS.clear()
        ROOMS.update(self.original)

    def test_registers_room_lowercase(self):
        MultiRoomConfig().add_room_name(
            "Living Room", "the living room", "in the living room"
        )
        self.assertEqual(
            ROOMS["living room"], RoomName("the living room", "in the living room")
        )


class GetCurrentRoomTest(unittest.TestCase):
    def setUp(self):
        self.m = MultiRoomConfig()
        self.m.sites = {"default": "livingroom"}

    def test_returns_site_mapping(self):
        payload = make_payload(site_id="default")
        self.assertEqual(self.m.get_current_room(payload), "livingroom")

    def test_unknown_site_returns_none(self):
        payload = make_payload(site_id="other")
        self.assertIsNone(self.m.get_current_room(payload))


class GetRoomTest(unittest.TestCase):
    def setUp(self):
        self.m = RoomMixin()
        self.m.sites = {"default": "bedroom"}

    def test_requires_location_slot(self):
        m = MultiRoomConfig()
        m.sites = {"default": "bedroom"}
        with self.assertRaises(AssertionError):
            m.get_room(make_payload())

    def test_returns_slot_value(self):
        payload = make_payload(site_id="default", slots=room_slot("kitchen"))
        self.assertEqual(self.m.get_room(payload), "kitchen")

    def test_default_room_when_slot_is_here(self):
        payload = make_payload(
            site_id="default", slots=room_slot(DEFAULT_ROOM_NAMES[0])
        )
        self.assertEqual(self.m.get_room(payload), "bedroom")

    def test_no_slot_returns_current_room(self):
        payload = make_payload(site_id="default")
        self.assertEqual(self.m.get_room(payload), "bedroom")


class InCurrentRoomTest(unittest.TestCase):
    def setUp(self):
        self.m = RoomMixin()
        self.m.sites = {"default": "bedroom"}

    def test_current_room(self):
        payload = make_payload(site_id="default", slots=room_slot("bedroom"))
        self.assertTrue(self.m.in_current_room(payload))

    def test_other_room(self):
        payload = make_payload(site_id="default", slots=room_slot("kitchen"))
        self.assertFalse(self.m.in_current_room(payload))


class GetRoomNameTest(unittest.TestCase):
    def setUp(self):
        self.m = RoomMixin()
        self.m.sites = {"default": "bedroom"}

    def test_applies_modifier(self):
        payload = make_payload(site_id="default", slots=room_slot("kitchen"))
        result = self.m.get_room_name(payload, modifier=lambda r: f"in the {r}")
        self.assertEqual(result, "in the kitchen")

    def test_returns_default_for_current_room(self):
        payload = make_payload(site_id="default", slots=room_slot("bedroom"))
        result = self.m.get_room_name(
            payload, modifier=lambda r: f"in the {r}", default="here"
        )
        self.assertEqual(result, "here")

    def test_unknown_room(self):
        self.m.sites = {}
        payload = make_payload(site_id="default")
        result = self.m.get_room_name(payload, modifier=lambda r: r)
        self.assertEqual(result, _("unknown room"))


class GetRoomConfigTest(unittest.TestCase):
    def setUp(self):
        self.m = RoomMixin()
        self.m.sites = {"default": "bedroom"}
        self.m.configuration = make_config(
            {"bedroom": {"site_id": "bedroom1"}}
        )

    def test_returns_section(self):
        payload = make_payload(site_id="default", slots=room_slot("bedroom"))
        cfg = self.m.get_room_config(payload)
        self.assertEqual(cfg["site_id"], "bedroom1")

    def test_missing_raises_clarification(self):
        payload = make_payload(site_id="default", slots=room_slot("kitchen"))
        with self.assertRaises(SnipsClarificationError) as ctx:
            self.m.get_room_config(payload)
        self.assertEqual(ctx.exception.intent, "TurnOn")
        self.assertEqual(ctx.exception.slot, "room")


class AllRoomsTest(unittest.TestCase):
    def setUp(self):
        self.m = RoomMixin()
        self.m.sites = {}

    def test_room_slot_is_all_rooms(self):
        payload = make_payload(slots=room_slot(ALL_ROOMS[0]))
        self.assertTrue(self.m.all_rooms(payload))

    def test_name_in_input(self):
        payload = make_payload(input=ALL_ROOMS[1], slots=room_slot("kitchen"))
        self.assertTrue(self.m.all_rooms(payload))

    def test_not_all_rooms(self):
        payload = make_payload(input="", slots=room_slot("kitchen"))
        self.assertFalse(self.m.all_rooms(payload))


class GetSiteIdTest(unittest.TestCase):
    def setUp(self):
        self.m = RoomMixin()
        self.m.sites = {"default": "bedroom"}

    def test_returns_site_id(self):
        self.m.configuration = make_config({"bedroom": {"site_id": "bedroom1"}})
        payload = make_payload(site_id="default", slots=room_slot("bedroom"))
        self.assertEqual(self.m.get_site_id(payload), "bedroom1")

    def test_unconfigured_room_raises(self):
        self.m.configuration = make_config({"bedroom": {}})
        payload = make_payload(site_id="default", slots=room_slot("bedroom"))
        with self.assertRaises(SnipsError):
            self.m.get_site_id(payload)


if __name__ == "__main__":
    unittest.main()
