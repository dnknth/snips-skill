#!/usr/bin/env python3

'''
    Simplistic wrapper for the Paho MQTT client.
'''

from argparse import ArgumentParser
from basecmd import BaseCmd
from functools import wraps
from getpass import getpass
from paho.mqtt.client import Client as PahoClient, MQTTv311
import json, logging, sys


__all__ = ('MqttClient', 'topic', 'CommandLineClient')


class MqttClient(PahoClient):
    'MQTT client'
    
    TCP = 'tcp'
    WEBSOCKETS = 'websockets'
    DEFAULT_PORT = 1883
    DEFAULT_TLS_PORT = 8883
    SUBSCRIPTIONS = {}
    

    def __init__(self, client_id=None, clean_session=True, \
        userdata=None, protocol=MQTTv311, transport=TCP):

        super(MqttClient, self).__init__(client_id,
            clean_session or not client_id,
            userdata, protocol, transport)
        self._tls_initialized = False


    def __enter__(self):
        return self


    def __exit__(self, *exc_info):
        self.disconnect()


    def connect(self, host='localhost', port=DEFAULT_PORT,
            username=None, password=None,
            keepalive=60, bind_address='', use_tls=False):
        'Connect to the MQTT broker'
        
        if username: self.username_pw_set(username, password)
        if use_tls or port == self.DEFAULT_TLS_PORT:
            if not self._tls_initialized: self.tls_set()
        self.log.debug("Connecting to MQTT broker %s as user '%s'",
            host, username or '')
        super().connect(host, port, keepalive, bind_address)
        return self


    def disconnect(self):
        super().disconnect()
        self.log.debug('Disconnected from MQTT broker')


    def reconnect(self):
        self.log.debug('Reconnecting to MQTT broker')
        super().reconnect()
    
        
    def loop_forever(self):
        'Wait for messages and invoke callbacks until interrupted'
        try:
            super().loop_forever()
            
        except KeyboardInterrupt:
            self.log.info('Interrupted by user')
    
    
    def subscribe(self, topic, qos=0):
        'Subscribe to a MQTT topic'
        super().subscribe(topic, qos)
        self.log.debug('Subscribed to MQTT topic: %s', topic)
        
        
    def publish(self, topic, payload=None,
        qos=0, retain=False, log_level=logging.NOTSET):
        'Send an MQTT message'
        
        self.log.log(log_level, 'Publishing: %s = %.20s', topic, payload)
        return super().publish(topic, payload, qos, retain)


    def on_connect(self, client, userdata, flags, rc):
        'Subscribe to MQTT topics'
        
        assert rc == 0, 'Connection failed'
        assert self == client, 'Bad karma'
        self.log.debug('Connected to MQTT broker')
        
        # Register @topic callbacks
        for topic, (callback, qos) in self.SUBSCRIPTIONS.items():
            self.subscribe(topic, qos)
            self.message_callback_add(topic, callback)


    @staticmethod
    def decode_json(payload):
        'Try to decode a message payload as JSON'
        try: return json.loads(payload)
        except ValueError: return payload
    


def topic(topic, qos=0, payload_converter=None, log_level=logging.NOTSET):
    ''' Decorator for callback functions.
        Callbacks are invoked with these positional parameters:
         - client: MqttClient instance
         - msg: MQTT message
         - userdata: User-defined extra data
        Return values are not expected.
        :param topic: MQTT topic, may contain wildcards
        :param qos: MQTT quality of service (default: 0)
        :param payload_converter: unary function to transform the message payload
    '''
    
    assert topic not in MqttClient.SUBSCRIPTIONS, \
        "Topic '%s' is already registered" % topic
    
    def wrapper(method):
        
        @wraps(method)
        def wrapped(client, userdata, msg):
            'Callback for the Paho MQTT client'
            if log_level: 
                client.log.log(log_level, 'Received message: %s', msg.topic)
            if payload_converter: msg.payload = payload_converter(msg.payload)
            
            # User-provided callback
            return method(client, userdata, msg)

        MqttClient.SUBSCRIPTIONS[topic] = (wrapped, qos)
        return wrapped
    return wrapper

 
class CommandLineClient(BaseCmd, MqttClient):
    'Simple MQTT command line client'

    password = None
    
    
    def add_arguments(self):
        'Set up arguments for connection parameters'        
        self.parser.add_argument('-H', '--host', default='localhost',
            help='MQTT host (default: localhost)')
        self.parser.add_argument('-P', '--port', default=MqttClient.DEFAULT_PORT,
            type=int, help='MQTT port (default: %d)' % MqttClient.DEFAULT_PORT)
        self.parser.add_argument('-T', '--tls', action='store_true',
            default=False, help='Use TLS')
        self.parser.add_argument('-u', '--username', nargs='?', help='User name')
        self.parser.add_argument('-p', '--password', action='store_true',
            help='Prompt for password')
    
    
    def parse_args(self):
        super().parse_args()
        if self.options.username and self.options.password:
            self.password = getpass()
        if self.options.tls and self.options.port == MqttClient.DEFAULT_PORT:
            self.options.port = MqttClient.DEFAULT_TLS_PORT
    
    
    def run(self):
        'Connect to MQTT and handle incoming messages'
        try:
            with self.connect(self.options.host, self.options.port,
                self.options.username, self.password, use_tls=self.options.tls):
                    self.loop_forever()
        except:
            if self.options.log_file: self.log.exception('Fatal error')
            raise
    

    def __call__(self):
        'Syntactic sugar for self.run()'
        self.run()
        
        
if __name__ == '__main__': # Demo code

    from colors import cyan
    from shutil import get_terminal_size

    
    class Logger(CommandLineClient):
                
        WIDTH = get_terminal_size().columns
        COLOR = cyan if sys.stderr.isatty() else str
        
        def add_arguments(self):
            super().add_arguments()
            self.parser.add_argument('-t', '--topic', default='#',
                help='MQTT topic (default: #)')
            self.parser.add_argument('-w', '--width', default=self.WIDTH,
                type=int, help='Output width (default: %d)' % self.WIDTH)
            self.parser.add_argument('-j', '--json', action='store_true',
                help='Try to decode JSON payloads')
            self.parser.add_argument('-z', '--clear', action='store_true',
                help='Clear retained messages')

    client = Logger()

    @topic(client.options.topic)
    def print_msg(client, userdata, msg):
        converter = client.decode_json if client.options.json else str
        width = client.options.width - len(msg.topic) - 2
        payload = converter(msg.payload)
        client.log.info('%s: %.*a', client.COLOR(msg.topic), width, payload)
        if client.options.clear and msg.retain and msg.payload:
            client.publish(msg.topic, retain=True)

    client()
