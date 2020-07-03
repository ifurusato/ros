#!/usr/bin/env python3
# coding: latin-1
"""
This module is designed to communicate with the UltraBorg

Use by creating an instance of the class, call the Init function, then command as desired, e.g.
import UltraBorg
UB = UltraBorg.UltraBorg()
UB.Init()
# User code here, use UB to control the board

Multiple boards can be used when configured with different I²C addresses by creating multiple instances, e.g.
import UltraBorg
UB1 = UltraBorg.UltraBorg()
UB2 = UltraBorg.UltraBorg()
UB1.i2cAddress = 0x44
UB2.i2cAddress = 0x45
UB1.Init()
UB2.Init()
# User code here, use UB1 and UB2 to control each board separately

For explanations of the functions available call the Help function, e.g.
import UltraBorg
UB = UltraBorg.UltraBorg()
UB.Help()
See the website at www.piborg.org/ultraborg for more details
"""

# Import the libraries we need
import io, fcntl, types, time

from colorama import init, Fore, Style
init()

# Constant values
I2C_SLAVE               = 0x0703
I2C_MAX_LEN             = 4
USM_US_TO_MM            = 0.171500
PWM_MIN                 = 2000  # Should be a 1 ms burst, typical servo minimum
PWM_MAX                 = 4000  # Should be a 2 ms burst, typical servo maximum
DELAY_AFTER_EEPROM      = 0.01  # Time to wait after updating an EEPROM value before reading
PWM_UNSET               = 0xFFFF
READ_DELAY_SEC          = 0.01 # time to wait for a reading off of the ultrasonic sensor
#READ_DELAY_SEC          = 0.0001 # time to wait for a reading off of the ultrasonic sensor

I2C_ID_SERVO_USM        = 0x36

COMMAND_GET_TIME_USM1   = 1     # Get the time measured by ultrasonic #1 in us (0 for no detection)
COMMAND_GET_TIME_USM2   = 2     # Get the time measured by ultrasonic #2 in us (0 for no detection)
COMMAND_GET_TIME_USM3   = 3     # Get the time measured by ultrasonic #3 in us (0 for no detection)
COMMAND_GET_TIME_USM4   = 4     # Get the time measured by ultrasonic #4 in us (0 for no detection)
COMMAND_SET_PWM1        = 5     # Set the PWM duty cycle for drive #1 (16 bit)
COMMAND_GET_PWM1        = 6     # Get the PWM duty cycle for drive #1 (16 bit)
COMMAND_SET_PWM2        = 7     # Set the PWM duty cycle for drive #2 (16 bit)
COMMAND_GET_PWM2        = 8     # Get the PWM duty cycle for drive #2 (16 bit)
COMMAND_SET_PWM3        = 9     # Set the PWM duty cycle for drive #3 (16 bit)
COMMAND_GET_PWM3        = 10    # Get the PWM duty cycle for drive #3 (16 bit)
COMMAND_SET_PWM4        = 11    # Set the PWM duty cycle for drive #4 (16 bit)
COMMAND_GET_PWM4        = 12    # Get the PWM duty cycle for drive #4 (16 bit)
COMMAND_CALIBRATE_PWM1  = 13    # Set the PWM duty cycle for drive #1 (16 bit, ignores limit checks)
COMMAND_CALIBRATE_PWM2  = 14    # Set the PWM duty cycle for drive #2 (16 bit, ignores limit checks)
COMMAND_CALIBRATE_PWM3  = 15    # Set the PWM duty cycle for drive #3 (16 bit, ignores limit checks)
COMMAND_CALIBRATE_PWM4  = 16    # Set the PWM duty cycle for drive #4 (16 bit, ignores limit checks)
COMMAND_GET_PWM_MIN_1   = 17    # Get the minimum allowed PWM duty cycle for drive #1
COMMAND_GET_PWM_MAX_1   = 18    # Get the maximum allowed PWM duty cycle for drive #1
COMMAND_GET_PWM_BOOT_1  = 19    # Get the startup PWM duty cycle for drive #1
COMMAND_GET_PWM_MIN_2   = 20    # Get the minimum allowed PWM duty cycle for drive #2
COMMAND_GET_PWM_MAX_2   = 21    # Get the maximum allowed PWM duty cycle for drive #2
COMMAND_GET_PWM_BOOT_2  = 22    # Get the startup PWM duty cycle for drive #2
COMMAND_GET_PWM_MIN_3   = 23    # Get the minimum allowed PWM duty cycle for drive #3
COMMAND_GET_PWM_MAX_3   = 24    # Get the maximum allowed PWM duty cycle for drive #3
COMMAND_GET_PWM_BOOT_3  = 25    # Get the startup PWM duty cycle for drive #3
COMMAND_GET_PWM_MIN_4   = 26    # Get the minimum allowed PWM duty cycle for drive #4
COMMAND_GET_PWM_MAX_4   = 27    # Get the maximum allowed PWM duty cycle for drive #4
COMMAND_GET_PWM_BOOT_4  = 28    # Get the startup PWM duty cycle for drive #4
COMMAND_SET_PWM_MIN_1   = 29    # Set the minimum allowed PWM duty cycle for drive #1
COMMAND_SET_PWM_MAX_1   = 30    # Set the maximum allowed PWM duty cycle for drive #1
COMMAND_SET_PWM_BOOT_1  = 31    # Set the startup PWM duty cycle for drive #1
COMMAND_SET_PWM_MIN_2   = 32    # Set the minimum allowed PWM duty cycle for drive #2
COMMAND_SET_PWM_MAX_2   = 33    # Set the maximum allowed PWM duty cycle for drive #2
COMMAND_SET_PWM_BOOT_2  = 34    # Set the startup PWM duty cycle for drive #2
COMMAND_SET_PWM_MIN_3   = 35    # Set the minimum allowed PWM duty cycle for drive #3
COMMAND_SET_PWM_MAX_3   = 36    # Set the maximum allowed PWM duty cycle for drive #3
COMMAND_SET_PWM_BOOT_3  = 37    # Set the startup PWM duty cycle for drive #3
COMMAND_SET_PWM_MIN_4   = 38    # Set the minimum allowed PWM duty cycle for drive #4
COMMAND_SET_PWM_MAX_4   = 39    # Set the maximum allowed PWM duty cycle for drive #4
COMMAND_SET_PWM_BOOT_4  = 40    # Set the startup PWM duty cycle for drive #4
COMMAND_GET_FILTER_USM1 = 41    # Get the filtered time measured by ultrasonic #1 in us (0 for no detection)
COMMAND_GET_FILTER_USM2 = 42    # Get the filtered time measured by ultrasonic #2 in us (0 for no detection)
COMMAND_GET_FILTER_USM3 = 43    # Get the filtered time measured by ultrasonic #3 in us (0 for no detection)
COMMAND_GET_FILTER_USM4 = 44    # Get the filtered time measured by ultrasonic #4 in us (0 for no detection)
COMMAND_GET_ID          = 0x99  # Get the board identifier
COMMAND_SET_I2C_ADD     = 0xAA  # Set a new I2C address

