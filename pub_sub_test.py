#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2020-03-12
#
# Tasks that monitor other tasks using `asyncio`'s `Event` object - modified.
# 
# Notice! This requires:  attrs==19.1.0
# 
# See:          https://roguelynn.com/words/asyncio-true-concurrency/
# Source:       https://github.com/econchick/mayhem/blob/master/part-1/mayhem_10.py
# See also:     https://cheat.readthedocs.io/en/latest/python/asyncio.html
# And another:  https://codepr.github.io/posts/asyncio-pubsub/
#               https://gist.github.com/appeltel/fd3ddeeed6c330c7208502462639d2c9
#               https://www.oreilly.com/library/view/using-asyncio-in/9781492075325/ch04.html
# 
# unrelated:
# Python Style Guide: https://www.python.org/dev/peps/pep-0008/

#        1         2         3         4         5         6         7         8
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import asyncio, attr, itertools, signal, string, uuid
import logging
import random
import sys, time
from datetime import datetime as dt

from colorama import init, Fore, Style
init()

# ..............

from lib.logger import Logger, Level
#from lib.message_factory import MessageFactory
from lib.event import Event

# NB: Using f-strings with log messages may not be ideal since no matter
# what the log level is set at, f-strings will always be evaluated
# whereas the old form ("foo %s" % "bar") is lazily-evaluated.
# But I just love f-strings.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# ..............................................................................
@attr.s
class Message:
    '''
    Don't create one of these directly: use the MessageFactory class.
    '''
    instance_name = attr.ib()
    message_id    = attr.ib(repr=False, default=str(uuid.uuid4()))
    timestamp     = attr.ib(repr=False, default=dt.now())
    hostname      = attr.ib(repr=False, init=False)
    acked         = attr.ib(repr=False, default=None) # count down to zero
    saved         = attr.ib(repr=False, default=False)
    processed     = attr.ib(repr=False, default=0)
    event         = attr.ib(repr=False, default=None)
    value         = attr.ib(repr=False, default=None)

    def __attrs_post_init__(self):
        self.hostname = f"{self.instance_name}.example.net"

    @property
    def expected(self):
        return self.acked != None

    def expect(self, count):
        self.acked = count

    @property
    def fulfilled(self):
        return self.acked <= 0

    def acknowledge(self):
        if self.acked == None:
            raise Exception('no expectation set ({}).'.format(self.instance_name))
        self.acked -= 1

# ..............................................................................
class MessageFactory(object):
    '''
    A factory for Messages.
    '''
    def __init__(self, level):
        self._log = Logger("msgfactory", level)
        self._counter = itertools.count()
        self._choices = string.ascii_lowercase + string.digits
        self._log.info('ready.')
 
    # ..........................................................................
    def get_random_event(self):
        '''
        Returns one of the randomly-assigned event types.
        '''
        types = [ Event.STOP, \
                  Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD, \
                  Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD, \
                  Event.SNIFF, \
                  Event.FULL_AHEAD, Event.ROAM, Event.ASTERN ] # not handled
        return types[random.randint(0, len(types)-1)]

    # ..........................................................................
    def get_message(self, event, value):
        _host_id = "".join(random.choices(self._choices, k=4))
        _instance_name = 'id-{}'.format(_host_id)
        return Message(instance_name=_instance_name, timestamp=dt.now(), event=event, value=value)

# ..............................................................................
class MessageBus(object):
    '''
    An asynchronous message bus.
    '''
    def __init__(self, loop, level):
        self._log = Logger("bus", level)
        self._loop = loop
        self._queue = asyncio.Queue()
        # may want to catch other signals too
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            self._loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(self.shutdown(s)))
        self._loop.set_exception_handler(self.handle_exception)
        self._log.info('ready.')

    # ..........................................................................
    @property
    def queue(self):
        return self._queue

    # exception handling .......................................................
    
    def handle_exception(self, loop, context):
        self._log.error('handle exception on loop: {}'.format(loop))
        message = context.get("exception", context["message"])
        # context["message"] will always be there; but context["exception"] may not
        self._log.error('caught exception: {}'.format(message))
        if loop.is_running() and not loop.is_closed():
            asyncio.create_task(self.shutdown(loop))
        else:
            self._log.info("loop already shut down.")
        self._log.info("Shutting down...")
    
    # shutdown .....................................................................
    async def shutdown(self, signal=None):
        '''
        Cleanup tasks tied to the service's shutdown.
        '''
        if signal:
            self._log.info('received exit signal {}...'.format(signal))
