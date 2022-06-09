from . mqtt import topic
import re


__all__ = ('StateAwareMixin',)


class StateAwareMixin:
    ''' Mixin for stateful skills.
        Status updates are recorded in-memory from MQTT topics,
        e.g. `status/#`.
        The message payload for status updates is JSON-converted if possible.
        The last known state is available in `self.current_state`.
        Subclasses may define handler methods for particular topics,
        e.g. `on_status_lamp_brightness(payload)`.
    '''
    
    def __init__(self):
        'Register topics and the state callcack.'
        
        super().__init__()
        self.current_state = {}

        status_topic = self.get_config().get('status_topic')
        assert status_topic, 'status_topic not found in configuration'

        # Subscribe to status updates
        register = topic(status_topic, payload_converter=self.decode_json)
        register(self.update_status)


    @staticmethod
    def update_status(self, _userdata, msg):
        ''' Track the global state,
            and invoke handler methods defined by subclasses
            with the message payload.
        '''
        if self.on_status_update(msg.topic, msg.payload):
            self.invoke_handlers(msg.topic, msg.payload)


    def on_status_update(self, topic, payload):
        ''' Keep the global state in-memory.
            Returns a path to the updated attribute in `self.current_state`
            when the state has changed, or `None` otherwise.
        '''
        # Update only if the value has changed
        if self.current_state.get(topic) != payload:
            self.current_state[topic] = payload
            self.log.debug('Updated: %s = %s', topic, payload)
            return topic
    
    
    def invoke_handlers(self, topic, payload):
        ''' Generic handler for status updates,
            invokes topic specific handlers.
        '''
        method_name = 'on_%s' % topic.replace('/', '_')
        if hasattr(self, method_name):
            handler = getattr(self, method_name)
            self.log.debug('Invoking: %s', method_name)
            handler(payload)