COMMAND_VALUE_FWD       = 1     # I2C value representing forward
COMMAND_VALUE_REV       = 2     # I2C value representing reverse

COMMAND_VALUE_ON        = 1     # I2C value representing on
COMMAND_VALUE_OFF       = 0     # I2C value representing off


def ScanForUltraBorg(busNumber = 1):
    """
ScanForUltraBorg([busNumber])

Scans the I²C bus for a UltraBorg boards and returns a list of all usable addresses
The busNumber if supplied is which I²C bus to scan, 0 for Rev 1 boards, 1 for Rev 2 boards, if not supplied the default is 1
    """
    found = []
    print('Scanning I²C bus #%d' % (busNumber))
    bus = UltraBorg()
    for address in range(0x03, 0x78, 1):
        try:
            bus.InitBusOnly(busNumber, address)
            i2cRecv = bus.RawRead(COMMAND_GET_ID, I2C_MAX_LEN)
            if len(i2cRecv) == I2C_MAX_LEN:
                if i2cRecv[1] == I2C_ID_SERVO_USM:
                    print('Found UltraBorg at %02X' % (address))
                    found.append(address)
                else:
                    pass
            else:
                pass
        except KeyboardInterrupt:
            raise
        except:
            pass
    if len(found) == 0:
        print('No UltraBorg boards found, is bus #%d correct (should be 0 for Rev 1, 1 for Rev 2)' % (busNumber))
    elif len(found) == 1:
        print('1 UltraBorg board found')
    else:
        print('%d UltraBorg boards found' % (len(found)))
    return found


def SetNewAddress(newAddress, oldAddress = -1, busNumber = 1):
    """
SetNewAddress(newAddress, [oldAddress], [busNumber])

Scans the I²C bus for the first UltraBorg and sets it to a new I2C address
If oldAddress is supplied it will change the address of the board at that address rather than scanning the bus
The busNumber if supplied is which I²C bus to scan, 0 for Rev 1 boards, 1 for Rev 2 boards, if not supplied the default is 1
Warning, this new I²C address will still be used after resetting the power on the device
    """
    if newAddress < 0x03:
        print('Error, I²C addresses below 3 (0x03) are reserved, use an address between 3 (0x03) and 119 (0x77)')
        return
    elif newAddress > 0x77:
        print('Error, I²C addresses above 119 (0x77) are reserved, use an address between 3 (0x03) and 119 (0x77)')
        return
    if oldAddress < 0x0:
        found = ScanForUltraBorg(busNumber)
        if len(found) < 1:
            print('No UltraBorg boards found, cannot set a new I²C address!')
            return
        else:
            oldAddress = found[0]
    print('Changing I²C address from %02X to %02X (bus #%d)' % (oldAddress, newAddress, busNumber))
    bus = UltraBorg()
    bus.InitBusOnly(busNumber, oldAddress)
    try:
        i2cRecv = bus.RawRead(COMMAND_GET_ID, I2C_MAX_LEN)
        if len(i2cRecv) == I2C_MAX_LEN:
            if i2cRecv[1] == I2C_ID_SERVO_USM:
                foundChip = True
                print('Found UltraBorg at %02X' % (oldAddress))
            else:
                foundChip = False
                print('Found a device at %02X, but it is not a UltraBorg (ID %02X instead of %02X)' % (oldAddress, i2cRecv[1], I2C_ID_SERVO_USM))
        else:
            foundChip = False
            print('Missing UltraBorg at %02X' % (oldAddress))
    except KeyboardInterrupt:
        raise
    except:
        foundChip = False
        print('Missing UltraBorg at %02X' % (oldAddress))
    if foundChip:
        bus.RawWrite(COMMAND_SET_I2C_ADD, [newAddress])
        time.sleep(0.1)
        print('Address changed to %02X, attempting to talk with the new address' % (newAddress))
        try:
            bus.InitBusOnly(busNumber, newAddress)
            i2cRecv = bus.RawRead(COMMAND_GET_ID, I2C_MAX_LEN)
            if len(i2cRecv) == I2C_MAX_LEN:
                if i2cRecv[1] == I2C_ID_SERVO_USM:
                    foundChip = True
                    print('Found UltraBorg at %02X' % (newAddress))
                else:
                    foundChip = False
                    print('Found a device at %02X, but it is not a UltraBorg (ID %02X instead of %02X)' % (newAddress, i2cRecv[1], I2C_ID_SERVO_USM))
            else:
                foundChip = False
                print('Missing UltraBorg at %02X' % (newAddress))
        except KeyboardInterrupt:
            raise
        except:
            foundChip = False
            print('Missing UltraBorg at %02X' % (newAddress))
    if foundChip:
        print('New I²C address of %02X set successfully' % (newAddress))
    else:
        print('Failed to set new I²C address...')


