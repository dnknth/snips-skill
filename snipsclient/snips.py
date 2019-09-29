#!/usr/bin/env python3

import json
import toml

try:
    from . import mqtt
except ImportError:
    import mqtt


class Client( mqtt.Client):
    "MQTT client with auto-configuration from snips.toml"
    
    CONFIG = '/etc/snips.toml'
    
    INTENT = 'hermes/intent'
    END_SESSION = 'hermes/dialogueManager/endSession'
    CONTINUUE_SESSION = 'hermes/dialogueManager/continueSession'
    INTENT_NOT_RECOGNIZED = 'hermes/dialogueManager/intentNotRecognized'
    SESSION_ENDED = 'hermes/dialogueManager/sessionEnded'


    def __init__( self, config=CONFIG, 
        client_id=None, clean_session=True, userdata=None,
        protocol=mqtt.MQTTv311, transport=mqtt.Client.TCP):
        
        super().__init__( client_id, clean_session, userdata,
            protocol, transport)
        self.config = toml.load( config)

        
    def run( self):
        "Connect to the MQTT broker and invoke callback methods"
        common = self.config.get( 'snips-common', {})
        
        host, port = None, None
        host_port = common.get( 'mqtt')
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
                "mqtt_tls_hostname not yet implemented"
            self.tls_set( ca_certs=cafile, certfile=cert, keyfile=key)
            self._tls_initialized = True
        
        super().run( host=host, port=port, username=username, password=password)


    def intent( self, intent, qos=1):
        'Decorator for intent callbacks'
        return self.topic( '%s/%s' % (self.INTENT, intent), qos, True)


    def intent_not_recognized( self, qos=1):
        'Decorator for intent callbacks'
        return self.topic( self.INTENT_NOT_RECOGNIZED, qos, True)


    def session_ended( self, qos=1):
        'Decorator for intent callbacks'
        return self.topic( self.SESSION_ENDED, qos, True)


    # See: https://docs.snips.ai/reference/dialogue#outbound-message-2
    def end_session( self, session_id, text=None, qos=1):
        'End the session with an optional message'
        payload = { 'sessionId': session_id }
        if text: payload[ 'text'] = text
        self.publish( self.END_SESSION, payload, qos=qos, json=True)


    # See: https://docs.snips.ai/reference/dialogue#outbound-message-1
    def continue_session( self, session_id, text, intent_filter=None, slot=None,
            send_intent_not_recognized=False, custom_data=None, qos=1):
        'Continue the session with a question'
        
        payload = { 'text': text, 'sessionId': session_id }
        if intent_filter: payload[ 'intentFilter'] = intent_filter
        if slot: payload[ 'slot'] = slot
        if send_intent_not_recognized:
            payload[ 'sendIntentNotRecognized'] = bool( send_intent_not_recognized)
        if custom_data:
            if type( custom_data) is dict:
                payload[ 'customData'] = json.dumps( custom_data)
            else:
                payload[ 'customData'] = str( custom_data)

        self.publish( self.CONTINUE_SESSION, payload, qos=qos, json=True)


if __name__ == '__main__': # Demo code

    BLUE      = '\033[94m'
    GREEN     = '\033[92m'
    PURPLE    = '\033[95m'
    RED       = '\033[91m'
    YELLOW    = '\033[93m'
    
    BOLD      = '\033[1m'
    ENDC      = '\033[0m'

    client = Client()

    @client.topic( 'hermes/nlu/intentParsed/#', json=True)
    def print_msg( client, userdata, msg):
        w = max( map( len, msg.payload.keys()))
        print()
        print( BOLD + GREEN + msg.topic + ENDC + ':')
        for k, v in sorted( msg.payload.items()):
            print( YELLOW, k.ljust( w) + ENDC, v)

    client.run()
