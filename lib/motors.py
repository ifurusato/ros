#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-18
# modified: 2020-03-26
#

import time, sys, traceback
from threading import Thread
from fractions import Fraction
from colorama import init, Fore, Style
init()

from .logger import Logger, Level
from .event import Event
from .enums import SlewRate, Orientation

try:
    from .motor import Motor
    print('import            :' + Fore.BLACK + ' INFO  : imported Motor.' + Style.RESET_ALL)
#except ImportError:
#   print('import            :' + Fore.RED + ' ERROR : failed to import Motor, using mock...' + Style.RESET_ALL)
#   from .mock_motor import Motor
except Exception:
#   print('import            :' + Fore.RED + ' ERROR : failed to import Motor, using mock...' + Style.RESET_ALL)
#   from .mock_motor import Motor
    traceback.print_exc(file=sys.stdout)
    print('import            :' + Fore.RED + ' ERROR : failed to import Motor, exiting...' + Style.RESET_ALL)
    sys.exit(1)

# ..........................................................................
def _configure_thunderborg_motors():
    '''
        Import the ThunderBorg library, then configure the Motors.
    '''
    print('tbconfig          :' + Fore.CYAN + ' INFO  : configure thunderborg & motors...' + Style.RESET_ALL)
    global pi
    try:
        print('tbconfig          :' + Fore.CYAN + ' INFO  : importing thunderborg...' + Style.RESET_ALL)
#           sys.path.append('/home/pi/thunderborg')
        import lib.ThunderBorg3 as ThunderBorg
        print('tbconfig          :' + Fore.CYAN + ' INFO  : successfully imported thunderborg.' + Style.RESET_ALL)
        TB = ThunderBorg.ThunderBorg()  # create a new ThunderBorg object
        TB.Init()                       # set the board up (checks the board is connected)
        print('tbconfig          :' + Fore.CYAN + ' INFO  : successfully instantiated thunderborg.' + Style.RESET_ALL)

        if not TB.foundChip:
            boards = ThunderBorg.ScanForThunderBorg()
            if len(boards) == 0:
                print('tbconfig          :' + Fore.RED + Style.BRIGHT + ' ERROR : no thunderborg found, check you are attached.' + Style.RESET_ALL)
            else:
                print('tbconfig          :' + Fore.RED + Style.BRIGHT + ' ERROR : no ThunderBorg at address {:02x}, but we did find boards:'.format(TB.i2cAddress) + Style.RESET_ALL)
                for board in boards:
                    print('tbconfig          :' + Fore.RED + Style.BRIGHT + ' ERROR :     {:02x} {:d}'.format(board, board))
                print('tbconfig          :' + Fore.RED + Style.BRIGHT + ' ERROR : if you need to change the I²C address change the setup line so it is correct, e.g. TB.i2cAddress = {:0x}'.format(boards[0]) + Style.RESET_ALL)
            sys.exit(1)
        TB.SetLedShowBattery(True)
        return TB

    except Exception as e:
        print('tbconfig          :' + Fore.RED + Style.BRIGHT + ' ERROR : unable to import thunderborg: {}'.format(e) + Style.RESET_ALL)
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)


def _import_pigpio():
    try:
        import pigpio
        pi = pigpio.pi()
        print('import            :' + Fore.CYAN + ' INFO  : successfully imported pigpio.' + Style.RESET_ALL)
        return pi
    except Exception:
    #except ModuleNotFoundError:
        print('import            :' + Fore.RED + ' ERROR : failed to import pigpio, operating without Pi.' + Style.RESET_ALL)


# ..............................................................................
class Motors():
    '''
        A dual motor controller with encoders.
    '''
    def __init__(self, config, tb, pi, level):
        super().__init__()
        self._log = Logger('motors', level)
        self._log.info('initialising motors...')
        if pi is None:
            pi = _import_pigpio()
            if pi is None:
                raise Exception('unable to configure pigpio.')
        self._pi = pi
        if tb is None:
            tb = _configure_thunderborg_motors()
            if tb is None:
                raise Exception('unable to configure thunderborg.')
        self._tb = tb
        self._set_max_power_ratio()

        self._port_motor = Motor(config, self._tb, self._pi, Orientation.PORT, level)
        self._port_motor.set_max_power_ratio(self._max_power_ratio)