# Class used to control UltraBorg
class UltraBorg:
    """
This module is designed to communicate with the UltraBorg

busNumber               I²C bus on which the UltraBorg is attached (Rev 1 is bus 0, Rev 2 is bus 1)
bus                     the smbus object used to talk to the I²C bus
i2cAddress              The I²C address of the UltraBorg chip to control
foundChip               True if the UltraBorg chip can be seen, False otherwise
printFunction           Function reference to call when printing text, if None "print" is used
    """

    # Shared values used by this class
    busNumber               = 1                 # Check here for Rev 1 vs Rev 2 and select the correct bus
    i2cAddress              = I2C_ID_SERVO_USM  # I²C address, override for a different address
    foundChip               = False
    printFunction           = None
    i2cWrite                = None
    i2cRead                 = None

    # Default calibration adjustments to standard values
    PWM_MIN_1               = PWM_MIN
    PWM_MAX_1               = PWM_MAX
    PWM_MIN_2               = PWM_MIN
    PWM_MAX_2               = PWM_MAX
    PWM_MIN_3               = PWM_MIN
    PWM_MAX_3               = PWM_MAX
    PWM_MIN_4               = PWM_MIN
    PWM_MAX_4               = PWM_MAX

    def RawWrite(self, command, data):
        """
RawWrite(command, data)

Sends a raw command on the I2C bus to the UltraBorg
Command codes can be found at the top of UltraBorg.py, data is a list of 0 or more byte values

Under most circumstances you should use the appropriate function instead of RawWrite
        """
        rawOutput = [command]
        rawOutput.extend(data)
        rawOutput = bytes(rawOutput)
        self.i2cWrite.write(rawOutput)


    def RawRead(self, command, length, retryCount = 3):
        """
RawRead(command, length, [retryCount])

Reads data back from the UltraBorg after sending a GET command
Command codes can be found at the top of UltraBorg.py, length is the number of bytes to read back

The function checks that the first byte read back matches the requested command
If it does not it will retry the request until retryCount is exhausted (default is 3 times)

Under most circumstances you should use the appropriate function instead of RawRead
        """
        while retryCount > 0:
            self.RawWrite(command, [])
            time.sleep(READ_DELAY_SEC)
            rawReply = self.i2cRead.read(length)
            reply = []
            for singleByte in rawReply:
                reply.append(singleByte)
            if command == reply[0]:
                break
            else:
                retryCount -= 1
        if retryCount > 0:
            return reply
        else:
            raise IOError('I2C read for command %d failed' % (command))


    def InitBusOnly(self, busNumber, address):
        """
InitBusOnly(busNumber, address)

Prepare the I2C driver for talking to a UltraBorg on the specified bus and I2C address
This call does not check the board is present or working, under most circumstances use Init() instead
        """
        self.busNumber = busNumber
        self.i2cAddress = address
        self.i2cRead = io.open("/dev/i2c-" + str(self.busNumber), "rb", buffering = 0)
        fcntl.ioctl(self.i2cRead, I2C_SLAVE, self.i2cAddress)
        self.i2cWrite = io.open("/dev/i2c-" + str(self.busNumber), "wb", buffering = 0)
        fcntl.ioctl(self.i2cWrite, I2C_SLAVE, self.i2cAddress)


    def Print(self, message):
        """
Print(message)

Wrapper used by the UltraBorg instance to print messages, will call printFunction if set, print otherwise
        """
        if self.printFunction == None:
            print(Fore.BLACK + "ultraborg         : INFO  : " + message + Style.RESET_ALL)
        else:
            self.printFunction(message)


    def NoPrint(self, message):
        """
NoPrint(message)

Does nothing, intended for disabling diagnostic printout by using:
UB = UltraBorg.UltraBorg()
UB.printFunction = UB.NoPrint
        """
        pass


    def Init(self, tryOtherBus = False):
        """
Init([tryOtherBus])

Prepare the I2C driver for talking to the UltraBorg

If tryOtherBus is True, this function will attempt to use the other bus if the ThunderBorg devices can not be found on the current busNumber
    This is only really useful for early Raspberry Pi models!
        """
        self.Print('Loading UltraBorg on bus %d, address %02X' % (self.busNumber, self.i2cAddress))

        # Open the bus
        self.i2cRead = io.open("/dev/i2c-" + str(self.busNumber), "rb", buffering = 0)
        fcntl.ioctl(self.i2cRead, I2C_SLAVE, self.i2cAddress)
        self.i2cWrite = io.open("/dev/i2c-" + str(self.busNumber), "wb", buffering = 0)
        fcntl.ioctl(self.i2cWrite, I2C_SLAVE, self.i2cAddress)

        # Check for UltraBorg
        try:
            i2cRecv = self.RawRead(COMMAND_GET_ID, I2C_MAX_LEN)
            if len(i2cRecv) == I2C_MAX_LEN:
                if i2cRecv[1] == I2C_ID_SERVO_USM:
                    self.foundChip = True
                    self.Print('Found UltraBorg at %02X' % (self.i2cAddress))
                else:
                    self.foundChip = False
                    self.Print('Found a device at %02X, but it is not a UltraBorg (ID %02X instead of %02X)' % (self.i2cAddress, i2cRecv[1], I2C_ID_SERVO_USM))
            else:
                self.foundChip = False
                self.Print('Missing UltraBorg at %02X' % (self.i2cAddress))
        except KeyboardInterrupt:
            raise
        except:
            self.foundChip = False
            self.Print('Missing UltraBorg at %02X' % (self.i2cAddress))

        # See if we are missing chips
        if not self.foundChip:
            self.Print('UltraBorg was not found')
            if tryOtherBus:
                if self.busNumber == 1:
                    self.busNumber = 0
                else:
                    self.busNumber = 1
                self.Print('Trying bus %d instead' % (self.busNumber))
                self.Init(False)
            else:
                self.Print('Are you sure your UltraBorg is properly attached, the correct address is used, and the I2C drivers are running?')
                self.bus = None
        else:
            self.Print('UltraBorg loaded on bus %d' % (self.busNumber))

        # Read the calibration settings from the UltraBorg
        self.PWM_MIN_1 = self.GetWithRetry(self.GetServoMinimum1, 5)
        self.PWM_MAX_1 = self.GetWithRetry(self.GetServoMaximum1, 5)
        self.PWM_MIN_2 = self.GetWithRetry(self.GetServoMinimum2, 5)
        self.PWM_MAX_2 = self.GetWithRetry(self.GetServoMaximum2, 5)
        self.PWM_MIN_3 = self.GetWithRetry(self.GetServoMinimum3, 5)
        self.PWM_MAX_3 = self.GetWithRetry(self.GetServoMaximum3, 5)
        self.PWM_MIN_4 = self.GetWithRetry(self.GetServoMinimum4, 5)
        self.PWM_MAX_4 = self.GetWithRetry(self.GetServoMaximum4, 5)


    def GetWithRetry(self, function, count):
        """
value = GetWithRetry(function, count)

Attempts to read a value multiple times before giving up
Pass a get function with no parameters
e.g.
distance = GetWithRetry(UB.GetDistance1, 5)
Will try UB.GetDistance1() upto 5 times, returning when it gets a value
Useful for ensuring a read is successful
        """
        value = None
        for i in range(count):
            okay = True
            try:
                value = function()
            except KeyboardInterrupt:
                raise
            except:
                okay = False
            if okay:
                break
        return value


    def SetWithRetry(self, setFunction, getFunction, value, count):
        """
worked = SetWithRetry(setFunction, getFunction, value, count)

Attempts to write a value multiple times before giving up
Pass a set function with one parameter, and a get function no parameters
The get function will be used to check if the set worked, if not it will be repeated
e.g.
worked = SetWithRetry(UB.SetServoMinimum1, UB.GetServoMinimum1, 2000, 5)
Will try UB.SetServoMinimum1(2000) upto 5 times, returning when UB.GetServoMinimum1 returns 2000.
Useful for ensuring a write is successful
        """
        for i in range(count):
            okay = True
            try:
                setFunction(value)
                readValue = getFunction()
            except KeyboardInterrupt:
                raise
            except:
                okay = False
            if okay:
                if readValue == value:
                    break
                else:
                    okay = False
        return okay


    def GetDistance1(self):
        """
distance = GetDistance1()

Gets the filtered distance for ultrasonic module #1 in millimeters
Returns 0 for no object detected or no ultrasonic module attached
If you need a faster response try GetRawDistance1 instead (no filtering)
e.g.
0     -> No object in range
25    -> Object 25 mm away
1000  -> Object 1000 mm (1 m) away
3500  -> Object 3500 mm (3.5 m) away
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_FILTER_USM1, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading ultrasonic #1 distance!')
            return

        time_us = (i2cRecv[1] << 8) + i2cRecv[2]
        if time_us == 65535:
            time_us = 0
        return time_us * USM_US_TO_MM


    def GetDistance2(self):
        """