#       self._log.info(Fore.RED + 'closing services...' + Style.RESET_ALL)
        self._log.info(Fore.RED + 'nacking outstanding tasks...' + Style.RESET_ALL)
        tasks = [t for t in asyncio.all_tasks() if t is not
                asyncio.current_task()]
        [task.cancel() for task in tasks]
        self._log.info(Fore.RED + 'cancelling {:d} outstanding tasks...'.format(len(tasks)) + Style.RESET_ALL)
        await asyncio.gather(*tasks, return_exceptions=True)
        self._log.info(Fore.RED + "stopping loop..." + Style.RESET_ALL)
        self._loop.stop()
        self._log.info(Fore.RED + "shutting down..." + Style.RESET_ALL)
        sys.exit(1)

# Publisher ....................................................................
class Publisher(object):
    def __init__(self, message_bus, message_factory, level=Level.INFO):
        '''
        Simulates an external publisher of messages.

        Args:
            queue (asyncio.Queue): Queue to publish messages to.
        '''
        self._log = Logger('publisher', level)
        self._log.info(Fore.BLACK + 'initialised...')
        if message_bus is None:
            raise ValueError('null message bus argument.')
        self._message_bus = message_bus
        if message_factory is None:
            raise ValueError('null message factory argument.')
        self._message_factory = message_factory
        self._log.info(Fore.BLACK + 'ready.')

    # ................................................................
    async def publish(self):
        while True:
            _event = self._message_factory.get_random_event()
            _message = self._message_factory.get_message(_event, _event.description)

            # publish the message
            asyncio.create_task(self._message_bus.queue.put(_message))
            self._log.info(Fore.BLACK + Style.BRIGHT + 'PUBLISHED message: {} (event: {})'.format(_message, _event.description) \
                    + Fore.WHITE + ' ({:d} in queue)'.format(self._message_bus.queue.qsize()))
            # simulate randomness of publishing messages
            await asyncio.sleep(random.random())
            self._log.debug(Fore.BLACK + Style.BRIGHT + 'after await sleep.')

# Subscribers ..................................................................
class Subscribers(object):
    '''
    The list of Subscribers.
    '''
    def __init__(self, message_bus, level=Level.INFO):
        self._log = Logger('subs', level)
        if message_bus is None:
            raise ValueError('null message bus argument.')
        self._message_bus = message_bus
        self._subscribers = []
        self._log.info('ready.')

    def add(self, subscriber):
        self._subscribers.append(subscriber)

    @property
    def count(self):
        return len(self._subscribers)

    async def consume(self):
        while True:
            for subscriber in self._subscribers:
                self._log.debug('publishing to subscriber {}...'.format(subscriber.name))
                await subscriber.consume(self._message_bus.queue, self.count)

# SaveFailed exception .........................................................
class SaveFailed(Exception):
    pass

# RestartFailed exception ......................................................
class RestartFailed(Exception):
    pass

