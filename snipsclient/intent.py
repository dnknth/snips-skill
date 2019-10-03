#!/usr/bin/env python3

import json
from datetime import datetime


def parse_date( date_str):
    'Convert a Snips date string to datetime'
    date_str = date_str[:19] + date_str[-7:-3] + date_str[-2:]
    return datetime.strptime( date_str, "%Y-%m-%d %H:%M:%S %z")


class SlotValue:

    def __init__( self, json_dict):
        self.kind = json_dict[ 'kind']
        self.value = json_dict.get( 'value')
    
    def __repr__( self):
        return "<%s value: %s>" % (self.kind, self.value)
        

class InstantTimeValue( SlotValue):

    def __init__( self, json_dict):
        super().__init__( json_dict)
        self.grain = json_dict[ 'grain']
        self.precision = json_dict[ 'precision']
        self.value = parse_date( self.value)
        

class TimeIntervalValue( SlotValue):

    def __init__( self, json_dict):
        super().__init__( json_dict)
        t1, t2 = json_dict[ 'from'], json_dict[ 'to']
        self.value = (parse_date( t1) if t1 else None, parse_date( t2) if t2 else None)
        

class DurationValue( SlotValue):

    def __init__( self, json_dict):
        super().__init__( json_dict)
        self.minutes = json_dict[ 'minutes'] # TODO verify
        

class TemperatureValue( SlotValue):

    def __init__( self, json_dict):
        super().__init__( json_dict)
        self.unit = json_dict[ 'unit']
    
    def __repr__( self):
        return "<%s value: %s %s>" % (self.kind, self.value, self.unit)
        

# See: https://docs.snips.ai/reference/dialogue#slot
class Slot:

    VALUE_MAP = {
        'InstantTime' : InstantTimeValue,
        'Temperature' : TemperatureValue,
        'TimeInterval': TimeIntervalValue,
        'Duration'    : DurationValue,
    }
    
    
    def __init__( self, position, json_dict):
        self.position = position
        self.entity = json_dict[ 'entity']
        self.slot_name = json_dict[ 'slotName']
        self.raw_value = json_dict[ 'rawValue']
        self.confidence_score = json_dict[ 'confidenceScore']
        
        r = json_dict[ 'range']
        self.range = (r['start'], r['end']) if r else None

        value = json_dict[ 'value']
        cls = self.VALUE_MAP.get( value[ 'kind'], SlotValue)
        self.value = cls( value)


    def __repr__( self):
        return "<Slot '%s' score=%.2f value='%s'>" % (
            self.slot_name, self.confidence_score, self.value)


# See: https://docs.snips.ai/reference/dialogue#intent
class Intent:
    
    def __init__( self, json_dict):
        self.intent_name = json_dict[ 'intentName']
        self.confidence_score = json_dict[ 'confidenceScore']

    def __repr__( self):
        return "<Intent '%s' score=%.2f>" % (
            self.intent_name, self.confidence_score)
        

# See: https://docs.snips.ai/reference/dialogue#intent
class IntentPayload:
    
    def __init__( self, json_dict):
        self.json = json_dict
        
        self.session_id = json_dict[ 'sessionId']
        self.input = json_dict[ 'input']
        self.intent = Intent( json_dict[ 'intent'])
        self.site_id = json_dict[ 'siteId']

        custom_data = json_dict.get( 'customData')
        if custom_data is not None:
            try:
                self.custom_data = json.loads( custom_data)
            except:
                self.custom_data = custom_data
        
        self.asr_tokens = json_dict.get( 'asrTokens')
        self.asr_confidence = json_dict.get( 'asrConfidence')
        self.slots = { s['slotName'] : Slot( i, s)
            for i, s in enumerate( json_dict.get( 'slots', [])) }
        self.slot_values = { name : s.value
            for name, s in self.slots.items() }

    def __repr__( self):
        return "<%s %s>" % (self.intent, list( self.slots))


def parse_intent( payload):
    'Parse intent data as objects'
    if type( payload) is bytes: payload = json.loads( payload)
    return IntentPayload( payload)


if __name__ == '__main__': # Demo code

    from snips import Client
    
    BLUE      = '\033[94m'
    GREEN     = '\033[92m'
    PURPLE    = '\033[95m'
    RED       = '\033[91m'
    YELLOW    = '\033[93m'
    
    BOLD      = '\033[1m'
    ENDC      = '\033[0m'

    client = Client()

    @client.topic( 'hermes/intent/#', payload_converter=parse_intent)
    def print_msg( client, userdata, msg):
        print()
        print( BOLD + GREEN + msg.topic + ENDC + ':')
        for k in ('site_id', 'input', 'intent'):
            print( YELLOW, k.ljust( 8) + ENDC, getattr( msg.payload, k))
        for name, slot in msg.payload.slots.items():
            print( PURPLE, name.ljust( 8) + ENDC, slot)

    client.run()
