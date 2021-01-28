#!/usr/bin/env python3

from snips_skill import *


_, ngettext = get_translations(__file__)


class ExampleSkill(Skill):
    
    'Your skill goes here'

    def add_arguments(self):
        super().add_arguments()
        
        self.parser.add_argument('--option',
            help='Optionally set an option')

    @intent('example:intent')
    def intent_handler(self, userdata, msg):
        return _('Not implemented')


if __name__ == '__main__':
    ExampleSkill().run()