distance = GetDistance2()

Gets the filtered distance for ultrasonic module #2 in millimeters
Returns 0 for no object detected or no ultrasonic module attached
If you need a faster response try GetRawDistance2 instead (no filtering)
e.g.
0     -> No object in range
25    -> Object 25 mm away
1000  -> Object 1000 mm (1 m) away
3500  -> Object 3500 mm (3.5 m) away
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_FILTER_USM2, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading ultrasonic #2 distance!')
            return

        time_us = (i2cRecv[1] << 8) + i2cRecv[2]
        if time_us == 65535:
            time_us = 0
        return time_us * USM_US_TO_MM


    def GetDistance3(self):
        """
distance = GetDistance3()

Gets the filtered distance for ultrasonic module #3 in millimeters
Returns 0 for no object detected or no ultrasonic module attached
If you need a faster response try GetRawDistance3 instead (no filtering)
e.g.
0     -> No object in range
25    -> Object 25 mm away
1000  -> Object 1000 mm (1 m) away
3500  -> Object 3500 mm (3.5 m) away
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_FILTER_USM3, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading ultrasonic #3 distance!')
            return

        time_us = (i2cRecv[1] << 8) + i2cRecv[2]
        if time_us == 65535:
            time_us = 0
        return time_us * USM_US_TO_MM


    def GetDistance4(self):
        """
distance = GetDistance4()

Gets the filtered distance for ultrasonic module #4 in millimeters
Returns 0 for no object detected or no ultrasonic module attached
If you need a faster response try GetRawDistance4 instead (no filtering)
e.g.
0     -> No object in range
25    -> Object 25 mm away
1000  -> Object 1000 mm (1 m) away
3500  -> Object 3500 mm (3.5 m) away
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_FILTER_USM4, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading ultrasonic #4 distance!')
            return

        time_us = (i2cRecv[1] << 8) + i2cRecv[2]
        if time_us == 65535:
            time_us = 0
        return time_us * USM_US_TO_MM



    def GetRawDistance1(self):
        """
distance = GetRawDistance1()

Gets the raw distance for ultrasonic module #1 in millimeters
Returns 0 for no object detected or no ultrasonic module attached
For a filtered (less jumpy) reading use GetDistance1
e.g.
0     -> No object in range
25    -> Object 25 mm away
1000  -> Object 1000 mm (1 m) away
3500  -> Object 3500 mm (3.5 m) away
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_TIME_USM1, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading ultrasonic #1 distance!')
            return

        time_us = (i2cRecv[1] << 8) + i2cRecv[2]
        if time_us == 65535:
            time_us = 0
        return time_us * USM_US_TO_MM


    def GetRawDistance2(self):
        """
distance = GetRawDistance2()

Gets the raw distance for ultrasonic module #2 in millimeters
Returns 0 for no object detected or no ultrasonic module attached
For a filtered (less jumpy) reading use GetDistance2
e.g.
0     -> No object in range
25    -> Object 25 mm away
1000  -> Object 1000 mm (1 m) away
3500  -> Object 3500 mm (3.5 m) away
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_TIME_USM2, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading ultrasonic #2 distance!')
            return

        time_us = (i2cRecv[1] << 8) + i2cRecv[2]
        if time_us == 65535:
            time_us = 0
        return time_us * USM_US_TO_MM


    def GetRawDistance3(self):
        """
distance = GetRawDistance3()

Gets the raw distance for ultrasonic module #3 in millimeters
Returns 0 for no object detected or no ultrasonic module attached
For a filtered (less jumpy) reading use GetDistance3
e.g.
0     -> No object in range
25    -> Object 25 mm away
1000  -> Object 1000 mm (1 m) away
3500  -> Object 3500 mm (3.5 m) away
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_TIME_USM3, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading ultrasonic #3 distance!')
            return

        time_us = (i2cRecv[1] << 8) + i2cRecv[2]
        if time_us == 65535:
            time_us = 0
        return time_us * USM_US_TO_MM


    def GetRawDistance4(self):
        """
