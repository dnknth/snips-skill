from configparser import ConfigParser
from typing import Callable, MutableMapping

from .exceptions import SnipsClarificationError, SnipsError
from .i18n import (
    ALL_ROOMS,
    DEFAULT_ROOM_NAMES,
    ROOMS,
    RoomName,
    get_translations,
    room_with_article,
    room_with_preposition,
)
from .intent import IntentPayload
from .skill import Skill

__all__ = ("MultiRoomConfig", "ROOMS", "room_with_article", "room_with_preposition")

_, ngettext = get_translations(__file__, "snips_skill")


class MultiRoomConfig:
    """Mixin for multi-site actions.
    Contains helper methods to extract location slots,
    look up room names, associated configuration and site IDs.
    """

    LOCATION_SLOT = None  # Override as needed, e.g. 'room'

    configuration: ConfigParser
    sites: dict[str, str]

    def process_config(self) -> None:
        "Load all non-standard config sections as rooms"
        self.sites = {
            self.configuration[section]["site_id"]: section
            for section in self.configuration
            if section not in Skill.STANDARD_SECTIONS
            and "site_id" in self.configuration[section]
        }

    def add_room_name(
        self, room: str, with_article: str, with_preposition: str
    ) -> None:
        "Register additional room names with articles and prepositions"
        ROOMS[room.lower()] = RoomName(with_article, with_preposition)

    def get_current_room(self, payload: IntentPayload) -> str | None:
        "Get the room name of the current site"
        return self.sites.get(payload.site_id)

    def get_room(self, payload: IntentPayload) -> str | None:
        "Get the recognized room name"

        default_room = room = self.get_current_room(payload)
        assert self.LOCATION_SLOT, "self.LOCATION_SLOT is undefined"
        if self.LOCATION_SLOT in payload.slot_values:
            room = payload.slot_values[self.LOCATION_SLOT].value
            if default_room is not None and room in DEFAULT_ROOM_NAMES:
                return default_room
        return room

    def in_current_room(self, payload: IntentPayload) -> bool:
        "Is the current site the disired room?"
        return self.get_room(payload) == self.get_current_room(payload)

    def get_room_name(
        self, payload: IntentPayload, modifier: Callable, default: str | None = None
    ) -> str:
        """Get the recognized room name,
        optionally adding an article or preposition
        """

        room = self.get_room(payload)
        default_room = self.get_current_room(payload)
        if room is not None and default is not None and room == default_room:
            return default
        return modifier(room or _("unknown room"))

    def get_room_config(self, payload: IntentPayload) -> MutableMapping:
        """Get the configuration section for a recognized room.
        :param payload: parsed intent message payload
        :return: room configuration
        """

        room = self.get_room(payload)
        if room and room in self.configuration:
            return self.configuration[room]
        raise SnipsClarificationError(
            _("in which room?"), payload.intent.intent_name, self.LOCATION_SLOT
        )

    def all_rooms(self, payload: IntentPayload) -> bool:
        "Check whether the intent refers to every room at once"
        room = self.get_room(payload)
        if room is not None:
            room = room.lower()
        for name in ALL_ROOMS:
            name = name.lower()
            if name == room or name in payload.input:
                return True
        return False

    def get_site_id(self, payload: IntentPayload) -> str:
        """Obtain a site_id by explicit or implied room name.
        :param payload: parsed intent message payload
        """

        config = self.get_room_config(payload)
        if "site_id" in config:
            return config["site_id"]
        raise SnipsError(_("This room has not been configured yet."))
