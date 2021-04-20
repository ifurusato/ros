#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# created:  2021-04-20
# modified: 2021-04-20
#
# Tests features of the Message class.
#

import pytest
import sys, traceback
from colorama import init, Fore, Style
init()
from lib.logger import Logger, Level
from lib.event import Event
from lib.message import Message
from lib.async_message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.subscriber import Subscriber

# ..............................................................................
@pytest.mark.unit
def test_message():

    _log = Logger('message-test', Level.INFO)
    try:

        _log.info('start message test...')
        _message_bus = MessageBus(Level.INFO)
        _message_factory = MessageFactory(_message_bus, Level.INFO)

        _subscriber1 = Subscriber('behaviour', Fore.YELLOW, _message_bus, Level.INFO)
        _message_bus.register_subscriber(_subscriber1)
        _subscriber2 = Subscriber('infrared', Fore.MAGENTA, _message_bus, Level.INFO)
        _message_bus.register_subscriber(_subscriber2)
        _subscriber3 = Subscriber('bumper', Fore.GREEN, _message_bus, Level.INFO)
        _message_bus.register_subscriber(_subscriber3)

        _message_bus.print_publishers()
        _message_bus.print_subscribers()
        # ................................

        _message = _message_factory.get_message(Event.BRAKE, True)
        _log.info('created message {}; event: {}'.format(_message.name, _message.event.name))

        _message.acknowledge(_subscriber1)
        _subscriber1.print_message_info('sub1 info for message:', _message, None)
         

    except Exception as e:
        _log.error('error: {}'.format(e))
    finally:
        _log.info('complete.')

# ..............................................................................
def main():

    try:
        test_message()
    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + 'error in motor test: {}'.format(e) + Style.RESET_ALL)
        traceback.print_exc(file=sys.stdout)
    finally:
        pass

if __name__== "__main__":
    main()

#EOF
