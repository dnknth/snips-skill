from argparse import ArgumentTypeError, FileType
from colors import red, green, yellow, blue, magenta, cyan
from datetime import datetime
from pathlib import Path
import json, logging

from . logging import LoggingMixin
from . mqtt import *
from . snips import *


class TestRunner( CommandLineMixin, LoggingMixin, SnipsClient):
    'Record Snips sessions and play them back'

    def __init__( self):
        super().__init__()
        
        self.test = None
        self.events = []
        self.failures = 0
        

    def add_arguments( self):
        super().add_arguments()
        self.parser.add_argument( '-d', '--log-dir',
            type=Path, nargs='?', help='Directory to log JSON messages')
        self.parser.add_argument( '-i', '--ignore-text', action='store_true',
            help='Do not compare TTS message texts')
        self.parser.add_argument( '-l', '--loop', action='store_true',
            help='Keep recording until interrupted')
        self.parser.add_argument( 'tests', nargs='*', type=self._json_file,
            metavar='JSON_TEST', help='JSON test spec')
    
         
    def _json_file( self, path):
        if Path( path).suffix != '.json':
            raise ArgumentTypeError( '%s is not a JSON file' % path) 
        return FileType('r')( path)
    
        
    def on_connect( self, client, userdata, flags, rc):
        super().on_connect( client, userdata, flags, rc)
        
        if self.options.log_dir: # Start recording
            if not self.options.log_dir.is_dir():
                self.log.error( 'No such directory: %s', self.options.log_dir)
                return self._exit()
            self.log.info( 'Waiting for session...')
        
        elif self.options.tests: self._start_session()
        else: self._exit( 'Nothing to do, exiting')

    
    def _start_session( self):
        with self.options.tests.pop( 0) as test:
            self.test = json.load( test)
        site_id = self.test[0].get( 'payload', {}).get( 'siteId')
        self.start_session( site_id, self.action_init())


    @on_session_started()
    def _on_start( self, userdata, msg):
        if self.options.log_dir: return # Recording

        try:
            self.session_id = msg.payload.get( 'sessionId')
            self.log.debug( 'Session started: %s', self.session_id)
    
            assert self.test, 'No test steps remaining'
            step = self.test[0]

            topic = step.get( 'topic')
            assert topic, 'Message topic is missing'
            assert topic.startswith( self.INTENT_PREFIX), \
                'Intent expected, but got: %s' % topic

            payload = step.get( 'payload')
            assert payload, 'Message payload is missing'
            payload['sessionId'] = self.session_id

            self.log.info( 'Starting test %s with %d steps',
                step.get('time'), len( self.test))
            self.publish( topic, json.dumps( payload))
            return
            
        except AssertionError as e:
            self._fail( e)    
        self._exit()


    @on_intent('#', log_level=None)
    @on_continue_session( log_level=None)
    @on_end_session( log_level=None)
    def _handle( self, userdata, msg):
        self.log.debug( 'Received message: %s', msg.topic)
        if self.options.log_dir:
            self.events.append( {
                'time': datetime.now().isoformat(),
                'topic': msg.topic,
                'payload': msg.payload })
            return

        # Ignore other sessions that are unrelated to the current test
        if msg.payload and msg.payload.get( 'sessionId') != self.session_id:
            return

        try:
            assert self.test, 'Test has already finished'
            step = self.test.pop( 0)
            topic = step.get( 'topic')
            assert topic, 'Test topic is missing'
            self.log.debug( 'Test step: %s', topic)
            
            assert topic == msg.topic, \
                'Expected topic: %s, received: %s' % (topic, msg.topic)

            payload = step.get( 'payload')
            assert payload, 'Test payload is missing'
            
            text = msg.payload.get( 'text')
            assert (self.options.ignore_text or payload.get('text') == text), \
                'Expected text: %s, received: %s' % (payload.get('text'), text)

            if topic.startswith( self.INTENT_PREFIX):
                self.tabular_log( logging.INFO, 'intent', topic, label_color=green)
            else: self.tabular_log( logging.INFO, 'topic', topic, label_color=cyan)
            if text: self.tabular_log( logging.INFO, 'text', text, label_color=cyan)
            
        except AssertionError as e: self._fail( e)


    @on_session_ended()
    def _on_end( self, userdata, msg):
        if self.test:
            self._fail( 'Test has %d remaining steps' % len( self.test))
        self.log.debug( 'Session ended: %s', msg.payload['sessionId'])
        if self.options.tests: self._start_session()
        else: self._exit()


    def _fail( self, e):
        self.colored_log( logging.ERROR, '%s', e, color=red)
        self.failures += 1
        self.test = None


    def _exit( self, msg='Exiting'):
        if self.events:
            event = self.events[0]
            intent = event['topic'].replace( self.INTENT_PREFIX, '')
            file_name = '%s-%s.json' % ( event['time'], intent)
            path = self.options.log_dir / file_name
            self.log.info( 'Logging session to %s', path)
            with open( path, 'w') as out:
                json.dump( self.events, out, ensure_ascii=False, indent=2)
            self.events = []
            
        if not (self.options.log_dir and self.options.loop):
            self.log.debug( msg)
            self.disconnect()


if __name__ == '__main__':
    import sys

    client = TestRunner()
    client.run()
    sys.exit( client.failures)
