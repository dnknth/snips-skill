from colors import cyan, green, magenta, red, yellow
import logging


__all__ = ('LoggingMixin', )


class LoggingMixin:
    'Logging for Snips events'
    
    INDENT = 10
    tty_log = None

    def colored_log(self, level, format, *args, color=None):
        if self.tty_log is None:
            self.tty_log = logging.getLogger().handlers[0].stream.isatty()
        if color and self.tty_log: args = map(color, args)
        self.log.log(level, format, *args)
    

    def tabular_log(self, level, key, value, color=None, width=INDENT):
        label = '%-*s' % (width, key)
        self.colored_log(level, '%s %s', label, str(value), color=color)
    
    
    def log_intent(self, payload, level=logging.DEBUG):
        'Log an intent message'
        self.tabular_log(level, 'intent', '%s, confidence: %.1f' % (
            red(payload.intent.intent_name, style='bold'),
            payload.intent.confidence_score), color=green)
        for k in ('site_id', 'input'):
            self.tabular_log(level, k, getattr(payload, k), color=cyan)
        for name, slot in payload.slots.items():
            self.tabular_log(level, name, slot.value, color=magenta)
        if payload.custom_data:
            self.tabular_log(level, 'data', payload.custom_data, color=yellow)
            
    
    def log_response(self, response, level=logging.DEBUG):
        'Log an action response'
        if response: self.tabular_log(level, 'answer',
            red(response, style='bold'), color=green)
