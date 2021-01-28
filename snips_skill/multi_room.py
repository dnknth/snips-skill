from . exceptions import SnipsError, SnipsClarificationError
from . i18n import *


__all__ = ('MultiRoomConfig', 'ROOMS', 'room_with_article', 'room_with_preposition')

_, ngettext = get_translations(__file__, 'snips_skill')


class MultiRoomConfig:
    ''' Mixin for multi-site actions.
        Contains helper methods to extract location slots,
        look up room names, associated configuration and site IDs.
    '''
    
    LOCATION_SLOT = None # Override as needed, e.g. 'room'


    def process_config(self):
        'Load all non-standard config sections as rooms'
        self.sites = { self.configuration[section]['site_id'] : section
            for section in self.configuration
            if section not in self.STANDARD_SECTIONS
                and 'site_id' in self.configuration[section] }


    def add_room_name(self, room, with_article, with_preposition):
        'Register additional room names with articles and prepositions'
        ROOMS[room.lower()] = RoomName(with_article, with_preposition)


    def get_current_room(self, payload):
        'Get the room name of the current site'
        return self.sites.get(payload.site_id)

        
    def get_room(self, payload):
        'Get the recognized room name'
        
        default_room = room = self.get_current_room(payload)
        assert self.LOCATION_SLOT, 'self.LOCATION_SLOT is undefined'
        if self.LOCATION_SLOT in payload.slot_values:
            room = payload.slot_values[self.LOCATION_SLOT].value
            if default_room and room in DEFAULT_ROOM_NAMES:
                return default_room
        return room
                

    def in_current_room(self, payload):
        'Is the current site the disired room?'
        return self.get_room(payload) == self.get_current_room(payload)

        
    def get_room_name(self, payload, modifier=str, default=None):
        ''' Get the recognized room name,
            optionally adding an article or preposition
        '''
        
        room = self.get_room(payload)
        default_room = self.get_current_room(payload)
        if room and default is not None and room == default_room:
            return default
        return modifier(room or _('unknown room'))


    def get_room_config(self, payload):
        ''' Get the configuration section for a recognized room.
            :param payload: parsed intent message payload
            :return: room configuration
        '''

        room = self.get_room(payload)
        if room in self.configuration: return self.configuration[room]
        raise SnipsClarificationError(_('in which room?'),
            payload.intent.intent_name, self.LOCATION_SLOT)

    
    def all_rooms(self, payload):
        'Check whether the intent refers to every room at once'
        room = self.get_room(payload).lower()
        for name in ALL_ROOMS:
            name = name.lower()
            if name == room or name in payload.input:
                return True
        

    def get_site_id(self, payload):
        ''' Obtain a site_id by explicit or implied room name.
            :param payload: parsed intent message payload
        '''
        
        config = self.get_room_config(payload)
        if 'site_id' in config: return config['site_id']
        raise SnipsError(_('This room has not been configured yet.'))
