#!/usr/bin/env python3

"""
    Simplistic wrapper for the Paho MQTT client.
"""

import functools
import logging
from paho.mqtt.client import Client as PahoClient, MQTTv311
from paho.mqtt.publish import single


class Client( PahoClient):
    'MQTT client'
    
    TCP = "tcp"
    WEBSOCKETS = "websockets"
    DEFAULT_PORT = 1883
    DEFAULT_TLS_PORT = 8883
    

    def __init__( self, client_id=None, clean_session=True, \
        userdata=None, protocol=MQTTv311, transport=TCP):

        super().__init__( client_id, clean_session or not client_id,
            userdata, protocol, transport)
        self._subscriptions = {}
        self._tls_initialized = False
        self.log = logging.getLogger( self.__class__.__name__)
        self.log.setLevel( logging.WARNING)


    def connect( self, host='localhost', port=DEFAULT_PORT,
            username=None, password=None,
            keepalive=60, bind_address="", use_tls=False):
        "Connect to the MQTT broker"
        
        if username: self.username_pw_set( username, password)
        if use_tls or port == self.DEFAULT_TLS_PORT:
            if not self._tls_initialized: self.tls_set()
        self.log.debug( "Connecting to MQTT broker %s as user '%s'",
            host, username or '')
        super().connect( host, port, keepalive, bind_address)
        self.log.info( "Connected to MQTT broker: %s", host)
        return self

    
    def loop_forever( self):
        "Wait for messages and invoke callbacks until interrupted"
        try:
            super().loop_forever()
            
        except KeyboardInterrupt:
            self.log.debug( "Interrupted by user")
            
        finally:
            self.disconnect()
        
        
    def topic( self, topic, qos=0, payload_converter=None):
        """ Decorator for callback functions.
            Callbacks are invoked with two positional parameters:
             - msg: MQTT message
             - userdata: User-defined extra data
            Return values are not expected.
            :param topc: MQTT topic, may contain wildcards
            :param qos: MQTT quality of service (default: 0)
            :param payload_converter: unary function to transform the message payload
        """
        
        assert topic not in self._subscriptions, \
            "Topic '%s' is already registered" % topic
        
        def wrapper( method):
            
            @functools.wraps( method)
            def wrapped( client, userdata, msg):
                "Callback for the Paho MQTT client"
                self.log.debug( 'Received message: %s', msg.topic)
                if payload_converter: msg.payload = payload_converter( msg.payload)
                
                # User-provided callback
                method( client, userdata, msg)

            self._subscriptions[ topic] = (wrapped, qos)
            return wrapped
        return wrapper
        
        
    def publish( self, topic, payload=None, qos=0, retain=False):
        "Send an MQTT message"
        self.log.debug( 'Publishing: %s', topic)
        return super().publish( topic, payload, qos, retain)


    def on_connect( self, client, userdata, flags, rc):
        "Subscribe to MQTT topics"
        
        assert rc == 0, "Connection failed"

        for topic, (callback, qos) in self._subscriptions.items():
            self.subscribe( topic, qos)
            self.message_callback_add( topic, callback)
            self.log.debug( 'Subscribed to MQTT topic: %s', topic)


if __name__ == '__main__': # Demo code
    
    from argparse import ArgumentParser
    from getpass import getpass
    import shutil
    
    parser = ArgumentParser()
    parser.add_argument( '-H', '--host', default='localhost',
        help='MQTT host (default: localhost)')
    parser.add_argument( '-P', '--port', default=Client.DEFAULT_PORT,
        type=int, help='MQTT port (default: %d)' % Client.DEFAULT_PORT)
    parser.add_argument( '-T', '--tls', action='store_true',
        default=False, help='Use TLS')
    parser.add_argument( '-u', '--username', nargs='?', help='User name')
    parser.add_argument( '-p', '--password', action='store_true',
        help='Prompt for password')
    parser.add_argument( '-t', '--topic', default='#',
        help='MQTT topic (default: #)')
    parser.add_argument( '-z', '--clear', action='store_true',
        help='Clear retained messages')
    
    options = parser.parse_args()
    password = getpass() if options.username and options.password else None
    port = Client.DEFAULT_TLS_PORT if options.tls \
        and options.port == Client.DEFAULT_PORT else options.port
    client = Client().connect( options.host, port,
        options.username, password, use_tls=options.tls)
    columns = shutil.get_terminal_size().columns
    
    @client.topic( options.topic)
    def print_msg( client, userdata, msg):
        print( ("%s: %s" % (msg.topic, msg.payload))[:columns])
        if options.clear and msg.retain and msg.payload:
            client.publish( msg.topic, retain=True)
    
    client.loop_forever()