#       self._log.debug('implementing class for port motor: {}'.format(type(self._port_motor)))
        self._stbd_motor = Motor(config, self._tb, self._pi, Orientation.STBD, level)
        self._stbd_motor.set_max_power_ratio(self._max_power_ratio)
#       self._log.debug('implementing class for starboard motor: {}'.format(type(self._stbd_motor)))
        self._enabled = True # default enabled
        # a dictionary of motor # to last set value
        self._msgIndex = 0
        self._last_set_power = { 0:0, 1:0 }
        self._log.info('motors ready.')


    # ..........................................................................
    def _set_max_power_ratio(self):
        pass
        # initialise ThunderBorg ...........................
        print('motors            :' + Fore.CYAN + ' INFO  : getting battery reading...' + Style.RESET_ALL)
        # get battery voltage to determine max motor power
        # could be: Makita 12V or 18V power tool battery, or 12-20V line supply
        voltage_in = self._tb.GetBatteryReading()
        if voltage_in is None:
            raise OSError('cannot continue: cannot read battery voltage.')
        print('motors            :' + Fore.CYAN + ' INFO  : voltage in:  {:>5.2f}V'.format(voltage_in) + Style.RESET_ALL)
#       voltage_in = 20.5
        # maximum motor voltage
        voltage_out = 9.0
        print('motors            :' + Fore.CYAN + ' INFO  : voltage out: {:>5.2f}V'.format(voltage_out) + Style.RESET_ALL)
        if voltage_in < voltage_out:
            raise OSError('cannot continue: battery voltage too low ({:>5.2f}V).'.format(voltage_in))
        # Setup the power limits
        if voltage_out > voltage_in:
            self._max_power_ratio = 1.0
        else:
            self._max_power_ratio = voltage_out / float(voltage_in)
        # convert float to ratio format
        print('motors            :' + Fore.CYAN + ' INFO  : battery level: {:>5.2f}V; motor voltage: {:>5.2f}V; maximum power ratio: {}'.format(voltage_in, voltage_out, \
                str(Fraction(self._max_power_ratio).limit_denominator(max_denominator=20)).replace('/',':')) + Style.RESET_ALL)


    # ..........................................................................
    def get_motor(self, orientation):
        if orientation is Orientation.PORT:
            return self._port_motor
        else:
            return self._stbd_motor


    # ..........................................................................
    def enable(self):
        self._enabled = True


    # ..........................................................................
    def disable(self):
        '''
            Disable the motors, halting first if in motion.
        '''
        self._log.info('disabling motors...')
        self._enabled = False
        if self.is_in_motion(): # if we're moving then halt
            self._log.warning('event: motors are in motion (halting).')
            self.halt()
        self._log.info('motors disabled.')


    # ..........................................................................
    def is_in_motion(self):
        '''
            Returns true if either motor is moving.
        '''
        return self._port_motor.is_in_motion() or self._stbd_motor.is_in_motion()


    # ..........................................................................
    def is_faster_than(self, speed):
        '''
            Returns true if either motor is moving faster than the argument.
        '''
#   DEAD_SLOW_SPEED     = 20.0
#   SLOW_SPEED          = 30.0
#   HALF_SPEED          = 50.0
#   THREE_QUARTER_SPEED = 65.0
#   FULL_SPEED          = 80.0
#   EMERGENCY_SPEED     = 100.0
#   MAXIMUM             = 100.000001
        self._log.warning('SPEED {:5.2f} compared to port: {:>5.2f}; starboard: {:>5.2f}'.format(speed.value, self._port_motor.get_current_power_level(Orientation.PORT), \
                self._stbd_motor.get_current_power_level(Orientation.STBD)) )

        return ( self._port_motor.get_current_power_level(Orientation.PORT) > speed.value ) or ( self._stbd_motor.get_current_power_level(Orientation.STBD) > speed.value )


    # ..........................................................................
    def get_steps(self):
        '''
            Returns the port and starboard motor step count.
        '''
        return [ self._port_motor.get_steps() , self._stbd_motor.get_steps() ]


    # ..........................................................................
    def get_current_power_level(self, orientation):
        '''
            Returns the last set power of the specified motor.
        '''
        if orientation is Orientation.PORT:
            return self._port_motor.get_current_power_level(orientation)
        else:
            return self._stbd_motor.get_current_power_level(orientation)


    # ..........................................................................
    def close(self):
        '''
            Halts, turn everything off and stop doing anything.
        '''
        self._log.debug('closing...')
        self.halt()
        self._port_motor.close()
        self._stbd_motor.close()
        self._log.debug('closed.')


