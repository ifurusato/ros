# ROS: Getting Started


## Requirements/Prerequisites

This Robot Operating System (ROS) can be installed on any linux-compatible OS, including Raspbian, the native Raspberry Pi OS.

It was designed to run on Python3 and therefore requires both Python3 and the Python3 library installation tool 'pip3'. 
In order to access the github repository and download the ROS software, 'git' is required. These are all installed by default on Raspbian.

To function a few other Python3 software libraries need to be either checked and/or installed.

To install Python YAML:
```
 $ pip3 install pyyaml
```

The pigpio library is installed on Raspbian by default. If not already installed, you can install it via:
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
   Loaded: loaded (/lib/systemd/system/pigpiod.service; enabled; vendor preset: enabled)
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



## ROS Installation 

Navigate to a directory where you'd like to install ROS and type:

```
 ►  git clone https://github.com/ifurusato/ros.git
```

This will create a new directory called 'ros' and download ("clone") the ROS code from the github.com website into that directory.


