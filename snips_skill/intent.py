#!/usr/bin/env python3

import json
from datetime import datetime, timedelta


__all__ = ('IntentPayload',)


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
        

# See: https://docs.snips.ai/articles/platform/dialog/slot-types#time-related-entities
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
        

# See: https://docs.snips.ai/articles/platform/dialog/slot-types#duration-entities
# TODO: years, quarters and months are not parsed
class DurationValue( SlotValue):

    def __init__( self, json_dict):
        super().__init__( json_dict)
        self.precision = json_dict[ 'precision']
        self.value = timedelta(
            weeks=json_dict[ 'weeks'],
            days=json_dict[ 'days'],
            hours=json_dict[ 'hours'],
            minutes=json_dict[ 'minutes'],
            seconds=json_dict[ 'seconds'])
        

class TemperatureValue( SlotValue):

    def __init__( self, json_dict):
        super().__init__( json_dict)
        self.unit = json_dict[ 'unit']
    
    def __repr__( self):
        return "<%s value: %s %s>" % (self.kind, self.value, self.unit)
        

class MonetaryValue( SlotValue):

    def __init__( self, json_dict):
        super().__init__( json_dict)
        self.unit = json_dict[ 'unit']
        self.precision = json_dict[ 'precision']
    
    def __repr__( self):
        return "<%s value: %s %s>" % (self.kind, self.value, self.unit)
        

# See: https://docs.snips.ai/reference/dialogue#slot
class Slot:

    VALUE_MAP = {
        'InstantTime'   : InstantTimeValue,
        'TimeInterval'  : TimeIntervalValue,
        'Duration'      : DurationValue,
        'Temperature'   : TemperatureValue,
        'AmountOfMoney' : MonetaryValue,
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
