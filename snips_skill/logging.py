from colors import red, green, yellow, blue, magenta, cyan
from functools import partial
import logging, re, sys

__all__ = ( 'LoggingMixin', )


class LoggingMixin:
    'Logging for Snips events'
    
    INDENT = 10
    STRIP_COLOR = partial( re.compile( '\x1b\\[(K|.*?m)').sub, '')
    COLORIZE = str if sys.stdout.isatty() else STRIP_COLOR


    def colored_log( self, level, format, *args, color=str):
        self.log.log( level, format, *map( self.COLORIZE,
            map( color, args)))
    

    def tabular_log( self, level, key, value, label_color=str, width=INDENT):
        label = label_color( '%-*s') % (width, key)
        self.colored_log( level, '%s %s', label, str( value))
    
    
    def log_intent( self, payload, level=logging.DEBUG):
        'Log an intent message'
        self.tabular_log( level, 'intent', '%s, confidence: %.1f' % (
            red( payload.intent.intent_name, style='bold'),
            payload.intent.confidence_score), label_color=green)
        for k in ('site_id', 'input'):
            self.tabular_log( level, k, getattr( payload, k), label_color=cyan)
        for name, slot in payload.slots.items():
            self.tabular_log( level, name, slot.value, label_color=magenta)
        if payload.custom_data:
            self.tabular_log( level, 'data', payload.custom_data, label_color=yellow)
            
    
    def log_response( self, response, level=logging.DEBUG):
        'Log an action response'
        if response: self.tabular_log( level, 'answer',
            red( response, style='bold'), label_color=green)