# Stopping Behaviours ....................................................................

    # ..........................................................................
    def interrupt(self):
        '''
            Interrupt any motor loops by setting the _interrupt flag.
        '''
        self._port_motor.interrupt()
        self._stbd_motor.interrupt()


    # ..........................................................................
    def halt(self):
        '''
            Quickly (but not immediately) stops both motors.
        '''
        self._log.info('halting...')
        if self.is_stopped():
            self._log.debug('already stopped.')
            return True

        # source: https://stackoverflow.com/questions/2957116/make-2-functions-run-at-the-same-time
        _tp = Thread(target=self.processStop, args=(Event.HALT, Orientation.PORT))
        _ts = Thread(target=self.processStop, args=(Event.HALT, Orientation.STBD))
        _tp.start()
        _ts.start()
        _tp.join()
        _ts.join()

        self._log.info('halted.')
        return True


    # ..........................................................................
    def brake(self):
        '''
            Slowly coasts both motors to a stop.
        '''
        self._log.info('braking...')
        if self.is_stopped():
            self._log.warning('already stopped.')
            return True

        _tp = Thread(target=self.processStop, args=(Event.BRAKE, Orientation.PORT))
        _ts = Thread(target=self.processStop, args=(Event.BRAKE, Orientation.STBD))
        _tp.start()
        _ts.start()
        _tp.join()
        _ts.join()

        self._log.info('braked.')
        return True


    # ..........................................................................
    def stop(self):
        '''
            Stops both motors immediately, with no slewing.
        '''
        self._log.info('stopping...')
        if self.is_stopped():
            self._log.warning('already stopped.')
            return True

        self._port_motor.stop()
        self._stbd_motor.stop()
        self._log.info('stopped.')
        return True


    # ..........................................................................
    def is_stopped(self):
        return self._port_motor.is_stopped() and self._stbd_motor.is_stopped()


# Synchronisation Support ................................................................


    # ..........................................................................
    def processStop(self, event, orientation):
        '''
            Synchronised process control over various kinds of stopping.
        '''
        if orientation is Orientation.PORT:
            if event is Event.HALT:
                self._log.info('halting port motor...')
                self._port_motor.halt()
            elif event is Event.BRAKE:
                self._log.info('braking port motor...')
                self._port_motor.brake()
            else: # is stop
                self._log.info('stopping port motor...')
                self._port_motor.stop()
        else:
            if event is Event.HALT:
                self._log.info('halting starboard motor...')
                self._stbd_motor.halt()
            elif event is Event.BRAKE:
                self._log.info('braking starboard motor...')
                self._stbd_motor.brake()
            else: # is stop
                self._log.info('stopping starboard motor...')
                self._stbd_motor.stop()
        self.print_current_power_levels()


    # ..........................................................................
    def get_current_power_levels(self):
        '''
            Returns the last set power values.
        '''
        _port_power = self._port_motor.get_current_power_level(Orientation.PORT)
        _stbd_power = self._stbd_motor.get_current_power_level(Orientation.STBD)
        return [ _port_power, _stbd_power ]


    # ..........................................................................
    def print_current_power_levels(self):
        '''
            Prints the last set power values.
        '''
        self._msgIndex += 1
        self._log.info('{}:\tcurrent power:\t{:6.1f}\t{:6.1f}'.format(self._msgIndex, self._last_set_power[0], self._last_set_power[1]))


    # ..........................................................................
    def accelerate(self, speed, slew_rate, steps, orientation):
        '''
            Unsynchronised (non-threaded) process control for a single motor. This
            is generally called by a dual-thread process to control both motors.
        '''
        if not self._enabled:
            self._log.info('cannot accelerate: motors disabled.')
            return
        self._log.debug('accelerating...')
        if orientation is Orientation.PORT:
            self._log.info('starting port motor with {:>5.2f} speed for {:d} steps...'.format(speed, steps))
            self._port_motor.accelerate(speed, slew_rate, steps)
        else:
            self._log.info('starting starboard motor with {:>5.2f} speed for {:d} steps...'.format(speed, steps))
            self._stbd_motor.accelerate(speed, slew_rate, steps)
        self._log.debug('accelerated.')


