from argparse import FileType
from json import dump, dumps, load
from pathlib import Path
import logging, sys

try:
    from . import skill, snips
except ImportError:
    import skill, snips


class TestRunner( skill.Skill):

    def __init__( self, args=None):

        self.test = None
        super().__init__( args)
        
        self.on_session_started()( self._on_start)
        for event in ('%s/#' % self.INTENT, self.CONTINUE_SESSION, self.END_SESSION):
            self.topic( event, payload_converter=snips.parse_json)( self._handle)
        self.on_session_ended()( self._on_end)

        self.events = []
        self.tests = []
        self.failures = 0
        for test_spec in self.options.tests:
            with test_spec:
                self.tests.append( load( test_spec))


    def add_arguments( self):
        self.parser.add_argument( '-l', '--log-dir',
            type=Path, nargs='?', help='Directory to log JSON messages')
        self.parser.add_argument( '-s', '--site-id',
            default='test', help='Site ID (default: test)')
        self.parser.add_argument( 'tests', nargs='*', type=FileType('r'),
            metavar='JSON_TEST', help='JSON test spec')
            
    
    def on_connect( self, client, userdata, flags, rc):
        super().on_connect( client, userdata, flags, rc)
        if not self.tests and not self.options.log_dir:
            self.log.info( "Nothing to do, exiting")
            self.disconnect()
        self.start_session( self.options.site_id, self.action_init())


    def _on_start( self, client, userdata, msg):
        if self.events: self._flush_log()
        self.session_id = msg.payload['sessionId']
        self.log.debug( "Session started: %s", self.session_id)
        if self.tests:
            self.log.info( "Running test %s", self.session_id)
            self.test = self.tests.pop( 0)
        self._handle( client, userdata, msg)

        
    def _on_end( self, client, userdata, msg):
        self._flush_log()
        if self.test:
            self.log.error( "Test has %d remaining steps" % len( self.test))
            self.failures += 1
            
        self.log.debug( "Session ended: %s", msg.payload['sessionId'])
        if not self.tests and not self.options.log_dir:
            self.log.info( "No more tests, exiting")
            self.disconnect()
        self.start_session( self.options.site_id, self.action_init())

        
    def _flush_log( self):
        if self.events and self.options.log_dir:
            path = self.options.log_dir / ('%s.json' % self.session_id)
            self.log.info( "Logging session to %s", path)
            with open( path, 'w') as out:
                dump( self.events, out,
                    ensure_ascii=False, sort_keys=True, indent=2)
        self.events = []


    def _handle( self, client, userdata, msg):
        self.events.append( {
            'event': None,
            'action': None,
            'topic': msg.topic,
            'payload': msg.payload })
            
        if not self.test: return
        step = self.test.pop( 0)
        
        try:
            assert 'event' in step, "Event missing in test specification"
            assert step['event'] == msg.topic, "Expected: %s, received: %s" % (
                step['event'], msg.topic)

            if not 'action' in step or not step['action']: return
            action = step['action']
        
            if action == 'publish':
                assert 'topic' in step, "Message topic is missing"
                assert 'payload' in step, "Message payload is missing"
                payload = step['payload']
                payload['siteId'] = self.options.site_id
                payload['sessionId'] = self.session_id
            
                self.test.insert( 0, { 'event': step['topic'] })
                self.publish( step['topic'], dumps( payload))
                
        except AssertionError as e:
            self.log.error( str( e))
            self.failures += 1
            self.test = None


if __name__ == '__main__':

    client = TestRunner().connect()
    client.loop_forever()
    sys.exit( client.failures)
