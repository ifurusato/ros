# A Python-based Robot Operating System (ROS)

This provides a _Robot Operating System_ (ROS) for a Raspberry Pi based robot
written in Python 3, whose prototype hardware implementation is the KR01 robot.
Main communication between sensors and motor controller is performed over I²C, 
using lever switch bumpers, Sharp/Pololu infrared distance sensors as well as 
a variety of Pimoroni sensors from the Breakout Garden series. 

![The KRO1 Robot](https://service.robots.org.nz/wiki/attach/KR01/KR01-0533-800x360.jpg)

The KR01 robot uses the PiBorg ThunderBorg motor controller and UltraBorg 
ultrasonic sensor and servo controller board. 

More information can be found on the New Zealand Personal Robotic Group (NZPRG) Blog at:

* [The KR01 Robot Project](https://robots.org.nz/2019/12/08/kr01/)
* [Facilius Est Multa Facere Quam Diu](https://robots.org.nz/2020/04/24/facilius-est/)
 
and the NZPRG wiki at:

* [KR01 Robot](https://service.robots.org.nz/wiki/Wiki.jsp?page=KR01)


## Status

Currently the files have been copied into the repository are from the initial local 
project.  These files function as advertised but the overall state of the ROS is not 
yet complete - there are still some pieces missing that are not quite "ready for prime 
time."

The project is being exposed publicly so that those interested can follow its progress.
At such a time when the ROS is generally useable this status section will be updated
accordingly.


## Installation

The ROS requires installation of a number of support libraries. In order to begin you'll
need Python3 and pip3, as well as the pigpio library.


## Support & Liability

This project comes with no promise of support or liability. Use at your own risk.


## Further Information

This project is part of the _New Zealand Personal Robotics (NZPRG)_ "Robot Operating
System", not to be confused with other "ROS" projects. For more information check out the
[NZPRG Blog](https://robots.org.nz/) and [NZPRG Wiki](https://service.robots.org.nz/wiki/).

Please note that the documentation in the code will likely be more current than this README file, so please consult it for the "canonical" information.


## Copyright & License

This software is Copyright 2020 by Murray Altheim, All Rights Reserved.

Distributed under the MIT License, see LICENSE file included with project.

