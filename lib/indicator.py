#!/usr/bin/env python3

import time, colorsys
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.event import Event
from lib.enums import Color
from rgbmatrix5x5 import RGBMatrix5x5


# ..............................................................................
class Indicator():
    '''
        This uses an RgbMatrix5x5 display as a sensor indicator:

               DS  DA  DA  DA  DP

               DS  CH  CH  CH  DP

               DS  DF  DF  DF  DP

               --  BS  BC  BP  --

               SS  IS  IC  IP  PS

       where: 
         -- = no display
         DP = direction to port
         DA = direction aft
         DS = direction to starboard
         CH = compass heading
         DF = direction forward
         BS = starboard bumper
         BC = center bumper
         BP = port bumper
         SS = starboard side IR
         IS = starboard IR
         IC = center IR
         IP = port IR
         PS = port side IR

        This additionally implements the add(message) method to act as a
        consumer on the message queue.
    '''
    def __init__(self, level):
        self._log = Logger("indicator", level)
        self._rgbmatrix5x5 = RGBMatrix5x5(address=0x74)
        self._log.debug('rgbmatrix at 0x74.')
        self._rgbmatrix5x5.set_brightness(0.8)
        self._rgbmatrix5x5.set_clear_on_exit()
        self._height = self._rgbmatrix5x5.height
        self._width  = self._rgbmatrix5x5.width
        self._log.info('ready.')


    # ..........................................................................
    def add(self, message):
        '''
            Receives a message and reacts by setting the display accordingly.
            This does not modify the message.
        '''
        self._log.debug('added message #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
        event = message.get_event()

        if event is Event.INFRARED_PORT_SIDE:
            self.set_ir_sensor_port_side(True, False)
            self._log.debug(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_PORT_SIDE_FAR:
            self.set_ir_sensor_port_side(True, True)
            self._log.debug(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))

        elif event is Event.INFRARED_PORT:
            self.set_ir_sensor_port(True, False)
            self._log.debug(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_PORT_FAR:
            self.set_ir_sensor_port(True, True)
            self._log.debug(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))

        elif event is Event.INFRARED_CNTR:
            self.set_ir_sensor_center(True, False)
            self._log.debug(Fore.BLUE + Style.BRIGHT  + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_CNTR_FAR:
            self.set_ir_sensor_center(True, True)
            self._log.debug(Fore.BLUE + Style.BRIGHT  + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))

        elif event is Event.INFRARED_STBD:
            self.set_ir_sensor_stbd(True, False)
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_STBD_FAR:
            self.set_ir_sensor_stbd(True, True)
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))

        elif event is Event.INFRARED_STBD_SIDE:
            self.set_ir_sensor_stbd_side(True, False)
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_STBD_SIDE_FAR:
            self.set_ir_sensor_stbd_side(True, True)
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))

        elif event is Event.BUMPER_PORT:
            self.set_bumper_port(True)
            self._log.debug(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.BUMPER_CNTR:
            self.set_bumper_center(True)
            self._log.debug(Fore.BLUE + Style.BRIGHT  + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.BUMPER_STBD:
            self.set_bumper_stbd(True)
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        else:
            self._log.debug(Fore.RED + 'other event: {}'.format(event.description))
            pass
        self.clear()

    # ..........................................................................
    def clear(self):
        self.set_color(Color.BLACK)

    # ..........................................................................
    def set_color(self, color):
#       for y in range(self._height):
#           for x in range(self._width):
#               self._rgbmatrix5x5.set_pixel(x, y, color.red, color.green, color.blue)
        self._rgbmatrix5x5.set_all(color.red, color.green, color.blue)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_heading(self, hue):
        '''
            Converts a hue value into an RGB value and displays it on the heading portion of the pixels.

            The hue value should be in degrees from 0-360, as colors on a color wheel.
        '''
        _offset = 0
        if hue < 0:
            r, g, b = [ Color.VERY_DARK_GREY.red, Color.VERY_DARK_GREY.green, Color.VERY_DARK_GREY.blue ]
            self._log.debug(Fore.WHITE + Style.NORMAL + 'uncalibrated; hue {}: rgb: {}/{}/{}'.format(hue, r, g, b))
        else:
            h = ((hue + _offset) % 360) / 360.0
            r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0)]
            self._log.debug(Fore.GREEN + Style.NORMAL + 'hue: {}/{:>5.2f}; rgb: {}/{}/{}'.format(hue, h, r, g, b))