distance = GetRawDistance4()

Gets the distance for ultrasonic module #4 in millimeters
Returns 0 for no object detected or no ultrasonic module attached
For a filtered (less jumpy) reading use GetDistance4
e.g.
0     -> No object in range
25    -> Object 25 mm away
1000  -> Object 1000 mm (1 m) away
3500  -> Object 3500 mm (3.5 m) away
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_TIME_USM4, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading ultrasonic #4 distance!')
            return

        time_us = (i2cRecv[1] << 8) + i2cRecv[2]
        if time_us == 65535:
            time_us = 0
        return time_us * USM_US_TO_MM


    def GetServoPosition1(self):
        """
position = GetServoPosition1()

Gets the drive position for servo output #1
0 is central, -1 is maximum left, +1 is maximum right
e.g.
0     -> Central
0.5   -> 50% to the right
1     -> 100% to the right
-0.75 -> 75% to the left
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM1, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo output #1!')
            return

        pwmDuty = (i2cRecv[1] << 8) + i2cRecv[2]
        powerOut = (float(pwmDuty) - self.PWM_MIN_1) / (self.PWM_MAX_1 - self.PWM_MIN_1)
        return (2.0 * powerOut) - 1.0


    def GetServoPosition2(self):
        """
position = GetServoPosition2()

Gets the drive position for servo output #2
0 is central, -1 is maximum left, +1 is maximum right
e.g.
0     -> Central
0.5   -> 50% to the right
1     -> 100% to the right
-0.75 -> 75% to the left
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM2, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo output #2!')
            return

        pwmDuty = (i2cRecv[1] << 8) + i2cRecv[2]
        powerOut = (float(pwmDuty) - self.PWM_MIN_2) / (self.PWM_MAX_2 - self.PWM_MIN_2)
        return (2.0 * powerOut) - 1.0


    def GetServoPosition3(self):
        """
position = GetServoPosition3()

Gets the drive position for servo output #3
0 is central, -1 is maximum left, +1 is maximum right
e.g.
0     -> Central
0.5   -> 50% to the right
1     -> 100% to the right
-0.75 -> 75% to the left
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM3, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo output #3!')
            return

        pwmDuty = (i2cRecv[1] << 8) + i2cRecv[2]
        powerOut = (float(pwmDuty) - self.PWM_MIN_3) / (self.PWM_MAX_3 - self.PWM_MIN_3)
        return (2.0 * powerOut) - 1.0


    def GetServoPosition4(self):
        """
position = GetServoPosition4()

