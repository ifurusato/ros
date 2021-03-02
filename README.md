# A Python-based Robot Operating System (ROS)

This provides a _Robot Operating System_ (ROS) for a Raspberry Pi based robot written in Python 3, whose prototype hardware implementation is the **KR01** robot.
Main communication between sensors and motor controller is performed over I²C, using lever switch bumpers, Sharp/Pololu infrared distance sensors as well as a
variety of Pimoroni sensors from the Breakout Garden series.


![The KRO1 Robot](https://service.robots.org.nz/wiki/attach/KR01/KR01-0533-1280x584.jpg)


The KR01 robot uses the PiBorg ThunderBorg motor controller and UltraBorg ultrasonic sensor and servo controller board.

More information can be found on the New Zealand Personal Robotic Group (NZPRG) Blog at:

* [The KR01 Robot Project](https://robots.org.nz/2019/12/08/kr01/)
* [Facilius Est Multa Facere Quam Diu](https://robots.org.nz/2020/04/24/facilius-est/)

and the NZPRG wiki at:

* [KR01 Robot](https://service.robots.org.nz/wiki/Wiki.jsp?page=KR01)


## Features

* [Behaviour-Based System (BBS)](https://en.wikipedia.org/wiki/Behavior-based_robotics)
* [Subsumption Architecture](https://en.wikipedia.org/wiki/Subsumption_architecture) (uses finite state machines, message queue, arbitrator and controller for task prioritisation)
* Auto-configures by scanning I²C bus for available devices on startup
* Configuration via YAML file
* Motor control via [PID controller](https://en.wikipedia.org/wiki/PID_controller) with odometry support using encoders
* complex composite sensors include mini-LIDAR, scanning ultrasonic distance sensor and PIR-based cat scanner
* supports analog and digital IR bumper sensors
* output via 11x7 white matrix LED and 5x5 RGB matrix LED displays
* supports Pimoroni Breakout Garden, Adafruit and other I²C sensors, and can be extended for others
* supports PiBorg ThunderBorg motor controller, UltraBorg servo and ultrasonic controller board
* written in Python 3


## Status

This project should currently be considered a "**Technology Preview**".

The files in the repository function largely as advertised but the overall state of the ROS is not yet complete — it's still very much a work-in-progress and there are still some pieces missing that are not quite "ready for prime time." Demonstrations and included tests (including the pytest suite) either pass entirely or are close to passing.

The project is being exposed publicly so that those interested can follow its progress. At such a time when the ROS is generally useable this status section will be updated accordingly.


## Installation

The ROS requires installation of a number of support libraries. In order to begin you'll need Python3 and pip3, as well as the pigpio library. The import_report.py script will report on which Python libraries used by ROS you have currently installed and which you don't; it doesn't itself import anything or alter your environment, unless calling one of the files within the ROS directory tree installs software (none do).

You'll first need to install the Python 3.7 dev library:

  % sudo apt install libpython3.7-dev


## Support & Liability

This project comes with no promise of support or liability. Use at your own risk.


## Further Information

This project is part of the _New Zealand Personal Robotics (NZPRG)_ "Robot Operating System", not to be confused with other "ROS" projects. For more information check out the [NZPRG Blog](https://robots.org.nz/) and [NZPRG Wiki](https://service.robots.org.nz/wiki/).

Please note that the documentation in the code will likely be more current than this README file, so please consult it for the "canonical" information.


## Execution

To force the Raspberry Pi to prioritise execution of the python operating system, use the 'chrt' command, e.g.:
'''
  % chrt -f 5 python3 ./fusion_test.py
'''


## Copyright & License

All contents (including software, documentation and images) Copyright 2020-2021 by Murray Altheim. All rights reserved.
This file is part of the Robot Operating System project, released under the MIT License. 

Software and documentation are distributed under the MIT License, see LICENSE file included with project.