# Straight Movement Behaviours ...........................................................

    # ..........................................................................
    def accelerate_to_zero(self, slew_rate):
        '''
            Slows both motors to a stop at the provided slew rate.
        '''
        if not self._enabled:
            self._log.info('cannot change velocity: motors disabled.')
            return
        self._log.info('slow to zero...')
        _tp = Thread(target=self._accelerate_to_zero, args=(slew_rate, Orientation.PORT))
        _ts = Thread(target=self._accelerate_to_zero, args=(slew_rate, Orientation.STBD))
        _tp.start()
        _ts.start()
        _tp.join()
        _ts.join()
#       self.print_current_power_levels()
        self._log.info('motors slow to zero complete.')
        return True


    # ..........................................................................
    def _accelerate_to_zero(self, slew_rate, orientation):
        '''
            Synchronised process control for both motors, to slow to a stop.
        '''
        if not self._enabled:
            self._log.info('cannot continue: motors disabled.')
            return
        if orientation is Orientation.PORT:
            self._log.debug('slowing port motor to a stop...')
            self._port_motor.accelerate_to_zero(slew_rate)
        else:
            self._log.debug('slowing starboard motor to a stop...')
            self._stbd_motor.accelerate_to_zero(slew_rate)
        self._log.debug('accelerated.')


    # ..........................................................................
    def change_velocity(self, port_velocity, starboard_velocity, slew_rate, steps):
        '''
            Slews both motors to the designated velocities at a the provided slew rate.

            If steps is greater than zero it provides a step limit on the motors.
        '''
        #  https://stackoverflow.com/questions/2957116/make-2-functions-run-at-the-same-time
        #  https://github.com/ray-project/ray
        if not self._enabled:
            self._log.info('cannot change velocity: motors disabled.')
            return
        self._log.info('change ahead quickly to velocities; port: {:>5.2f}; stbd: {:>5.2f}.'.format(port_velocity, starboard_velocity))
        _tp = Thread(target=self._accelerate_to_velocity, args=(port_velocity, slew_rate, steps, Orientation.PORT))
        _ts = Thread(target=self._accelerate_to_velocity, args=(starboard_velocity, slew_rate, steps, Orientation.STBD))
        _tp.start()
        _ts.start()
        _tp.join()
        _ts.join()
#       self.print_current_power_levels()
        self._log.info('motors change velocity complete.')
        return True


    # ..........................................................................
    def _accelerate_to_velocity(self, velocity, slew_rate, steps, orientation):
        '''
            Synchronised process control for both motors, over various kinds of accelerating.
        '''
        if not self._enabled:
            self._log.info('cannot accelerate: motors disabled.')
            return
        self._log.debug('accelerating to velocity {:>6.3f}...'.format(velocity))
        if orientation is Orientation.PORT:
            self._log.debug('starting port motor with {:>5.2f} velocity...'.format(velocity))
            self._port_motor.accelerate_to_velocity(velocity, slew_rate, steps)
        else:
            self._log.debug('starting starboard motor with {:>5.2f} velocity...'.format(velocity))
            self._stbd_motor.accelerate_to_velocity(velocity, slew_rate, steps)
        self._log.debug('accelerated.')


    # ..........................................................................
    def step_to(self, steps):
        '''
            Maintains the current velocity and runs until the number of steps have been reached.
            The argument is in absolute steps, not relative to the beginning of the method call.
        '''
        if not self._enabled:
            self._log.info('cannot step ahead: motors disabled.')
            return
        self._log.info('change ahead quickly to {:d} steps.'.format(steps))
        _tp = Thread(target=self._step_to, args=(steps, Orientation.PORT))
        _ts = Thread(target=self._step_to, args=(steps, Orientation.STBD))
        _tp.start()
        _ts.start()
        _tp.join()
        _ts.join()
