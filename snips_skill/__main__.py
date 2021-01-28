from . intent import IntentPayload
from . logging import LoggingMixin
from . mqtt import CommandLineMixin
from . snips import *
import logging


if __name__ == '__main__': # demo code

    class Logger( CommandLineMixin, LoggingMixin, SnipsClient):
            
        @on_intent( '#')
        def intent_logger( self, userdata, msg):
            self.log_intent( IntentPayload( msg.payload), level=logging.INFO)

        @on_end_session( log_level=None)
        @on_continue_session()
        def response_logger( self, userdata, msg):
            self.log_response( msg.payload.get('text'), level=logging.INFO)

    Logger().run()
