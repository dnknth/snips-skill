#!/usr/bin/env python3

from . mqtt import MqttClient, MQTTv311, topic
from functools import partial, wraps
import io, json, logging, toml, uuid, wave


__all__ = ('SnipsClient', 'debug_json',
    'on_hotword_detected', 'on_start_session', 'on_session_started', 'on_intent',
    'on_end_session', 'on_continue_session', 'on_session_ended', 'on_play_finished' )


class SnipsClient(MqttClient):
    'Snips client with auto-configuration'
    
    CONFIG = '/etc/snips.toml'
    
    INTENT_PREFIX         = 'hermes/intent/'
    DIALOGUE              = 'hermes/dialogueManager/'
    
    # Session life cycle messages
    HOTWORD_DETECTED      = 'hermes/hotword/+/detected'
    START_SESSION         = DIALOGUE + 'startSession'
    SESSION_QUEUED        = DIALOGUE + 'sessionQueued'
    SESSION_STARTED       = DIALOGUE + 'sessionStarted'
    CONTINUE_SESSION      = DIALOGUE + 'continueSession'
    END_SESSION           = DIALOGUE + 'endSession'
    SESSION_ENDED         = DIALOGUE + 'sessionEnded'
    
    # Misc
    PLAY_BYTES     = 'hermes/audioServer/{site_id}/playBytes/{request_id}'
    PLAY_FINISHED  = 'hermes/audioServer/%s/playFinished'
    REGISTER_SOUND = 'hermes/tts/registerSound/%s'


    def __init__(self, config=CONFIG, 
        client_id=None, clean_session=True, userdata=None,
        protocol=MQTTv311, transport=MqttClient.TCP):
        
        super().__init__(client_id, clean_session, userdata,
            protocol, transport)

        self.log.debug('Loading config: %s', config)        
        self.config = toml.load(config)

        
    def connect(self):
        'Connect to the MQTT broker and invoke callback methods'
        common = self.config.get('snips-common', {})
        
        host, port = None, None
        host_port = common.get('mqtt', 'localhost:1883')
        if host_port:
            if ':' in host_port:
                host, port = host_port.split(':')
                port = int(port)
            else:
                host = host_port
        
        password = None
        username = common.get('mqtt_username')
        if username:
            password = common.get('mqtt_password')
        
        cafile = common.get('mqtt_tls_cafile')
        cert = common.get('mqtt_tls_client_cert')
        key = None if not cert else common.get('mqtt_tls_client_key')
        
        if cafile or cert or port == self.DEFAULT_TLS_PORT:
            assert not common.get('mqtt_tls_hostname'), \
                'mqtt_tls_hostname not supported'
            self.tls_set(ca_certs=cafile, certfile=cert, keyfile=key)
            self._tls_initialized = True
        
        return super().connect(host=host, port=port,
            username=username, password=password)


    # See: https://docs.snips.ai/reference/dialogue#session-initialization-action
    def action_init(self, text=None, intent_filter=[],
            can_be_enqueued=True, send_intent_not_recognized=False):
        'Build the init part of action type to start a session'
        
        init = { 'type' : 'action' }
        if text: init['text'] = str(text)
        if not can_be_enqueued: init['canBeEnqueued'] = False
        if intent_filter: init['intentFilter'] = intent_filter
        if send_intent_not_recognized: init['sendIntentNotRecognized'] = True
        return init


    # See: https://docs.snips.ai/reference/dialogue#session-initialization-notification
    def notification_init(self, text):
        'Build the init part of notification type to start a session'
        return { 'type' : 'notification', 'text' : str(text) }


    # See: https://docs.snips.ai/reference/dialogue#start-session
    def start_session(self, site_id, init, custom_data=None, qos=1):
        'End the session with an optional message'
        payload = { 'siteId': site_id, 'init' : init }
        
        if type(custom_data) in (dict, list, tuple):
            payload['customData'] = json.dumps(custom_data)
        elif custom_data is not None:
            payload['customData'] = str(custom_data)
            
        self.log.debug("Starting %s session on site '%s'", init.get('type'), site_id)
        self.publish(self.START_SESSION, json.dumps(payload), qos=qos)


    def speak(self, site_id, text):
        'Say a one-time notification'
        self.start_session(site_id, self.notification_init(text))
        

    # See: https://docs.snips.ai/reference/dialogue#end-session
    def end_session(self, session_id, text=None, qos=1):
        'End the session with an optional message'
        payload = { 'sessionId': session_id }
        
        if text:
            text = ' '.join(text.split())
            payload['text'] = text

        self.log.debug("Ending session %s with '%s'", session_id, text)
        self.publish(self.END_SESSION, json.dumps(payload), qos=qos)


    # See: https://docs.snips.ai/reference/dialogue#continue-session
    def continue_session(self, session_id, text, intent_filter=None, slot=None,
            send_intent_not_recognized=False, custom_data=None, qos=1):
        'Continue the session with a question'
        
        text = ' '.join(text.split())
        payload = { 'text': text, 'sessionId': session_id }
        if intent_filter: payload['intentFilter'] = intent_filter
        if slot: payload['slot'] = slot
        if send_intent_not_recognized:
            payload['sendIntentNotRecognized'] = bool(send_intent_not_recognized)

        if type(custom_data) in (dict, list, tuple):
            payload['customData'] = json.dumps(custom_data)
        elif custom_data is not None:
            payload['customData'] = str(custom_data)

        self.log.debug("Continuing session %s with '%s'", session_id, text)
        self.publish(self.CONTINUE_SESSION, json.dumps(payload), qos=qos)


    # See: https://docs.snips.ai/reference/dialogue#start-session
    def play_sound(self, site_id, wav_data, request_id=None):
        'Play a WAV sound at the given site'
        if not request_id: request_id = str(uuid.uuid4())
        self.publish(self.PLAY_BYTES.format(site_id=site_id, request_id=request_id), payload=wav_data)
        return request_id


    def register_sound(self, name, wav_data):
        self.publish(self.REGISTER_SOUND % name, wav_data)
        return self


    def run(self):
        'Connect to MQTT and handle incoming messages'
        with self.connect():
            self.loop_forever()


