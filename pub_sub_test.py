#!/usr/bin/env python3
# Copyright (c) 2018-2019 Lynn Root
'''
Tasks that monitor other tasks using `asyncio`'s `Event` object - modified.

Notice! This requires:
 - attrs==19.1.0

To run:

    $ python part-1/mayhem_10.py

Follow along: https://roguelynn.com/words/asyncio-true-concurrency/
Source:       https://github.com/econchick/mayhem/blob/master/part-1/mayhem_10.py
See also:     https://cheat.readthedocs.io/en/latest/python/asyncio.html
And another:  https://codepr.github.io/posts/asyncio-pubsub/
              https://gist.github.com/appeltel/fd3ddeeed6c330c7208502462639d2c9
              https://www.oreilly.com/library/view/using-asyncio-in/9781492075325/ch04.html

unrelated:
Python Style Guide: https://www.python.org/dev/peps/pep-0008/
'''
#        1         2         3         4         5         6         7         8
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import asyncio, attr, itertools, signal, string, uuid
import logging
import random
import sys, time # TEMP
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
#   restarted     = attr.ib(repr=False, default=False)
    saved         = attr.ib(repr=False, default=False)
    acked         = attr.ib(repr=False, default=False)
    extended_cnt  = attr.ib(repr=False, default=0)
    event         = attr.ib(repr=False, default=None)
    value         = attr.ib(repr=False, default=None)

    def __attrs_post_init__(self):
        self.hostname = f"{self.instance_name}.example.net"

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
                  Event.FULL_AHEAD, Event.ROAM, Event.ASTERN ] # not handled
        return types[random.randint(0, len(types)-1)]

    # ..........................................................................
    def get_message(self, event, value):
#       return Message(next(self._counter), event, value)
        _host_id = "".join(random.choices(self._choices, k=4))
        _instance_name = 'id-{}'.format(_host_id)
        return Message(instance_name=_instance_name, event=event, value=value)

# Publisher ....................................................................
class Publisher(object):
    def __init__(self, queue, message_factory, level=Level.INFO):
        '''
        Simulates an external publisher of messages.

        Args:
            queue (asyncio.Queue): Queue to publish messages to.
        '''
        self._log = Logger('publisher', level)
        self._log.info(Fore.BLACK + 'initialised...')
        if queue is None:
            raise ValueError('null queue argument.')
        self._queue = queue
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
            # 💭 💮  📤 📥
#           self._log.info(Fore.BLACK + Style.BRIGHT + '📢 PUBLISHING message: {} (event: {})'.format(_message, _event.description))
            asyncio.create_task(self._queue.put(_message))
            self._log.info(Fore.BLACK + Style.BRIGHT + '📢 PUBLISHED  message: {} (event: {})'.format(_message, _event.description) \
                    + Fore.WHITE + ' ({:d} in queue)'.format(self._queue.qsize()))
            # simulate randomness of publishing messages
            await asyncio.sleep(random.random())
            self._log.debug(Fore.BLACK + Style.BRIGHT + 'after await sleep.')

# Subscribers ..................................................................
class Subscribers(object):
    '''
    The list of Subscribers.
    '''
    def __init__(self, level=Level.INFO):
        self._log = Logger('subs', level)
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
                await subscriber.consume()

# Subscriber ...................................................................
class Subscriber(object):
    '''
    Description.
    '''
    def __init__(self, name, color, queue, events, level=Level.INFO):
        self._log = Logger('sub-{}'.format(name), level)
        self._name = name
        self._color = color
        self._log.info(self._color + 'initialised...')
        if queue is None:
            raise ValueError('null queue argument.')
        self._queue = queue
        self._events = events # list of event types
        self._is_cleanup_task = events is None
        self._log.info(self._color + 'ready.')

    # ..........................................................................
    @property
    def name(self):
        return self._name

    # ..........................................................................
    def accept(self, event):
        '''
        An event filter that teturns True if the subscriber should accept the event.
        '''
        return ( self._events is None ) or ( event in self._events )

    def acceptable(self, event):
        return event in [ Event.STOP, Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD, Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD ]

    # ................................................................
    async def consume(self):
        '''
        Consumer client to simulate subscribing to a publisher.
        This filters on event type, either consuming the message,
        ignoring it (and putting it back on the bus), or, if this
        is the cleanup task, sinking it.

        Args:
            queue (asyncio.Queue): Queue from which to consume messages.
        '''
        # 🍈🍅🍐🍑🍓🥝🥚🥧
