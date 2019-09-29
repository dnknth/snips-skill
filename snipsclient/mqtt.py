#!/usr/bin/env python3

"""
    Simplistic wrapper for the Paho MQTT client.
"""

from json import dumps, loads
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


    def run( self, host='localhost', port=DEFAULT_PORT,
        username=None, password=None,
        keepalive=60, bind_address="", use_tls=False):
        "Connect to the MQTT broker and invoke callback methods"
        
        if username: self.username_pw_set( username, password)
        if use_tls or port == self.DEFAULT_TLS_PORT:
            if not self._tls_initialized: self.tls_set()
        self.connect( host, port, keepalive, bind_address)
        self.loop_forever()
        
        
    def topic( self, topic, qos=0, json=False):
        """ Decorator for callback functions.
            Callbacks are invoked with two positional parameters:
             - msg: MQTT message
             - userdata: User-defined extra data
            Return values are not expected.
        """
        
        assert topic not in self._subscriptions, \
            "Topic '%s' is already registered" % topic
            
        def wrapper( method):
            def wrapped( client, userdata, msg):
                "Callback for the Paho MQTT client"
                if json: msg.payload = loads( msg.payload.decode())
                # User-provided callback
                method( client, userdata, msg)

            self._subscriptions[ topic] = (wrapped, qos)
            return wrapped
        return wrapper


    def on_connect( self, client, userdata, flags, rc):
        "Subscribe to MQTT topics"
        
        assert rc == 0, "Connection failed"

        for topic, (callback, qos) in self._subscriptions.items():
            self.subscribe( topic, qos)
            self.message_callback_add( topic, callback)


    def publish( self, topic, payload=None, qos=0, retain=False, json=False):
        "Publish a payload to a MQTT topic"
        
        if json and payload: payload = dumps( payload)
        return super().publish( topic, payload, qos, retain)


if __name__ == '__main__': # Demo code

    import sys
    client = Client()
    
    @client.topic( sys.argv[2] if len( sys.argv) > 2 else '#')
    def print_msg( client, userdata, msg):
        print( ("%s: %s" % (msg.topic, msg.payload))[:80])
    
    client.run( sys.argv[1] if len( sys.argv) > 1 else 'localhost')
