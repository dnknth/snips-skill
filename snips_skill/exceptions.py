class SnipsError( Exception):
    'Signal that an intent cannot be handled'
    
    def __str__( self):
        return str( self.args[0])


class SnipsClarificationError( SnipsError):
    'Signal that some clarification is needed from the user.'
    
    def __init__( self, msg, intent=None, slot=None, custom_data=None):
        ''' Create a clarification request.
            :param msg: Question for the user
            :param intent: Optional expected intent
            :param slot: Optional slot name
            See: https://docs.snips.ai/reference/dialogue#continue-session
        '''
        super().__init__( msg, intent, slot, custom_data)
        
    def __str__( self):
        return str( self.args[0])
        
    @property
    def intent( self):
        return self.args[1]

    @property
    def slot( self):
        return self.args[2]
        
    @property
    def custom_data( self):
        return self.args[3]
