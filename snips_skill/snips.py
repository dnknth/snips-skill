#!/usr/bin/env python3

import functools
from json import dumps, loads
import toml
import uuid

try:
    from . import intent
    from . import mqtt
except ImportError:
    import intent, mqtt


class SnipsError( Exception):
    'Signal that an intent cannot be handled'
    pass


def parse_json( payload):
    'parse msg.payload as JSON'
    return loads( payload.decode())
    

class Client( mqtt.Client):
    "Snips client with auto-configuration"
    
    CONFIG = '/etc/snips.toml'
    
    INTENT   = 'hermes/intent'
    DIALOGUE = 'hermes/dialogueManager/'
    
    # Session life cycle messages
    START_SESSION         = DIALOGUE + 'startSession'
    SESSION_STARTED       = DIALOGUE + 'sessionStarted'
    INTENT_NOT_RECOGNIZED = DIALOGUE + 'intentNotRecognized'
    CONTINUE_SESSION      = DIALOGUE + 'continueSession'
    END_SESSION           = DIALOGUE + 'endSession'
    SESSION_ENDED         = DIALOGUE + 'sessionEnded'
    
    # Misc
    PLAY_BYTES = 'hermes/audioServer/{site_id}/playBytes/{request_id}'


    def __init__( self, config=CONFIG, 
        client_id=None, clean_session=True, userdata=None,
        protocol=mqtt.MQTTv311, transport=mqtt.Client.TCP):
        
        super().__init__( client_id, clean_session, userdata,
            protocol, transport)

        self.log.debug( "Loading config: %s", config)        
        self.config = toml.load( config)

        
    def run( self):
        "Connect to the MQTT broker and invoke callback methods"
        common = self.config.get( 'snips-common', {})
        
        host, port = None, None
        host_port = common.get( 'mqtt', 'localhost:1883')
        if host_port:
            if ':' in host_port:
                host, port = host_port.split( ':')
                port = int( port)
            else:
                host = host_port
        
        password = None
        username = common.get( 'mqtt_username')
        if username:
            password = common.get( 'mqtt_password')
        
        cafile = common.get( 'mqtt_tls_cafile')
        cert = common.get( 'mqtt_tls_client_cert')
        key = None if not cert else common.get( 'mqtt_tls_client_key')
        
        if cafile or cert or port == self.DEFAULT_TLS_PORT:
            assert not common.get( 'mqtt_tls_hostname'), \
                "mqtt_tls_hostname not supported"
            self.tls_set( ca_certs=cafile, certfile=cert, keyfile=key)
            self._tls_initialized = True
        
        super().run( host=host, port=port, username=username, password=password)


    def on_session_started( self, qos=1, payload_converter=parse_json):
        'Decorator for session start handler methods'
        return self.topic( self.SESSION_STARTED, qos=qos,
            payload_converter=payload_converter)


    def on_session_ended( self, qos=1, payload_converter=parse_json):
        'Decorator for session end handler methods'
        return self.topic( self.SESSION_ENDED, qos=qos,
            payload_converter=payload_converter)


    def on_intent( self, intent, qos=1, payload_converter=intent.parse_intent):
        'Decorator for intent handler methods'
        return self.topic( '%s/%s' % (self.INTENT, intent), qos=qos,
            payload_converter=payload_converter)


    def on_intent_not_recognized( self, qos=1, payload_converter=parse_json):
        'Decorator for unknown intent handler methods'
        return self.topic( self.INTENT_NOT_RECOGNIZED, qos=qos,
            payload_converter=payload_converter)


    # See: https://docs.snips.ai/reference/dialogue#session-initialization-action
    def action_init( self, text=None, intent_filter=[],
            can_be_enqueued=True, send_intent_not_recognized=False):
        'Build the init part of action type to start a session'
        
        init = { "type" : "action" }
        if text: init[ "text"] = str( text)
        if not can_be_enqueued: init[ "canBeEnqueued"] = False
        if intent_filter: init[ "intentFilter"] = intent_filter
        if send_intent_not_recognized: init[ "sendIntentNotRecognized"] = True
        return init


    # See: https://docs.snips.ai/reference/dialogue#session-initialization-notification
    def notification_init( self, text):
        'Build the init part of notification type to start a session'
        return {
            "type" : "notification",
            "text" : str( text)
        }


    # See: https://docs.snips.ai/reference/dialogue#start-session
    def start_session( self, site_id, init, custom_data=None, qos=1):
        'End the session with an optional message'
        payload = {
            'siteId': site_id,
            'init' : init
        }
        
        if type( custom_data) in (dict, list, tuple):
            payload[ 'customData'] = dumps( custom_data)
        elif custom_data is not None:
            payload[ 'customData'] = str( custom_data)
            
        self.log.debug( "Starting %s session on site '%s'", init.get( 'type'), site_id)
        self.publish( self.START_SESSION, dumps( payload), qos=qos)


    # See: https://docs.snips.ai/reference/dialogue#end-session
    def end_session( self, session_id, text=None, qos=1):
        'End the session with an optional message'
        payload = { 'sessionId': session_id }
        
        if text:
            text = ' '.join( text.split())
            payload[ 'text'] = text
            self.log.debug( "Ending session %s with message: %s",
                session_id, text)
                
        else: self.log.debug( "Ending session %s", session_id)
            
        self.publish( self.END_SESSION, dumps( payload), qos=qos)


    # See: https://docs.snips.ai/reference/dialogue#continue-session
    def continue_session( self, session_id, text, intent_filter=None, slot=None,
            send_intent_not_recognized=False, custom_data=None, qos=1):
        'Continue the session with a question'
        
        text = ' '.join( text.split())
        payload = { 'text': text, 'sessionId': session_id }
        if intent_filter: payload[ 'intentFilter'] = intent_filter
        if slot: payload[ 'slot'] = slot
        if send_intent_not_recognized:
            payload[ 'sendIntentNotRecognized'] = bool( send_intent_not_recognized)

        if type( custom_data) in (dict, list, tuple):
            payload[ 'customData'] = dumps( custom_data)
        elif custom_data is not None:
            payload[ 'customData'] = str( custom_data)

        self.log.debug( "Continuing session %s with message: %s", session_id, text)
        self.publish( self.CONTINUE_SESSION, dumps( payload), qos=qos)


    # See: https://docs.snips.ai/reference/dialogue#start-session
    def play_sound( self, site_id, wav_data, request_id=None):
        'Play a WAV sound at the given site'
        if not request_id: request_id = str( uuid.uuid4())
        self.publish( self.PLAY_BYTES.format( site_id=site_id, request_id=request_id), payload=wav_data)
        return request_id


def debug_json( *keys):
    'Decorator to debug message payloads'

    def wrapper( method):
        @functools.wraps( method)
        def wrapped( client, userdata, msg):
            if type( msg.payload) is dict:
                data = msg.payload
                if keys: data = { k: v for k, v in data.items() if k in keys }
                client.log.debug( 'Payload: %s',
                    dumps( data, sort_keys=True, indent=4))
            return method( client, userdata, msg)
        return wrapped
    return wrapper


def end_on_error( method):
    "Decorator to end a session on SnipsError."
    
    @functools.wraps( method)
    def wrapped( client, userdata, msg):
        try:
            return method( client, userdata, msg)
        except SnipsError as e:
            client.end_session( msg.payload.session_id, str( e))
    return wrapped


def end_session( method):
    """
        Decorator to end a session with an optional message.
        The decorated function should either return a string, or throw a SnipsError.
    """
    
    @functools.wraps( method)
    def wrapped( client, userdata, msg):
        client.end_session( msg.payload.session_id, 
            method( client, userdata, msg))
    return end_on_error( wrapped)