#       self.print_current_power_levels()
        self._log.info('motors step to complete.')
        return True


    # ..........................................................................
    def _step_to(self, steps, orientation):
        '''
            Steps the specified motor to a specific step location.
        '''
        if not self._enabled:
            self._log.info('cannot step to: motors disabled.')
        elif orientation is Orientation.PORT:
            self._log.info('advancing port motor to {:d} steps...'.format(steps))
            self._port_motor.step_to(steps)
        else:
            self._log.info('advancing starboard motor to {:d} steps...'.format(steps))
            self._stbd_motor.step_to(steps)


    # =======================================================================================================


    # ..........................................................................
    def ahead(self, speed):
        '''
            Slews both motors to move ahead at speed. 0 <= speed <= 100.
        '''
        if not self._enabled:
            self._log.info('cannot move ahead: motors disabled.')
            return
        self._log.info('motors ahead at speed {:6.3f}...'.format(speed))
        self.step(speed, speed, -1, -1)
        self._log.info('motors ahead complete.')
        return True


    # ..........................................................................
    def change_speed(self, speed):
        '''
            Slews both motors to the provided speed at a higher slew rate than 'ahead()'.
        '''
        if not self._enabled:
            self._log.info('cannot change speed: motors disabled.')
            return
        self._log.info('change ahead quickly to speed {:6.3f}.'.format(speed))
        _slew_rate = SlewRate.FAST
        _tp = Thread(target=self.accelerate, args=(speed, _slew_rate, -1, Orientation.PORT))
        _ts = Thread(target=self.accelerate, args=(speed, _slew_rate, -1, Orientation.STBD))
        _tp.start()
        _ts.start()
        _tp.join()
        _ts.join()
        self.print_current_power_levels()
        self._log.info('motors change speed complete.')
        return True


    # ..........................................................................
    def astern(self, speed):
        '''
            Slews both motors astern at Speed, using the enum. 

            The value of the enum is: 0 <= speed <= 100.
        '''
        if not self._enabled:
            self._log.info('cannot move astern: motors disabled.')
            return

        self._log.critical('motors astern at speed {:6.3f}...'.format(speed))

        self.step(-1.0 * speed,-1.0 * speed, -1, -1)

#       self.step(-1.0 * speed, -1.0 * speed, -1, -1)
#       _slew_rate = SlewRate.NORMAL
#       _tp = Thread(target=self.accelerate, args=(-1.0 * speed, _slew_rate, -1, Orientation.PORT))
#       _ts = Thread(target=self.accelerate, args=(-1.0 * speed, _slew_rate, -1, Orientation.STBD))
#       _tp.start()
#       _ts.start()
#       _tp.join()
#       _ts.join()

        self._log.critical('motors astern complete.')
        return True


    # ..........................................................................
    def stepAstern(self, speed, steps):
        '''
            Slews both motors astern the specified number of steps, then stops.
        '''
        if not self._enabled:
            self._log.info('cannot step astern: motors disabled.')
            return
        self._log.info('motors astern {} steps to speed of {:6.3f}...'.format(steps, speed))
        self.step(-1.0 * speed, -1.0 * speed, steps, steps)
        self._log.info('motors step astern complete.')
        return True


    # ..........................................................................
    def stepAhead(self, speed, steps):
        '''
            Slews ahead or astern the specified number of steps, then stops.
        '''
        if not self._enabled:
            self._log.info('cannot step ahead: motors disabled.')
            return
        self._log.info('motors ahead {} steps to speed of {:6.3f}...'.format(steps,speed))
        self.step(speed, speed, steps, steps)
        self._log.info('motors step ahead complete.')
        return True