###################################
### Decorators for Snips events ###
###################################

def _load_json(payload):
    'Helper to convert JSON to a Python dict'
    # Only convert if this appears to be a JSON payload.
    # Needed for multiple annotations on a method
    return json.loads(payload) if type(payload) is bytes else payload
    
on_hotword_detected = partial(topic,
    SnipsClient.HOTWORD_DETECTED, payload_converter=_load_json)

on_start_session = partial(topic,
    SnipsClient.START_SESSION, payload_converter=_load_json)

def on_intent(intent, qos=0, log_level=logging.DEBUG):
 return topic('%s%s' % (SnipsClient.INTENT_PREFIX, intent),
     qos=qos, payload_converter=_load_json, log_level=log_level)

on_continue_session = partial(topic,
    SnipsClient.CONTINUE_SESSION, payload_converter=_load_json)

on_session_queued = partial(topic,
    SnipsClient.SESSION_QUEUED, payload_converter=_load_json)

on_session_started = partial(topic,
    SnipsClient.SESSION_STARTED, payload_converter=_load_json)

on_end_session = partial(topic,
    SnipsClient.END_SESSION, payload_converter=_load_json)

on_session_ended = partial(topic,
    SnipsClient.SESSION_ENDED, payload_converter=_load_json)

def on_play_finished(site='+', qos=0, log_level=logging.DEBUG):
    return topic(SnipsClient.PLAY_FINISHED % site,
        qos=qos, payload_converter=_load_json, log_level=log_level)


def debug_json(keys=[]):
    'Decorator to debug message payloads'
    def wrapper(method):
        @wraps(method)
        def wrapped(client, userdata, msg):
            if type(msg.payload) is dict:
                data = msg.payload
                if keys: data = { k: v for k, v in data.items()
                    if not keys or k in keys }
                client.log.debug('Payload: %s',
                    json.dumps(data, sort_keys=True, indent=2))
            return method(client, userdata, msg)
        return wrapped
    return wrapper