Gets the drive position for servo output #4
0 is central, -1 is maximum left, +1 is maximum right
e.g.
0     -> Central
0.5   -> 50% to the right
1     -> 100% to the right
-0.75 -> 75% to the left
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM4, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo output #4!')
            return

        pwmDuty = (i2cRecv[1] << 8) + i2cRecv[2]
        powerOut = (float(pwmDuty) - self.PWM_MIN_4) / (self.PWM_MAX_4 - self.PWM_MIN_4)
        return (2.0 * powerOut) - 1.0


    def SetServoPosition1(self, position):
        """
SetServoPosition1(position)

Sets the drive position for servo output #1
0 is central, -1 is maximum left, +1 is maximum right
e.g.
0     -> Central
0.5   -> 50% to the right
1     -> 100% to the right
-0.75 -> 75% to the left
        """
        powerOut = (position + 1.0) / 2.0
        pwmDuty = int((powerOut * (self.PWM_MAX_1 - self.PWM_MIN_1)) + self.PWM_MIN_1)
        pwmDutyLow = pwmDuty & 0xFF
        pwmDutyHigh = (pwmDuty >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_PWM1, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo output #1!')


    def SetServoPosition2(self, position):
        """
SetServoPosition2(position)

Sets the drive position for servo output #2
0 is central, -1 is maximum left, +1 is maximum right
e.g.
0     -> Central
0.5   -> 50% to the right
1     -> 100% to the right
-0.75 -> 75% to the left
        """
        powerOut = (position + 1.0) / 2.0
        pwmDuty = int((powerOut * (self.PWM_MAX_2 - self.PWM_MIN_2)) + self.PWM_MIN_2)
        pwmDutyLow = pwmDuty & 0xFF
        pwmDutyHigh = (pwmDuty >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_PWM2, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo output #2!')


    def SetServoPosition3(self, position):
        """
SetServoPosition3(position)

Sets the drive position for servo output #3
0 is central, -1 is maximum left, +1 is maximum right
e.g.
0     -> Central
0.5   -> 50% to the right
1     -> 100% to the right
-0.75 -> 75% to the left
        """
        powerOut = (position + 1.0) / 2.0
        pwmDuty = int((powerOut * (self.PWM_MAX_3 - self.PWM_MIN_3)) + self.PWM_MIN_3)
        pwmDutyLow = pwmDuty & 0xFF
        pwmDutyHigh = (pwmDuty >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_PWM3, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo output #3!')


    def SetServoPosition4(self, position):
        """
SetServoPosition4(position)

Sets the drive position for servo output #4
0 is central, -1 is maximum left, +1 is maximum right
e.g.
0     -> Central
0.5   -> 50% to the right
1     -> 100% to the right
-0.75 -> 75% to the left
        """
        powerOut = (position + 1.0) / 2.0
        pwmDuty = int((powerOut * (self.PWM_MAX_4 - self.PWM_MIN_4)) + self.PWM_MIN_4)
        pwmDutyLow = pwmDuty & 0xFF
        pwmDutyHigh = (pwmDuty >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_PWM4, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo output #1!')


    def GetServoMinimum1(self):
        """
pwmLevel = GetServoMinimum1()

Gets the minimum PWM level for servo output #1
This corresponds to position -1
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
2000  -> 1 ms servo burst, typical shortest burst
4000  -> 2 ms servo burst, typical longest burst
3000  -> 1.5 ms servo burst, typical centre
5000  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM_MIN_1, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo #1 minimum burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoMinimum2(self):
        """
pwmLevel = GetServoMinimum2()

Gets the minimum PWM level for servo output #2
This corresponds to position -1
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
2000  -> 1 ms servo burst, typical shortest burst
4000  -> 2 ms servo burst, typical longest burst
3000  -> 1.5 ms servo burst, typical centre
5000  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM_MIN_2, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo #2 minimum burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoMinimum3(self):
        """
pwmLevel = GetServoMinimum3()

Gets the minimum PWM level for servo output #3
This corresponds to position -1
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
2000  -> 1 ms servo burst, typical shortest burst
4000  -> 2 ms servo burst, typical longest burst
3000  -> 1.5 ms servo burst, typical centre
5000  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM_MIN_3, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo #3 minimum burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoMinimum4(self):
        """
pwmLevel = GetServoMinimum4()

Gets the minimum PWM level for servo output #4
This corresponds to position -1
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
2000  -> 1 ms servo burst, typical shortest burst
4000  -> 2 ms servo burst, typical longest burst
3000  -> 1.5 ms servo burst, typical centre
5000  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM_MIN_4, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo #4 minimum burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoMaximum1(self):
        """
pwmLevel = GetServoMaximum1()

Gets the maximum PWM level for servo output #1
This corresponds to position +1
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
2000  -> 1 ms servo burst, typical shortest burst
4000  -> 2 ms servo burst, typical longest burst
3000  -> 1.5 ms servo burst, typical centre
5000  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM_MAX_1, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo #1 maximum burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoMaximum2(self):
        """
pwmLevel = GetServoMaximum2()

Gets the maximum PWM level for servo output #2
This corresponds to position +1
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
2000  -> 1 ms servo burst, typical shortest burst
4000  -> 2 ms servo burst, typical longest burst
3000  -> 1.5 ms servo burst, typical centre
5000  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM_MAX_2, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo #2 maximum burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoMaximum3(self):
        """
pwmLevel = GetServoMaximum3()

Gets the maximum PWM level for servo output #3
This corresponds to position +1
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
2000  -> 1 ms servo burst, typical shortest burst
4000  -> 2 ms servo burst, typical longest burst
3000  -> 1.5 ms servo burst, typical centre
5000  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM_MAX_3, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo #3 maximum burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoMaximum4(self):
        """
pwmLevel = GetServoMaximum4()

Gets the maximum PWM level for servo output #4
This corresponds to position +1
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
2000  -> 1 ms servo burst, typical shortest burst
4000  -> 2 ms servo burst, typical longest burst
3000  -> 1.5 ms servo burst, typical centre
5000  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM_MAX_4, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo #4 maximum burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoStartup1(self):
        """
pwmLevel = GetServoStartup1()

Gets the startup PWM level for servo output #1
This can be anywhere in the minimum to maximum range
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
2000  -> 1 ms servo burst, typical shortest burst
4000  -> 2 ms servo burst, typical longest burst
3000  -> 1.5 ms servo burst, typical centre
5000  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM_BOOT_1, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo #1 startup burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoStartup2(self):
        """
pwmLevel = GetServoStartup2()

Gets the startup PWM level for servo output #2
This can be anywhere in the minimum to maximum range
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
2000  -> 1 ms servo burst, typical shortest burst
4000  -> 2 ms servo burst, typical longest burst
3000  -> 1.5 ms servo burst, typical centre
5000  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM_BOOT_2, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo #2 startup burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoStartup3(self):
        """
pwmLevel = GetServoStartup3()

Gets the startup PWM level for servo output #3
This can be anywhere in the minimum to maximum range
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
2000  -> 1 ms servo burst, typical shortest burst
4000  -> 2 ms servo burst, typical longest burst
3000  -> 1.5 ms servo burst, typical centre
5000  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM_BOOT_3, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo #3 startup burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoStartup4(self):
        """
pwmLevel = GetServoStartup4()

Gets the startup PWM level for servo output #4
This can be anywhere in the minimum to maximum range
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
2000  -> 1 ms servo burst, typical shortest burst
4000  -> 2 ms servo burst, typical longest burst
3000  -> 1.5 ms servo burst, typical centre, 
5000  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM_BOOT_4, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo #4 startup burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def CalibrateServoPosition1(self, pwmLevel):
        """
CalibrateServoPosition1(pwmLevel)

Sets the raw PWM level for servo output #1
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

Setting values outside the range of the servo for extended periods of time can damage the servo
NO LIMIT CHECKING IS PERFORMED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition1 / GetServoPosition1

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_CALIBRATE_PWM1, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending calibration servo output #1!')


    def CalibrateServoPosition2(self, pwmLevel):
        """
CalibrateServoPosition2(pwmLevel)

Sets the raw PWM level for servo output #2
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

Setting values outside the range of the servo for extended periods of time can damage the servo
NO LIMIT CHECKING IS PERFORMED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition2 / GetServoPosition2

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_CALIBRATE_PWM2, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending calibration servo output #2!')


    def CalibrateServoPosition3(self, pwmLevel):
        """
CalibrateServoPosition3(pwmLevel)

Sets the raw PWM level for servo output #3
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

Setting values outside the range of the servo for extended periods of time can damage the servo
NO LIMIT CHECKING IS PERFORMED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition3 / GetServoPosition3

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_CALIBRATE_PWM3, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending calibration servo output #3!')


    def CalibrateServoPosition4(self, pwmLevel):
        """
CalibrateServoPosition4(pwmLevel)

Sets the raw PWM level for servo output #4
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

Setting values outside the range of the servo for extended periods of time can damage the servo
NO LIMIT CHECKING IS PERFORMED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition4 / GetServoPosition4

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_CALIBRATE_PWM4, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending calibration servo output #4!')


    def GetRawServoPosition1(self):
        """
pwmLevel = GetRawServoPosition1()

Gets the raw PWM level for servo output #1
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

This value requires interpreting into an actual servo position, this is already done by GetServoPosition1
We recommend using the tuning GUI for setting the servo limits for SetServoPosition1 / GetServoPosition1

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM1, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading raw servo output #1!')
            return

        pwmDuty = (i2cRecv[1] << 8) + i2cRecv[2]
        return pwmDuty


    def GetRawServoPosition2(self):
        """
pwmLevel = GetRawServoPosition2()

Gets the raw PWM level for servo output #2
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

This value requires interpreting into an actual servo position, this is already done by GetServoPosition2
We recommend using the tuning GUI for setting the servo limits for SetServoPosition2 / GetServoPosition2

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM2, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading raw servo output #2!')
            return

        pwmDuty = (i2cRecv[1] << 8) + i2cRecv[2]
        return pwmDuty


    def GetRawServoPosition3(self):
        """
pwmLevel = GetRawServoPosition3()

Gets the raw PWM level for servo output #3
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

This value requires interpreting into an actual servo position, this is already done by GetServoPosition3
We recommend using the tuning GUI for setting the servo limits for SetServoPosition3 / GetServoPosition3

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM3, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading raw servo output #3!')
            return

        pwmDuty = (i2cRecv[1] << 8) + i2cRecv[2]
        return pwmDuty


    def GetRawServoPosition4(self):
        """
pwmLevel = GetRawServoPosition4()

Gets the raw PWM level for servo output #4
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

This value requires interpreting into an actual servo position, this is already done by GetServoPosition4
We recommend using the tuning GUI for setting the servo limits for SetServoPosition4 / GetServoPosition4

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_PWM4, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading raw servo output #4!')
            return

        pwmDuty = (i2cRecv[1] << 8) + i2cRecv[2]
        return pwmDuty


    def SetServoMinimum1(self, pwmLevel):
        """
SetServoMinimum1(pwmLevel)

Sets the minimum PWM level for servo output #1
This corresponds to position -1
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

Setting values outside the range of the servo for extended periods of time can damage the servo
LIMIT CHECKING IS ALTERED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition1 / GetServoPosition1

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_PWM_MIN_1, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo minimum limit #1!')
        time.sleep(DELAY_AFTER_EEPROM)
        self.PWM_MIN_1 = self.GetServoMinimum1()


    def SetServoMinimum2(self, pwmLevel):
        """
SetServoMinimum2(pwmLevel)

Sets the minimum PWM level for servo output #2
This corresponds to position -1
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

Setting values outside the range of the servo for extended periods of time can damage the servo
LIMIT CHECKING IS ALTERED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition2 / GetServoPosition2

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_PWM_MIN_2, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo minimum limit #2!')
        time.sleep(DELAY_AFTER_EEPROM)
        self.PWM_MIN_2 = self.GetServoMinimum2()


    def SetServoMinimum3(self, pwmLevel):
        """
SetServoMinimum3(pwmLevel)

Sets the minimum PWM level for servo output #3
This corresponds to position -1
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

Setting values outside the range of the servo for extended periods of time can damage the servo
LIMIT CHECKING IS ALTERED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition3 / GetServoPosition3

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_PWM_MIN_3, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo minimum limit #3!')
        time.sleep(DELAY_AFTER_EEPROM)
        self.PWM_MIN_3 = self.GetServoMinimum3()


    def SetServoMinimum4(self, pwmLevel):
        """
SetServoMinimum4(pwmLevel)

Sets the minimum PWM level for servo output #4
This corresponds to position -1
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

Setting values outside the range of the servo for extended periods of time can damage the servo
LIMIT CHECKING IS ALTERED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition4 / GetServoPosition4

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_PWM_MIN_4, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo minimum limit #4!')
        time.sleep(DELAY_AFTER_EEPROM)
        self.PWM_MIN_4 = self.GetServoMinimum4()


    def SetServoMaximum1(self, pwmLevel):
        """
SetServoMaximum1(pwmLevel)

Sets the maximum PWM level for servo output #1
This corresponds to position +1
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

Setting values outside the range of the servo for extended periods of time can damage the servo
LIMIT CHECKING IS ALTERED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition1 / GetServoPosition1

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_PWM_MAX_1, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo maximum limit #1!')
        time.sleep(DELAY_AFTER_EEPROM)
        self.PWM_MAX_1 = self.GetServoMaximum1()


    def SetServoMaximum2(self, pwmLevel):
        """
SetServoMaximum2(pwmLevel)

Sets the maximum PWM level for servo output #2
This corresponds to position +1
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

Setting values outside the range of the servo for extended periods of time can damage the servo
LIMIT CHECKING IS ALTERED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition2 / GetServoPosition2

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_PWM_MAX_2, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo maximum limit #2!')
        time.sleep(DELAY_AFTER_EEPROM)
        self.PWM_MAX_2 = self.GetServoMaximum2()


    def SetServoMaximum3(self, pwmLevel):
        """
SetServoMaximum3(pwmLevel)

Sets the maximum PWM level for servo output #3
This corresponds to position +1
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

Setting values outside the range of the servo for extended periods of time can damage the servo
LIMIT CHECKING IS ALTERED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition3 / GetServoPosition3

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_PWM_MAX_3, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo maximum limit #3!')
        time.sleep(DELAY_AFTER_EEPROM)
        self.PWM_MAX_3 = self.GetServoMaximum3()


    def SetServoMaximum4(self, pwmLevel):
        """
SetServoMaximum4(pwmLevel)

Sets the maximum PWM level for servo output #4
This corresponds to position +1
This value can be set anywhere from 0 for a 0% duty cycle to 65535 for a 100% duty cycle

Setting values outside the range of the servo for extended periods of time can damage the servo
LIMIT CHECKING IS ALTERED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition4 / GetServoPosition4

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_PWM_MAX_4, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo maximum limit #4!')
        time.sleep(DELAY_AFTER_EEPROM)
        self.PWM_MAX_4 = self.GetServoMaximum4()


    def SetServoStartup1(self, pwmLevel):
        """
SetServoStartup1(pwmLevel)

Sets the startup PWM level for servo output #1
This can be anywhere in the minimum to maximum range

We recommend using the tuning GUI for setting the servo limits for SetServoPosition1 / GetServoPosition1
This value is checked against the current servo limits before setting

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF
        inRange = True

        if self.PWM_MIN_1 < self.PWM_MAX_1:
            # Normal direction
            if pwmLevel < self.PWM_MIN_1:
                inRange = False
            elif pwmLevel > self.PWM_MAX_1:
                inRange = False
        else:
            # Inverted direction
            if pwmLevel > self.PWM_MIN_1:
                inRange = False
            elif pwmLevel < self.PWM_MAX_1:
                inRange = False
        if pwmLevel == PWM_UNSET:
            # Force to unset behaviour (central)
            inRange = True

        if not inRange:
            print('Servo #1 startup position %d is outside the limits of %d to %d' % (pwmLevel, self.PWM_MIN_1, self.PWM_MAX_1))
            return

        try:
            self.RawWrite(COMMAND_SET_PWM_BOOT_1, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo startup position #1!')
        time.sleep(DELAY_AFTER_EEPROM)


    def SetServoStartup2(self, pwmLevel):
        """
SetServoStartup2(pwmLevel)

Sets the startup PWM level for servo output #2
This can be anywhere in the minimum to maximum range

We recommend using the tuning GUI for setting the servo limits for SetServoPosition2 / GetServoPosition2
This value is checked against the current servo limits before setting

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF
        inRange = True

        if self.PWM_MIN_2 < self.PWM_MAX_2:
            # Normal direction
            if pwmLevel < self.PWM_MIN_2:
                inRange = False
            elif pwmLevel > self.PWM_MAX_2:
                inRange = False
        else:
            # Inverted direction
            if pwmLevel > self.PWM_MIN_2:
                inRange = False
            elif pwmLevel < self.PWM_MAX_2:
                inRange = False
        if pwmLevel == PWM_UNSET:
            # Force to unset behaviour (central)
            inRange = True

        if not inRange:
            print('Servo #2 startup position %d is outside the limits of %d to %d' % (pwmLevel, self.PWM_MIN_2, self.PWM_MAX_2))
            return

        try:
            self.RawWrite(COMMAND_SET_PWM_BOOT_2, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo startup position #2!')
        time.sleep(DELAY_AFTER_EEPROM)


    def SetServoStartup3(self, pwmLevel):
        """
SetServoStartup3(pwmLevel)

Sets the startup PWM level for servo output #3
This can be anywhere in the minimum to maximum range

We recommend using the tuning GUI for setting the servo limits for SetServoPosition3 / GetServoPosition3
This value is checked against the current servo limits before setting

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF
        inRange = True

        if self.PWM_MIN_3 < self.PWM_MAX_3:
            # Normal direction
            if pwmLevel < self.PWM_MIN_3:
                inRange = False
            elif pwmLevel > self.PWM_MAX_3:
                inRange = False
        else:
            # Inverted direction
            if pwmLevel > self.PWM_MIN_3:
                inRange = False
            elif pwmLevel < self.PWM_MAX_3:
                inRange = False
        if pwmLevel == PWM_UNSET:
            # Force to unset behaviour (central)
            inRange = True

        if not inRange:
            print('Servo #3 startup position %d is outside the limits of %d to %d' % (pwmLevel, self.PWM_MIN_3, self.PWM_MAX_3))
            return

        try:
            self.RawWrite(COMMAND_SET_PWM_BOOT_3, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo startup position #3!')
        time.sleep(DELAY_AFTER_EEPROM)


    def SetServoStartup4(self, pwmLevel):
        """
SetServoStartup4(pwmLevel)

Sets the startup PWM level for servo output #4
This can be anywhere in the minimum to maximum range

We recommend using the tuning GUI for setting the servo limits for SetServoPosition4 / GetServoPosition4
This value is checked against the current servo limits before setting

The value is an integer where 2000 represents a 1ms servo burst, approximately 3% duty cycle
e.g.
2000  -> 1 ms servo burst, typical shortest burst, ~3% duty cycle
4000  -> 2 ms servo burst, typical longest burst, ~ 6.1% duty cycle
3000  -> 1.5 ms servo burst, typical centre, ~4.6% duty cycle
5000  -> 2.5 ms servo burst, higher than typical longest burst, ~ 7.6% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF
        inRange = True

        if self.PWM_MIN_4 < self.PWM_MAX_4:
            # Normal direction
            if pwmLevel < self.PWM_MIN_4:
                inRange = False
            elif pwmLevel > self.PWM_MAX_4:
                inRange = False
        else:
            # Inverted direction
            if pwmLevel > self.PWM_MIN_4:
                inRange = False
            elif pwmLevel < self.PWM_MAX_4:
                inRange = False
        if pwmLevel == PWM_UNSET:
            # Force to unset behaviour (central)
            inRange = True

        if not inRange:
            print('Servo #4 startup position %d is outside the limits of %d to %d' % (pwmLevel, self.PWM_MIN_4, self.PWM_MAX_4))
            return

        try:
            self.RawWrite(COMMAND_SET_PWM_BOOT_4, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo startup position #4!')
        time.sleep(DELAY_AFTER_EEPROM)


    def Help(self):
        """
Help()

Displays the names and descriptions of the various functions and settings provided
        """
        funcList = [UltraBorg.__dict__.get(a) for a in dir(UltraBorg) if isinstance(UltraBorg.__dict__.get(a), types.FunctionType)]
        funcListSorted = sorted(funcList, key = lambda x: x.func_code.co_firstlineno)

        print(self.__doc__)
        print
        for func in funcListSorted:
            print('=== %s === %s' % (func.func_name, func.func_doc))