#       while True:
        # cleanup, consume or ignore the message
        _message = await self._queue.get()
        if self._is_cleanup_task:
            if _message.acked:
                self._log.info(self._color + Style.BRIGHT + '🍏 CLEANUP message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
                if self.acceptable(_message.event):
                    raise Exception('🍏 UNPROCESSED acceptable message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
                # otherwise we let it die here
            else:
                asyncio.create_task(self._queue.put(_message))
                self._log.info(self._color + Style.BRIGHT + '🧀 RETURN unacknowledged message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
        elif self.accept(_message.event):
            self._log.info(self._color + Style.BRIGHT + '🍎 CONSUMED message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
            asyncio.create_task(self.handle_message(_message))
        else:
            # acknowledge, put it back onto the message bus, ignored.
            _message.acked = True
            asyncio.create_task(self._queue.put(_message))
#           self._queue._put(_message)
            self._log.info(self._color + Style.DIM + '🍋 IGNORED message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))

    # ................................................................
    async def handle_message(self, msg):
        '''
        Kick off tasks for a given message.

        Args:
            msg (Message): consumed message to process.
        '''
        event = asyncio.Event()
        asyncio.create_task(self.extend(msg, event))
        asyncio.create_task(self.cleanup(msg, event))

        await asyncio.gather(self.save(msg), self.restart_host(msg))
        event.set()

    # ................................................................
    async def extend(self, msg, event):
        '''
        Periodically extend the message acknowledgement deadline.

        Args:
            msg (Message): consumed event message to extend.
            event (asyncio.Event): event to watch for message extention or
                cleaning up.
        '''
        while not event.is_set():
            msg.extended_cnt += 1
            self._log.info(self._color + Style.DIM + 'extended deadline by 3 seconds for {}'.format(msg))
            # want to sleep for less than the deadline amount
            await asyncio.sleep(2)

    # ................................................................
    async def cleanup(self, msg, event):
        '''
        Cleanup tasks related to completing work on a message.

        Args:
            msg (Message): consumed event message that is done being
                processed.
        '''
        # this will block the rest of the coro until `event.set` is called
        await event.wait()
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
        msg.acked = True
        self._log.info(self._color + Style.DIM + 'done: acked {}'.format(msg))

    # ................................................................
    async def save(self, msg):
        """Save message to a database.

        Args:
            msg (Message): consumed event message to be saved.
        """
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
        msg.save = True
        self._log.info(self._color + Style.DIM + 'saved {} into database.'.format(msg))

    # ................................................................
    async def restart_host(self, msg):
        """Restart a given host.

        Args:
            msg (Message): consumed event message for a particular
                host to be restarted.
        """
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
        msg.restart = True
        self._log.info(self._color + Style.DIM + 'restarted host {}'.format(msg.hostname))


# ..............................................................................
class MessageBus(object):
    '''
    An asynchronous message bus.
    '''
    def __init__(self, loop, level):
        self._log = Logger("bus", level)
        self._loop = loop
        self._queue = asyncio.Queue()
        # May want to catch other signals too
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
        # context["message"] will always be there; but context["exception"] may not
        self._log.info(Fore.GREEN + 'LOOP: {}'.format(loop))
        msg = context.get("exception", context["message"])
        self._log.error('caught exception: {}'.format(msg))
        if loop.running() and not loop.closed():
            # see if the loop is active before calling for a shutdown
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
        self._log.info(Fore.RED + 'closing database connections' + Style.RESET_ALL)
        self._log.info(Fore.RED + 'nacking outstanding messages' + Style.RESET_ALL)
        tasks = [t for t in asyncio.all_tasks() if t is not
                 asyncio.current_task()]
    
        [task.cancel() for task in tasks]
    
        self._log.info(Fore.RED + 'cancelling {:d} outstanding tasks'.format(len(tasks)) + Style.RESET_ALL)
        await asyncio.gather(*tasks, return_exceptions=True)
        self._log.info(Fore.RED + "flushing metrics." + Style.RESET_ALL)
        self._loop.stop()
        sys.exit(1)
    
# main .........................................................................
def main():

    _log = Logger("main", Level.INFO)
    _log.info(Fore.BLUE + '1. configuring test...')
    _loop = asyncio.get_event_loop()

    _message_bus = MessageBus(_loop, Level.INFO)
    _queue = _message_bus.queue

    _message_factory = MessageFactory(Level.INFO)
    _publisher = Publisher(_queue, _message_factory, Level.INFO)
    _subscribers = Subscribers(Level.INFO)                 
    _subscriber1 = Subscriber('1-stp', Fore.YELLOW, _queue, [ Event.STOP ], Level.INFO) # reacts to STOP
    _subscribers.add(_subscriber1)
    _subscriber2 = Subscriber('2-irs', Fore.MAGENTA, _queue,  [ Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD ], Level.INFO) # reacts to IR
    _subscribers.add(_subscriber2)
    _subscriber3 = Subscriber('3-bmp', Fore.GREEN, _queue, [ Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD ], Level.INFO) # reacts to bumpers
    _subscribers.add(_subscriber3)
    _subscriber4 = Subscriber('4-cup', Fore.RED, _queue, None, Level.INFO)              # cleanup subscriber
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
        _log.info("Process interrupted")
    finally:
        _loop.close()
        _log.info("Successfully shutdown the Mayhem service.")


# ........................
if __name__ == "__main__":
    main()

