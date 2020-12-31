from . intent import IntentPayload
from . logging import LoggingMixin
from . mqtt import CommandLineMixin
from . snips import *
import logging


if __name__ == '__main__': # demo code

    class Logger( CommandLineMixin, LoggingMixin, SnipsClient):
        
        def __init__( self):
            super().__init__()
            self.parse_args()
    
        @on_intent( '#', log_level=None)
        def intent_logger( self, userdata, msg):
            self.log_intent( IntentPayload( msg.payload), level=logging.INFO)

        @on_end_session()
        @on_continue_session( log_level=None)
        def response_logger( self, userdata, msg):
            self.log_response( msg.payload.get('text'), level=logging.INFO)

    Logger().run()
