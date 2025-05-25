import logging

from basecmd import BaseCmd

from .intent import IntentPayload
from .log import LoggingMixin
from .snips import SnipsClient, on_continue_session, on_end_session, on_intent


class Logger(BaseCmd, LoggingMixin, SnipsClient):
    @on_intent("#")
    # Do not use @intent here because it ends the session,
    # and thus interferes with other intent handlers
    def intent_logger(self, userdata, msg):
        self.log_intent(IntentPayload.model_validate(msg.payload), level=logging.INFO)

    @on_end_session()
    @on_continue_session()
    def response_logger(self, userdata, msg):
        self.log_response(msg.payload.get("text"), level=logging.INFO)


def main():
    Logger().run()


if __name__ == "__main__":  # demo code
    main()
