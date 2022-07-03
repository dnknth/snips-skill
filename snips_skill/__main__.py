from . intent import IntentPayload
from . logging import LoggingMixin
from . snips import *
from basecmd import BaseCmd
import logging


if __name__ == '__main__': # demo code

    class Logger(BaseCmd, LoggingMixin, SnipsClient):
            
        @on_intent('#')
        # Do not use @intent here because it ends the session,
        # and thus interferes with other intent handlers
        def intent_logger(self, userdata, msg):
            self.log_intent(IntentPayload(msg.payload), level=logging.INFO)

        @on_end_session()
        @on_continue_session()
        def response_logger(self, userdata, msg):
            self.log_response(msg.payload.get('text'), level=logging.INFO)

    Logger().run()
