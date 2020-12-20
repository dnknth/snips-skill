import configparser
import gettext, os

try:
    from . snips import SnipsError
    from . i18n import _
except ImportError:
    from snips import SnipsError
    from i18n import _


class SnipsSiteError( SnipsError):
    'Complain about unknown room names or site IDs'
    pass


class MultiRoomConfig:
    
    PREPOSITIONS = {
        # Map translated room names to room names with prepositions
        # for languages that use genders for room names
        _("bathroom").lower():    _("in the bathroom"),
        _("bedroom").lower():     _("in the bedroom"),
        _("dining room").lower(): _("in the dining room"),
        _("livingroom").lower():  _("in the livingroom"),
        _("kid's room").lower():  _("in the kid's room"),
        _("kitchen").lower():     _("in the kitchen"),
        _("office").lower():      _("in the office"),
    }
    
    
    def __init__( self, configuration_file='config.ini', prepositions={}):
        self.config = configparser.ConfigParser()
        self.config.read( configuration_file, encoding='utf-8')
        
        self.config.sites = { self.config[section]['site_id'] : section
            for section in self.config if section != 'DEFAULT' }
            
        self.PREPOSITIONS.update( (k.lower, v)
            for k, v in prepositions.items())


    def get_room_slot( self, payload, slot='room', default_name=''):
        'Get the spoken room name'
        if slot not in payload.slot_values: return default_name
        room = payload.slot_values[ slot].value
        return (default_name if room == _('here').lower()
            else self.preposition( room))
        

    def get_site_id( self, payload, slot='room'):
        ''' Obtain a site_id by room name or message origin.
            :param payload: parsed intent message payload
            :param slot: room slot name
            :return: site ID, or None if no room was given
        '''

        if slot not in payload.slot_values: return 

        room = payload.slot_values[ slot].value
        if room == _("here").lower(): return payload.site_id

        if room not in self.config or 'site_id' not in self.config[ room]:
            raise SnipsSiteError( _("The room {room} is unknown.").format(
                room=room))
        return self.config[ room]['site_id']


    def get_room_name( self, site_id, msg_site_id='', default_name=''):
        'Get the room name for a site_id'
        
        if site_id == msg_site_id: return default_name
        if site_id not in self.config.sites:
            raise SnipsSiteError( _("This room has not been configured yet."))
        return self.preposition( self.config.sites[ site_id])


    def preposition( self, room):
        "Add an 'in the' preposition to a room name"
        return self.PREPOSITIONS.get( room.lower(),
            _("in the {room}").format( room=room))
