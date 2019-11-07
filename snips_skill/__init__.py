from . import mqtt
from . snips import Client, debug_json, end_on_error, end_session, SnipsError
from . skill import log_intent, Skill
from . multi_room import MultiRoomConfig


def use_language( language, path=None):
    """
        Set 'language' as current locale.
        Optionally search for locale in directory 'path'.
        :param locale: language name, eg 'en_GB'
    """
    from . import i18n
    i18n.use_language( language, 'snips_skill', path)
