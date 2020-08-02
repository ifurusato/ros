#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#   Robot Operating System Daemon (rosd)
#
# This also uses the rosd.service.

# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-01
# modified: 2020-08-01
#
# see: https://dpbl.wordpress.com/2017/02/12/a-tutorial-on-python-daemon/
# ..............................................................................

try:
    import daemon
    from daemon import pidfile
except Exception:
    sys.exit("This script requires the python-daemon module.\nInstall with: sudo pip3 install python-daemon")

import os, signal, sys, time, threading, traceback
from datetime import datetime
import RPi.GPIO as GPIO

from lib.logger import Level, Logger
from lib.config_loader import ConfigLoader
from ros import ROS

# ..............................................................................

def shutdown(signum, frame):  # signum and frame are mandatory
    sys.exit(0)

# ..............................................................................
class RosDaemon():
    '''
        Monitors a toggle switch, mirroring its state on an LED.

        This state is used to enable or disable the ROS. This replaces rather
        than reuses the Status class (as a reliable simplification).
    '''
    def __init__(self, config, gpio, level):
        self._log = Logger("rosd", level)
        self._gpio = gpio
        self._gpio.setmode(GPIO.BCM)
        self._gpio.setwarnings(False)
        if config is None:
            raise ValueError('no configuration provided.')
        self._log.info('configuration provided.')
        self._config = config['rosd']
        self._switch_pin = self._config.get('switch_pin') # default 14
        self._led_pin    = self._config.get('led_pin')    # default 27
        self._log.info('initialising with switch on pin {} and LED on pin {}.'.format(self._switch_pin, self._led_pin))
        self._gpio.setup(self._switch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._gpio.setup(self._led_pin, GPIO.OUT, initial=GPIO.LOW)
        self._old_state = False
        self._thread = None
        self._thread_timeout_delay_sec = 1
        _rosd_mask = os.umask(0)              # I'm doing this weird three lines trick
        os.umask(_rosd_mask)                  # due to the behaviour of os.umask.
        self._log.info('mask: {}'.format(_rosd_mask))  # to print the umask set by DaemonContext
        self._log.info('cwd:  {}'.format(os.getcwd()))
        self._log.info('uid:  {}'.format(os.getuid()))
        self._log.info('gid:  {}'.format(os.getgid()))
        self._log.info('rosd ready.')


    # ..........................................................................
    def _get_timestamp(self):
        return datetime.utcfromtimestamp(datetime.utcnow().timestamp()).isoformat()
#       return datetime.utcfromtimestamp(datetime.utcnow().timestamp()).isoformat().replace(':','_').replace('-','_').replace('.','_')


    # ..........................................................................
    def read_state(self):
        '''
            Reads the state of the toggle switch, sets the LED accordingly,
            then returns the value. This only calls enable() or disable()
            if the value has changed since last reading.
        '''
        self._state = not GPIO.input(self._switch_pin)
#       self._log.info('current state: {}'.format(self._state))
        if self._state is not self._old_state: # if low
            if self._state:
                self.enable()
            else:
                self.disable()
        self._old_state = self._state
        return self._state


    # ..........................................................................
    def enable(self):
        self._log.info('ros state enabled at: {}           +++++++++++++++++ '.format(self._get_timestamp()))
        if self._thread is None:
            self._log.info('STARTING ROS           +++++++++++++++++++++++++++++++++++++ ')
            self._thread = ROS()
            self._thread.start()
            self._log.info('ros started.')
        else:
            self._log.info('cannot start ros: thread already exists.')
        self._gpio.output(self._led_pin, True)


    # ..........................................................................
    def disable(self):
        self._log.info('ros state disabled at: {}          ----------------- '.format(self._get_timestamp()))
        if self._thread is not None:
            self._log.info('HALTING ROS        --------------------------------------- ')
            self._thread.join(timeout=self._thread_timeout_delay_sec)
            self._log.info('ros thread joined.')
            self._thread = None
        self._gpio.output(self._led_pin,False)

    # ..........................................................................
    def close(self):
        self._log.info('closing rosd...')
        self._gpio.output(self._led_pin,False)
        self._log.info('rosd closed.')


# main .........................................................................

_daemon = None

def main():
    try:
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _daemon = RosDaemon(_config, GPIO, Level.INFO)
        while True:
            _daemon.read_state()
            time.sleep(0.2)

    except Exception:
        print('error starting ros daemon: {}'.format(traceback.format_exc()))
    finally:
        if _daemon is not None:
            _daemon.close()
        print('rosd complete.')

# ..............................................................................

with daemon.DaemonContext(
    stdout=sys.stdout,
    stderr=sys.stderr,
    chroot_directory=None,
    working_directory='/home/pi/ros',
    umask=0o002,
    pidfile=pidfile.TimeoutPIDLockFile('/home/pi/ros/.rosd.pid'),
    signal_map={
        signal.SIGTERM: shutdown,
        signal.SIGTSTP: shutdown
    }) as context:
    main()

#EOF