# Turning Behaviours .....................................................................


    # ..........................................................................
    def turnAhead(self, port_speed, stbd_speed):
        '''
            Moves ahead in an arc by setting different speeds. 0 <= port_speed,starboard_speed <= 100

            If the port speed is greater than the starboard the robot will curve to starboard (clockwise).

            If the starboard speed is greater than the port the robot will curve to port (counter-clockwise).
        '''
        if not self._enabled:
            self._log.info('cannot turn ahead: motors disabled.')
            return
        self._log.info('turning with port speed {:6.3f} and starboard speed {:6.3f}.'.format(port_speed, stbd_speed))
        self.step(abs(port_speed), abs(stbd_speed), -1, -1)
        self._log.info('turned ahead.')
        return True


    # ..........................................................................
    def turnAstern(self, port_speed, stbd_speed):
        '''
            Moves astern in an arc by setting different speeds. 0 <= port_speed,starboard_speed <= 100

            If the port speed is greater than the starboard the robot will curve to starboard (clockwise).

            If the starboard speed is greater than the port the robot will curve to port (counter-clockwise).
        '''
        if not self._enabled:
            self._log.info('cannot turn astern: motors disabled.')
            return
        self._log.info('turning astern with port speed {:6.3f} and starboard speed {:6.3f}.'.format(port_speed, stbd_speed))
        self.step(-1.0 * abs(port_speed), -1.0 * abs(stbd_speed), -1, -1)
        self._log.info('turned astern.')
        return True


    # ..........................................................................
    def stepTurnAstern(self, port_speed, stbd_speed, port_steps, stbd_steps):
        '''
            Turns astern using the port and starboard speeds, going the number of port and starboard steps before stopping.
            If a step argument is -1 no step limit is set.

            If the port speed is greater than the starboard the robot will curve to starboard (clockwise).

            If the starboard speed is greater than the port the robot will curve to port (counter-clockwise).
        '''
        if not self._enabled:
            self._log.info('cannot step turn astern: motors disabled.')
            return
        self._log.info('astern turning with port speed {:6.3f} for {} steps and starboard speed {:6.3f} for {} steps.'.format(port_speed, port_steps, stbd_speed, stbd_steps))
        self.step(-1.0 * abs(port_speed), -1.0 * abs(stbd_speed), port_steps, stbd_steps)
        self._log.info('step turned astern.')
        return True


    # ..........................................................................
    def step(self, port_speed, stbd_speed, port_steps, stbd_steps):
        '''
            Moves ahead or backward using the designated port and starboard speeds, going the number 
            of port and starboard steps before stopping. If a step argument is -1 no step limit is set.

            If the speeds are equal the robot will move ahead or astern in a straight line.

            If the port speed is greater than the starboard the robot will curve to starboard (clockwise).

            If the starboard speed is greater than the port the robot will curve to port (counter-clockwise).

            This is the method that actually does all the work.
        '''
        if not self._enabled:
            self._log.info('cannot step: motors disabled.')
            return
        self._log.info('step with port speed {:6.3f} for {} steps and starboard speed {:6.3f} for {} steps.'.format(port_speed, port_steps, stbd_speed, stbd_steps))
        _slew_rate = SlewRate.NORMAL
        _tp = Thread(target=self.accelerate, args=(port_speed, _slew_rate, port_steps, Orientation.PORT))
        _ts = Thread(target=self.accelerate, args=(stbd_speed, _slew_rate, stbd_steps, Orientation.STBD))
        _tp.start()
        _ts.start()
        _tp.join()
        _ts.join()
        self.print_current_power_levels()
        self._log.info('step complete.')


# Spinning Behaviours ....................................................................


    # ..........................................................................
    def spinPort(self, speed):
        '''
            Halts, then sets motors to turn counter-clockwise at speed. 0 <= speed <= 100
        '''
        if not self._enabled:
            self._log.info('cannot spin to port: motors disabled.')
            return
        self._log.info('spinning to port at speed {:6.3f}...'.format(speed))
        self.stepSpin(Orientation.PORT, speed, -1)
        self._log.info('spun to port.')
        return True


    # ..........................................................................
    def spinStarboard(self, speed):
        '''
            Halts, then sets motors to turn clockwise at speed. 0 <= speed <= 100
        '''
        if not self._enabled:
            self._log.info('cannot spin to starboard: motors disabled.')
            return
        self._log.info('spinning to starboard at speed {:6.3f}...'.format(speed))
        self.stepSpin(Orientation.STBD, speed, -1)
        self._log.info('spun to starboard.')
        return True


    # ..........................................................................
    def stepSpin(self, orientation, speed, steps):
        '''
            Halts, then spins to port (counter-clockwise) or starboard (clockwise)
            at the specified speed and steps, then stops.
        '''
        if not self._enabled:
            self._log.info('cannot step spin to port: motors disabled.')
            return
        self.halt()

        _slew_rate = SlewRate.NORMAL
        if orientation is Orientation.PORT:
            self._log.info('spinning to port {} steps at speed {:6.3f}...'.format(steps, speed))
            _port_speed = abs(speed)
            _starboard_speed = -1.0 * abs(speed)
        else:
            self._log.info('spinning to starboard {} steps at speed {:6.3f}...'.format(steps, speed))
            _port_speed = -1.0 * abs(speed)
            _starboard_speed = abs(speed)
        _tp = Thread(target=self.accelerate, args=(_port_speed, _slew_rate, steps, Orientation.PORT))
        _ts = Thread(target=self.accelerate, args=(_starboard_speed, _slew_rate, steps, Orientation.STBD))
        _tp.start()
        _ts.start()
        _tp.join()
        _ts.join()
        self.print_current_power_levels()

        if orientation is Orientation.PORT:
            self._log.info('step spun to port.')
        else:
            self._log.info('step spun to starboard.')
        return True



    @staticmethod
    def cancel():
        print('cancelling motors...')
        Motor.cancel()


#EOF