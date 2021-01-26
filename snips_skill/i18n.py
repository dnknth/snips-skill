from collections import namedtuple
import gettext, locale, os


__all__ = ('_', 'ALL_ROOMS', 'DEFAULT_ROOM_NAMES', 'ROOMS',
    'ngettext', 'room_with_article', 'room_with_preposition')


# Install translations
_language, _encoding = locale.getlocale()
_translation = gettext.translation( 'snips_skill', 
    languages=[_language], fallback=True,
    localedir=os.path.join( os.path.dirname( __file__), 'locale'))
_  = _translation.gettext
ngettext = _translation.ngettext


RoomName = namedtuple( 'RoomName', 'with_article, with_preposition')

DEFAULT_ROOM_NAMES = (
    _('here'),
    _('this room'),
)

ALL_ROOMS = {
    _('everywhere') : _('everywhere'), 
    _('all rooms')  : _('in all rooms'),
}

ROOMS = {
    # Map translated room names to room names with articles and prepositions
    # for languages that use genders for room names, e.g. German
    _("bathroom").lower():     RoomName( _("the bathroom"),    _("in the bathroom")),
    _("bedroom").lower():      RoomName( _("the bedroom"),     _("in the bedroom")),
    _("dining room").lower():  RoomName( _("the dining room"), _("in the dining room")),
    _("livingroom").lower():   RoomName( _("the livingroom"),  _("in the livingroom")),
    _("kid's room").lower():   RoomName( _("the kid's room"),  _("in the kid's room")),
    _("kitchen").lower():      RoomName( _("the kitchen"),     _("in the kitchen")),
    _("office").lower():       RoomName( _("the office"),      _("in the office")),
    _("hall").lower():         RoomName( _("the hall"),        _("in the hall")),
    _("garden").lower():       RoomName( _("the garden"),      _("in the garden")),
    _("unknown room").lower(): RoomName( _("an unknown room"), _("in an unknown room")),
}

        
def room_with_article( room_name):
    'Get the spoken room name with the definite article'
    room = ROOMS.get( room_name.lower())
    return room.with_article if room \
        else _('the {room}').format( room=room_name)
    

def room_with_preposition( room_name):
    'Get the spoken room name with "in" preposition'
    room = ROOMS.get( room_name.lower())
    return room.with_preposition if room \
        else _('in the {room}').format( room=room_name)
