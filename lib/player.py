#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
#    This class and its Enum plays sounds.
#

import os, sys, time, threading
from enum import Enum
from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.logger import Logger, Level


# configuration ................................................................

# path to the sound directory
SOUND_DIR = 'sound'
# play volume 0.0 - 1.0
PLAY_VOLUME = 1.0

# suppress pygame and config console output ....................................
temp_stdout = sys.stdout
sys.stdout = DevNull()
import pygame
sys.stdout = temp_stdout

# configuration ................................................................
class Sound(Enum):
    '''
        An enumerated set of available sounds.
    '''
    BEEP        = (   1, "Beep.mp3"              ) # from an answering machine, probably 440 Hz tone
    HONK        = (   2, "HornHonk.mp3"          ) # single honk, more modern car
    HONK2       = (   3, "HornHonk2.mp3"         ) # short car horn
    BUZZ        = (   4, "Buzz.mp3"              ) # rather audible buzzz
    DOOR_BUZZ   = (   5, "DoorBuzzer.mp3"        ) # sounds like it's at a distance
    ALARM       = (   6, "AnalogWatchAlarm.mp3"  ) # high pitch beep-beep (actually audible)
    CHIRP       = (   7, "RadioInterruption.mp3" ) # electronic chirp
    CALL_BELL   = (   8, "SchoolBell.mp3"        ) # repeating 10x call bell
    BLIP        = (   9, "RobotBlip.mp3"         ) # quiet but audible
    PING        = (  10, "Ping.mp3"              ) # submarine sonar
    DIVE_ALARM  = (  11, "DiveAlarm.mp3"         ) # three blasts
    SHIP_HORN   = (  12, "AirHorn1.mp3"          ) # long ship's horn
    SHIP_HORN2  = (  13, "AirHorn3.mp3"          ) # nice ship's horn
    KLAXON      = (  14, "AirHorn2.mp3"          ) # pretty good, klaxon
    SIREN       = (  15, "Siren.mp3"             ) # single siren
    LONG_SIREN  = (  16, "LongSiren.mp3"         ) # long repeating volume siren 
    TORNADO     = (  17, "TornadoWarning.mp3"    ) # just like Iowa, 1974
    RR_XING     = (  18, "RRCrossing.mp3"        ) # reasonable volume clang clang clang
    CRICKETS    = (  19, "Crickets.mp3"          ) # quite nice
    CHIRPING    = (  20, "SummerCrickets.mp3"    ) # pleasant
    FROGS       = (  21, "Frogs.mp3"             ) # where are they?
    CROAKING    = (  22, "CroakingFrogs.mp3"     ) # oh so nice
    SMALL_DOG   = (  23, "SmallDog.mp3"          ) # sounds like a small dog caught deep within the Pi
    LARGE_DOG   = (  24, "LargeDog.mp3"          ) # large dog that sounds very small
    LA_ROSITA   = (  25, "/home/pi/Music/La_Rosita.mp3" ) # Coleman Hawkins and Ben Webster 'Compact Jazz'

    # ..................................
    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, num, name):
        self._name = name

    # this makes sure the name is read-only
    @property
    def name(self):
        return self._name


# ..............................................................................
class Player():

    def __init__(self, level):
        global _active
        self._log = Logger("player", level)
        self._log.info('initialising mixer...')
        pygame.mixer.init()
        self._log.info('mixer initialised.')
        pygame.mixer.music.set_volume(PLAY_VOLUME)
        self._thread = None
        _active = False
        # set system volume
        SYSTEM_VOLUME = 90
        self._log.info('setting system volume to {}%...'.format(SYSTEM_VOLUME))
        os.system('/usr/bin/amixer set PCM ' + str(SYSTEM_VOLUME) + '%')
        self._log.info('ready.')


    # ..........................................................................
    def is_playing(self):
        '''
            Returns true if there is an existing thread (a sound is being played).
        '''
        global _active
        return _active and self._thread is not None


    # ..........................................................................
    def play(self, sound):
        '''
            Play the Sound once.
        '''
        if self._thread is None:
            self._thread = threading.Thread(target=Player._fPlay, args=[self, sound, 1, None])
            self._thread.start()
        else:
            self._log.warning('cannot play sound: player currently in use.')


    # ..........................................................................
    def stop(self):
        '''
            Stops playing any repeating sound, after the current track 
            has finished. This has no effect if nothing is playing.
        '''
        global _active
        _active = False


    # ..........................................................................
    def repeat(self, sound, count, delay_sec ):
        '''
            Play the Sound the designated number of times, with 
            the designated delay between plays.
        '''
        if self._thread is None:
            self._thread = threading.Thread(target=Player._fPlay, args=[self, sound, count, delay_sec])
            self._thread.start()
        else:
            self._log.warning('cannot play sound: player currently in use.')


    # ..........................................................................
    def _fPlay(self, sound, count, delay_sec ):
        '''
            Play the Sound the designated number of times, with the designated
            delay between plays. Stopping play will not interrupt an existing
            sound but will stop subsequent sounds when repeating.
        '''
        global _active
        try:
            _active = True
            if sound.name.startswith('/'): # absolute path
                _pathname = sound.name
            else:
                _pathname = os.getcwd() + '/' + SOUND_DIR + '/' + sound.name
            self._log.info('pathname: {}'.format(_pathname))
            pygame.mixer.music.load(_pathname)
            # play how many times?
            for i in range(0, count):
                self._log.info("playing {} ({} of {})".format(sound.name, i+1, count))
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() == True:
                    pass
                # delay between plays
                if delay_sec:
                    time.sleep(delay_sec)
                if not _active:
                    return
        except KeyboardInterrupt:
            self._log.info("finished.")
        finally:
            self._thread = None
            self._log.info(Fore.GREEN + Style.BRIGHT + "play finished.")
            _active = False


#EOF