#       self._rgbmatrix5x5.set_all(r, g, b)
        self._rgbmatrix5x5.set_pixel(0, 0, r, g, b)
        self._rgbmatrix5x5.set_pixel(0, 1, r, g, b)
        self._rgbmatrix5x5.set_pixel(0, 2, r, g, b)
        self._rgbmatrix5x5.set_pixel(0, 3, r, g, b)
        self._rgbmatrix5x5.set_pixel(0, 4, r, g, b)
        self._rgbmatrix5x5.set_pixel(1, 0, r, g, b)
        self._rgbmatrix5x5.set_pixel(1, 1, r, g, b)
        self._rgbmatrix5x5.set_pixel(1, 2, r, g, b)
        self._rgbmatrix5x5.set_pixel(1, 3, r, g, b)
        self._rgbmatrix5x5.set_pixel(1, 4, r, g, b)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_direction_fwd(self, enable):
        _color = Color.CYAN if enable else Color.BLACK
        self._rgbmatrix5x5.set_pixel(2, 1, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.set_pixel(2, 2, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.set_pixel(2, 3, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_direction_port(self, enable):
        _color = Color.RED if enable else Color.BLACK
        self._rgbmatrix5x5.set_pixel(0, 4, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.set_pixel(1, 4, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.set_pixel(2, 4, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_direction_aft(self, enable):
        _color = Color.YELLOW if enable else Color.BLACK
        self._rgbmatrix5x5.set_pixel(0, 1, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.set_pixel(0, 2, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.set_pixel(0, 3, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_direction_stbd(self, enable):
        _color = Color.GREEN if enable else Color.BLACK
        self._rgbmatrix5x5.set_pixel(0, 0, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.set_pixel(1, 0, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.set_pixel(2, 0, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_ir_sensor_port_side(self, enable, far):
        if enable:
            if far:
                _color = Color.DARK_RED
            else:
                _color = Color.RED
        else:
            _color = Color.BLACK
        self._rgbmatrix5x5.set_pixel(4, 4, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_ir_sensor_port(self, enable, far):
        if enable:
            if far:
                _color = Color.DARK_MAGENTA
            else:
                _color = Color.MAGENTA
        else:
            _color = Color.BLACK
        self._rgbmatrix5x5.set_pixel(4, 3, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_ir_sensor_center(self, enable, far):
        if enable:
            if far:
                _color = Color.DARK_BLUE
            else:
                _color = Color.BLUE
        else:
            _color = Color.BLACK
        self._rgbmatrix5x5.set_pixel(4, 2, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_ir_sensor_stbd(self, enable, far):
        if enable:
            if far:
                _color = Color.DARK_CYAN
            else:
                _color = Color.CYAN
        else:
            _color = Color.BLACK
        self._rgbmatrix5x5.set_pixel(4, 1, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_ir_sensor_stbd_side(self, enable, far):
        if enable:
            if far:
                _color = Color.DARK_GREEN
            else:
                _color = Color.GREEN
        else:
            _color = Color.BLACK
        self._rgbmatrix5x5.set_pixel(4, 0, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_bumper_port(self, enable):
        _color = Color.RED if enable else Color.BLACK
        self._rgbmatrix5x5.set_pixel(3, 3, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_bumper_center(self, enable):
        _color = Color.BLUE if enable else Color.BLACK
        self._rgbmatrix5x5.set_pixel(3, 2, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.show()

    # ..........................................................................
    def set_bumper_stbd(self, enable):
        _color = Color.GREEN if enable else Color.BLACK
        self._rgbmatrix5x5.set_pixel(3, 1, _color.red, _color.green, _color.blue)
        self._rgbmatrix5x5.show()

#EOF
