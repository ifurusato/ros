# ROS: Getting Started


## Requirements/Prerequisites

         1         2         3         4         5         6         7         8
12345678901234567890123456789012345678901234567890123456789012345678901234567890

This Robot Operating System (ROS) can be installed on any linux-compatible OS, 
including the native Raspberry Pi OS (the operating system previously known as 
"Raspbian").

It is designed to run on Python3 and therefore requires both Python3 and the 
Python3 library installation tool 'pip3'. In order to access the github 
repository and download the ROS software, 'git' is required. These are all 
installed by default on the Raspberry Pi OS.

To function a few other Python3 software libraries need to be either checked 
and/or installed. You will need to prefix pip3 commands with "sudo" if you want
to install your software system-wide.

Before making any installations, it's a good idea to upgrade the pip3 installer
itself:
```
 $ sudo -H pip3 install --upgrade pip
```

To install Python's test library, pytest (which is used in a number of files):
```
 $ sudo pip3 install pytest
```

To install Python YAML:
```
 $ sudo pip3 install pyyaml
```

Some of the sensor libraries used require Adafruit's CircuitPython, which is
supplied by the Blinka library:
```
 $ sudo pip3 install adafruit-blinka
```

The pigpio library is installed on Raspbian by default. If not already 
installed, you can install it via:
```
 $ sudo apt install pigpio
```

To automate running the pigpio daemon at boot time, run:
```
 $ sudo systemctl enable pigpiod
```

To run the daemon once using systemctl, run:
```
 $ sudo systemctl start pigpiod
```

You can see if it's running ("active") via:
```
 $ sudo service pigpiod status
● pigpiod.service - Daemon required to control GPIO pins via pigpio
   Loaded: loaded (/lib/systemd/system/pigpiod.service; enabled; vendor preset:
           enabled)
   Active: active (running) since Sun 2020-05-17 10:30:21 NZST; 11s ago
  Process: 995 ExecStart=/usr/bin/pigpiod -l (code=exited, status=0/SUCCESS)
 Main PID: 996 (pigpiod)
    Tasks: 4 (limit: 1012)
   Memory: 712.0K
   CGroup: /system.slice/pigpiod.service
           └─996 /usr/bin/pigpiod -l

May 17 10:30:21 pi systemd[1]: Starting Daemon required to control GPIO pins via pigpio...
May 17 10:30:21 pi systemd[1]: Started Daemon required to control GPIO pins via pigpio.
```

## Additional hardware-support libraries

To support the Pimoroni Breakout Garden 5x5 RGB Matrix Breakout, run:
```
 $ sudo pip3 install rgbmatrix5x5
```

If you're using any of the Nuvoton MS51 based Pimoroni sensors like the IO 
Expander, follow the directions at: https://github.com/pimoroni/ioe-python
which are basically to go to a suitable base directory and type:
```
 $ git clone https://github.com/pimoroni/ioe-python
 $ cd ioe-python
 $ sudo ./install.sh
```

The NXP 9 DoF IMU, which includes both a FXOS8700 3 axis accelerometer and 
magnetometer and a FXAS21002 gyroscope, requires:
```
 $ sudo pip3 install nxp-imu adafruit-circuitpython-fxos8700 adafruit-circuitpython-fxas21002c
 $ sudo pip3 install pyquaternion
```

## ROS Installation 

Navigate to a directory where you'd like to install ROS and type:

```
 ►  git clone https://github.com/ifurusato/ros.git
```

This will create a new directory called 'ros' and download ("clone") the ROS 
code from the github.com website into that directory.


