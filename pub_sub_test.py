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
'''

import asyncio, attr, itertools, signal, string, uuid
import logging
import random
import time
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
    def get_message(self, event, value):
#       return Message(next(self._counter), event, value)
        _host_id = "".join(random.choices(self._choices, k=4))
        _instance_name = 'cattle-{}'.format(_host_id)
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

    def get_random_event(self):
        types = [ Event.STOP, Event.INFRARED_PORT, Event.INFRARED_STBD, Event.FULL_AHEAD, Event.ROAM, Event.EVENT_R1 ]
        return types[random.randint(0, len(types)-1)]

    # ................................................................
    async def publish(self):
        while True:
            _event = self.get_random_event()
            _message = self._message_factory.get_message(_event, _event.description)
            # publish the message
            self._log.info(Fore.BLACK + Style.BRIGHT + 'PUBLISHING message: {}'.format(_message))
            asyncio.create_task(self._queue.put(_message))
            self._log.info(Fore.BLACK + Style.BRIGHT + 'PRE-published message: {}; queue: {:d} items.'.format(_message, self._queue.qsize()))
            # simulate randomness of publishing messages
            await asyncio.sleep(random.random())
            self._log.info(Fore.BLACK + Style.BRIGHT + 'POST-published message: {}; queue: {:d} items.'.format(_message, self._queue.qsize()))

# Subscriber ...................................................................
class Subscriber(object):
    '''
    Description.
    '''
    def __init__(self, name, color, queue, level=Level.INFO):
        self._log = Logger('sub-{}'.format(name), level)
        self._color = color
        self._log.info(self._color + 'initialised...')
        if queue is None:
            raise ValueError('null queue argument.')
        self._queue = queue
        self._log.info(self._color + 'ready.')

    # ................................................................
    async def consume(self):
        '''
        Consumer client to simulate subscribing to a publisher.

        Args:
            queue (asyncio.Queue): Queue from which to consume messages.
        '''
        while True:
#           msg = await self._queue.get()
#           if self._queue.qsize() > 0:
            _peeked_message = await self._queue._get()
            if _peeked_message != None:
                print(Fore.RED + 'OBJECT: {}; len: {}'.format(_peeked_message, len(self._queue)) + Style.RESET_ALL)
                self._log.info(Fore.WHITE + 'peeked message: {}'.format(peeked_msg))
                # filter on...
                # types = [ Event.STOP, Event.INFRARED_PORT, Event.INFRARED_STBD, Event.FULL_AHEAD, Event.ROAM, Event.EVENT_R1 ]
                if _peeked_message.event == Event.INFRARED_PORT or _peeked_message.event == Event.INFRARED_STBD:
                    self._log.info(self._color + 'consumed message: {}'.format(msg))
                    asyncio.create_task(self.handle_message(msg))
                else:
                    self._log.info(self._color + 'passed on message: {}'.format(msg))
                    self._put(_peeked_message)

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
        """Cleanup tasks related to completing work on a message.

        Args:
            msg (Message): consumed event message that is done being
                processed.
        """
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

# shutdown .....................................................................
async def shutdown(signal, loop):
    '''
    Cleanup tasks tied to the service's shutdown.
    '''
    logging.info(Fore.RED + 'received exit signal {}...'.format(signal.name) + Style.RESET_ALL)
    logging.info(Fore.RED + 'Closing database connections' + Style.RESET_ALL)
    logging.info(Fore.RED + 'Nacking outstanding messages' + Style.RESET_ALL)
    tasks = [t for t in asyncio.all_tasks() if t is not
             asyncio.current_task()]

    [task.cancel() for task in tasks]

    logging.info(Fore.RED + 'cancelling {:d} outstanding tasks'.format(len(tasks)) + Style.RESET_ALL)
    await asyncio.gather(*tasks, return_exceptions=True)
    logging.info(Fore.RED + "flushing metrics." + Style.RESET_ALL)
    loop.stop()

# ..............................................................................
# main .........................................................................
def main():

    loop = asyncio.get_event_loop()

    # May want to catch other signals too
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, loop)))

    _queue = asyncio.Queue()

    _message_factory = MessageFactory(Level.INFO)
    _publisher = Publisher(_queue, _message_factory, Level.INFO)
    _subscriber1 = Subscriber('1', Fore.YELLOW, _queue, Level.INFO)
    _subscriber2 = Subscriber('2', Fore.MAGENTA, _queue, Level.INFO)

    try:
        loop.create_task(_publisher.publish())
        loop.create_task(_subscriber1.consume())
        loop.create_task(_subscriber2.consume())
        loop.run_forever()
    except KeyboardInterrupt:
        logging.info("Process interrupted")
    finally:
        loop.close()
        logging.info("Successfully shutdown the Mayhem service.")


if __name__ == "__main__":
    main()

