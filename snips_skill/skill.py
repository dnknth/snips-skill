from argparse import ArgumentParser
import functools
import gettext, logging, os

try:
    from . import snips
except ImportError:
    import snips


BLUE      = '\033[94m'
GREEN     = '\033[92m'
PURPLE    = '\033[95m'
RED       = '\033[91m'
YELLOW    = '\033[93m'

BOLD      = '\033[1m'
ENDC      = '\033[0m'


def _colorize( color, msg, colored=True):
    "Colorize a string for xterm"
    if not colored: return msg
    return color + msg + ENDC
    

class Skill( snips.Client):
    """
        Base class for Snips actions.
        Sets up logging and provides some skeleton methods for sub-classes.
    """
    
    # Map verbosity argument choices to log levels
    LOG_LEVELS = {
        0: logging.ERROR,
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.DEBUG,
    }
    
    DEFAULT_LOG_LEVEL = 2


    def __init__( self, args=None):
        logging.basicConfig()
        super().__init__()

        self.parser = ArgumentParser()
        self.parser.add_argument( '-v', '--verbosity',
            type=int, choices=[0, 1, 2, 3], default=self.DEFAULT_LOG_LEVEL,
            help='Logging verbosity: 0=errors only, 1=errors and warnings, 2=normal output, 3=debug output')
        self.add_arguments()
        
        self.options = self.parser.parse_args( args)
        self.log.setLevel( self.LOG_LEVELS[ self.options.verbosity])
        self.log.debug( 'Command line options: %s', self.options)
    

    def add_arguments( self):
        "Hook for subclasses to add additional command line options"
        pass
        
        
    def log_intent( self, msg, level=logging.DEBUG, colorize=True):
        "Log an intent message for debugging"
        
        self.log.log( level, '%s %s', _colorize( BLUE, 'intent'.ljust( 8), colorize),
            _colorize( BOLD + GREEN, msg.payload.intent.intent_name, colorize))
        for k in ('site_id', 'input'):
            self.log.log( level, '%s %s', _colorize( BLUE, k.ljust( 8), colorize),
                getattr( msg.payload, k))
        for name, slot in msg.payload.slots.items():
            self.log.log( level, '%s %s', _colorize( PURPLE, name.ljust( 8), colorize),
                slot.value)


def log_intent( method):
    @functools.wraps( method)
    def wrapped( client, userdata, msg):
        try:
            client.log_intent( msg, level=logging.DEBUG, colorize=True)
            return method( client, userdata, msg)
        except snips.SnipsError as e:
            client.end_session( msg.payload.session_id, str( e))
    return wrapped


if __name__ == '__main__': # demo code

    client = Skill().connect()

    @client.on_intent( '#')
    def print_msg( client, userdata, msg):
        client.log_intent( msg, level=logging.INFO)

    client.loop_forever()