# Subscriber ...................................................................
class Subscriber(object):
    '''
    Description.
    '''
    def __init__(self, name, color, events, level=Level.INFO):
        self._log = Logger('sub-{}'.format(name), level)
        self._name = name
        self._color = color
        self._log.info(self._color + 'initialised...')
        self._events = events # list of event types
        self._is_cleanup_task = events is None
        self._log.info(self._color + 'ready.')

    # ..........................................................................
    @property
    def name(self):
        return self._name

    # ..........................................................................
    @property
    def queue(self):
        return self._queue

    # ..........................................................................
    def accept(self, event):
        '''
        An event filter that returns True if the subscriber should accept the event.
        '''
        return ( self._events is None ) or ( event in self._events )

    def acceptable(self, event):
        '''
        A filter that returns True if the event is acceptable.
        '''
        return event in [ Event.STOP, Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD, Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD ]

    # ................................................................
    async def consume(self, queue, count):
        '''
        Consumer client to simulate subscribing to a publisher.
        This filters on event type, either consuming the message,
        ignoring it (and putting it back on the bus), or, if this
        is the cleanup task, destroying it.

        Args:
            queue (asyncio.Queue): Queue from which to consume messages.
            count:                 the number of subscribers.
        '''
        # 🍈 🍅 🍐 🍑 🍓 🥝 🥚 🥧
        # cleanup, consume or ignore the message
        _message = await queue.get()
        if not _message.expected:
            _message.expect(count-1) # we don't count cleanup task
        else:
            _message.acknowledge()
 
        if self._is_cleanup_task:
            if _message.fulfilled:
                _elapsed_ms = int((dt.now() - _message.timestamp).total_seconds() * 1000.0)
                if _message.event == Event.SNIFF:
                    self._log.info(self._color + Style.BRIGHT + 'CLEANUP message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description) \
                            + Fore.WHITE + Style.NORMAL + '; processed by {:d} in {:d}ms.'.format(_message.processed, _elapsed_ms))
                    if _message.event == Event.SNIFF and _message.processed < 2:
                        raise Exception('processed by only {:d}.'.format(_message.processed))
                else:
                    self._log.info(self._color + 'CLEANUP message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description) \
                            + Fore.WHITE + Style.NORMAL + '; processed by {:d} in {:d}ms.'.format(_message.processed, _elapsed_ms))
                # otherwise we exit to let it expire
                return
            elif self.acceptable(_message.event):
                raise Exception('🍏 UNPROCESSED acceptable message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
#               self._log.info(self._color + Style.BRIGHT + '🧀 RETURN unacknowledged message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
            # else put it back onto the bus

        else:
            # if this subscriber is interested, handle the message
            if self.accept(_message.event):
                self._log.info(self._color + Style.BRIGHT + 'CONSUMED message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
                # message processed, but not everyone has seen it yet so put back onto message bus once done
                asyncio.create_task(self._consume_message(_message))

        # was not cleaned up nor fulfilled, so put back into queue
        if not _message.fulfilled:
            asyncio.create_task(queue.put(_message))
            self._log.info(self._color + Style.DIM + 'returning unprocessed message {} '.format(_message) + Fore.WHITE + ' to queue; event: {}'.format(_message.event.description))
        else:
            self._log.info(self._color + Style.DIM + '🍋 AWAITING CLEANUP message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))


    # ................................................................
    async def _consume_message(self, message):
        '''
        Kick off tasks to consume the message.

        :param message: the message to consume.
        '''
        _event = asyncio.Event()
        asyncio.create_task(self._process(message, _event))
        asyncio.create_task(self._cleanup(message, _event))

        results = await asyncio.gather(self._save(message), self._restart_host(message), return_exceptions=True)
        self._handle_results(results, message)
        _event.set()

    # ................................................................
    async def _process(self, message, event):
        '''
        Process the message, i.e., do something with it to change the state of the robot.

        Args:
        :param message:  the message to process.
        :event event:    the asyncio.Event to watch for message extention or cleaning up.
        '''
        while not event.is_set():
            message.processed += 1
            _elapsed_ms = int((dt.now() - message.timestamp).total_seconds() * 1000.0)
            self._log.info(Fore.GREEN + Style.NORMAL + 'processing message: {} in {:d}ms'.format(message, _elapsed_ms))
            # want to sleep for less than the deadline amount
            await asyncio.sleep(2)

    # ................................................................
    async def _cleanup(self, message, event):
        '''
        Cleanup tasks related to completing work on a message.

        Args:
            message (Message): consumed event message that is done being
                processed.
        '''
        # this will block the rest of the coro until `event.set` is called
        await event.wait()
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
        message.acked == 0
        self._log.info(self._color + Style.DIM + 'done: acked {}'.format(message))

    # ................................................................
    async def _save(self, message):
        """Save message to a database.

        Args:
            message (Message): consumed event message to be saved.
        """
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
        if random.randrange(1, 5) == 3:
            raise SaveFailed('Could not save {}'.format(message))
        message.saved = True
        self._log.info(self._color + Style.DIM + 'saved {} into database.'.format(message))

    # ................................................................
    async def _restart_host(self, message):
        """Restart a given host.

        Args:
            message (Message): consumed event message for a particular
                host to be restarted.
        """
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
        if random.randrange(1, 5) == 3:
            raise RestartFailed('Could not restart {}'.format(message.hostname))
        message.restart = True
        self._log.info(self._color + Style.DIM + 'restarted host {}'.format(message.hostname))

    # ................................................................
    def _handle_results(self, results, message):
        self._log.info('handling results for message: {}'.format(message))
        for result in results:
            if isinstance(result, RestartFailed):
                self._log.error('retrying for failure to restart: {}'.format(message.hostname))
            elif isinstance(result, SaveFailed):
                self._log.error('failed to save: {}'.format(message.hostname))
            elif isinstance(result, Exception):
                self._log.error('handling general error: {}'.format(result))


# main .........................................................................
def main():

    _log = Logger("main", Level.INFO)
    _log.info(Fore.BLUE + '1. configuring test...')
    _loop = asyncio.get_event_loop()

    _message_bus = MessageBus(_loop, Level.INFO)
    _message_factory = MessageFactory(Level.INFO)
    _publisher   = Publisher(_message_bus, _message_factory, Level.INFO)
    _subscribers = Subscribers(_message_bus, Level.INFO)                 

    _subscriber1 = Subscriber('1-stop', Fore.YELLOW, [ Event.STOP, Event.SNIFF ], Level.INFO) # reacts to STOP
    _subscribers.add(_subscriber1)
    _subscriber2 = Subscriber('2-infrared', Fore.MAGENTA, [ Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD ], Level.INFO) # reacts to IR
    _subscribers.add(_subscriber2)
    _subscriber3 = Subscriber('3-bumper', Fore.GREEN, [ Event.SNIFF, Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD ], Level.INFO) # reacts to bumpers
    _subscribers.add(_subscriber3)
    _subscriber4 = Subscriber('4-clean', Fore.RED, None, Level.INFO) # cleanup subscriber
    _subscribers.add(_subscriber4)

    _log.info(Fore.BLUE + '{:d} subscribers in list.'.format(_subscribers.count))

#   for i in range(10):
#       _event = _message_factory.get_random_event()
#       _message = _message_factory.get_message(_event, _event.description)
#       _log.info(Fore.YELLOW + '[{:02d}] message {}; event: {}'.format(i, _message, _message.event.description))
#   sys.exit(0)

    try:
        _log.info(Fore.BLUE + '2. creating task for publishers...')
        _loop.create_task(_publisher.publish())

#       _log.info(Fore.BLUE + '3. creating task for subscriber 1...')
#       _loop.create_task(_subscriber1.consume())
#       _log.info(Fore.BLUE + '4. creating task for subscriber 2...')
#       _loop.create_task(_subscriber2.consume())
#       _log.info(Fore.BLUE + '5. creating task for subscriber 3...' + Style.RESET_ALL)
#       _loop.create_task(_subscriber3.consume())
#       _log.info(Fore.BLUE + '6. creating task for subscriber 4...' + Style.RESET_ALL)
#       _loop.create_task(_subscriber4.consume())

        _log.info(Fore.BLUE + '3. creating task for subscribers...' + Style.RESET_ALL)
        _loop.create_task(_subscribers.consume())

        _log.info(Fore.BLUE + 'z. run forever...' + Style.RESET_ALL)
        _loop.run_forever()

    except KeyboardInterrupt:
        _log.info("process interrupted")
    finally:
        _loop.close()
        _log.info("successfully shutdown the message bus service.")


# ........................
if __name__ == "__main__":
    main()

