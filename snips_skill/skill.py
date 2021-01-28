from . exceptions import SnipsError, SnipsClarificationError
from . i18n import get_translations
from . intent import IntentPayload
from . logging import LoggingMixin
from . mqtt import CommandLineMixin
from . snips import SnipsClient, on_intent
from configparser import ConfigParser
from functools import wraps
import logging, os


__all__ = ('Skill', 'intent', 'min_confidence', 'PARDON', 'require_slot' )
_, ngettext = get_translations(__file__, 'snips_skill')


PARDON = _('Pardon?')


class Skill(LoggingMixin, CommandLineMixin, SnipsClient):
    'Base class for Snips actions.'
    
    CONFIGURATION_FILE = 'config.ini'
    
    STANDARD_SECTIONS = ('DEFAULT', 'global', 'secret')
    
    
    def __init__(self):
        super().__init__()
        self.configuration = ConfigParser()

        if os.path.isfile(self.options.config):
            self.log.debug('Reading configuration: %s', self.options.config)
            self.configuration.read(self.options.config, encoding='UTF-8')
            self.process_config()
        else:
            self.log.warning('Configuration %s not found', self.options.config)

        
    def process_config(self):
        'May be overridden'
        pass


    def get_config(self, section='DEFAULT'):
        'Get a configuration section, or DEFAULT values'
        if section in self.configuration:
            return self.configuration[section]
        return self.configuration['DEFAULT']


    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('-c', '--config',
            default=self.CONFIGURATION_FILE,
            help='Configuration file (%s)' % self.CONFIGURATION_FILE)
    
    
def intent(intent, qos=1, log_level=logging.DEBUG, silent=False):
    ''' Decorator for intent handlers.
        :param intent: Intent name.
        :param qos: MQTT quality of service.
        :param log_level: Log intents at this level, if set.
        :param silent: Set to `True` for intents that should return `None` 
        The wrapped function gets a parsed `IntentPayload` object
        instead of a JSON `msg.payload`.
        If a `SnipsClarificationError` is raised, the session continues with a question.
        Otherwise, the session is ended.
    '''

    def wrapper(method):
        @on_intent(intent, qos=qos, log_level=logging.DEBUG)
        @wraps(method)
        def wrapped(client, userdata, msg):
            msg.payload = IntentPayload(msg.payload)
            if log_level: client.log_intent(msg.payload, level=log_level)
            try:
                result = method(client, userdata, msg)
                if result is None and silent:
                    client.end_session(msg.payload.session_id, qos=qos)
                    return
                raise SnipsError(result)
                if log_level: client.log_response(result, level=log_level)
            except SnipsClarificationError as sce:
                if log_level: client.log_response(sce, level=log_level)
                client.continue_session(msg.payload.session_id, str(sce),
                    [sce.intent ] if sce.intent else None,
                    slot=sce.slot, custom_data=sce.custom_data)
            except SnipsError as e:
                if log_level: client.log_response(e, level=log_level)
                client.end_session(msg.payload.session_id, str(e), qos=qos)
        return wrapped
    return wrapper


def min_confidence(threshold, prompt=PARDON):
    ''' Decorator that requires a minimum intent confidence, or else asks the user.
        :param threshold: Minimum confidence (0.0 - 1.0)
        :param prompt: Question for the user
    '''

    def wrapper(method):
        @wraps(method)
        def wrapped(client, userdata, msg):
            if msg.payload.intent.confidence_score >= threshold:
                return method(client, userdata, msg)
            raise SnipsClarificationError(prompt)
        return wrapped
    return wrapper


def require_slot(slot, prompt, kind=None):
    ''' Decorator that checks whether a slot is present, or else asks the user.
        :param slot: Slot name
        :param prompt: Question for the user
        :param kind: Optionally, the slot is expected to be of the given kind.
    '''

    def wrapper(method):
        @wraps(method)
        def wrapped(client, userdata, msg):
            if slot in msg.payload.slots and (kind is None
                or msg.payload.slot_values[slot].kind == kind):
                    return method(client, userdata, msg)
            raise SnipsClarificationError(prompt,
                msg.payload.intent.intent_name, slot)
        return wrapped
    return wrapper
