*******************************************
A Python-based Robot Operating System (ROS)
*******************************************

This provides a *Robot Operating System* (ROS) for a Raspberry Pi based robot
written in Python 3, whose prototype hardware implementation is the **KR01** robot.
Main communication between sensors and motor controller is performed over I²C,
using lever switch bumpers, Sharp/Pololu infrared distance sensors as well as a
variety of Pimoroni sensors from the Breakout Garden series.

.. image:: https://service.robots.org.nz/wiki/attach/KR01/KR01-0533-1280x584.jpg
   :width: 1280px
   :align: center
   :height: 584px
   :alt: The KR01 Robot

The KR01 robot uses the PiBorg ThunderBorg motor controller and an UltraBorg
ultrasonic sensor and servo controller board.

More information can be found on the New Zealand Personal Robotic Group (NZPRG) Blog at:

* `The KR01 Robot Project <https://robots.org.nz/2019/12/08/kr01/>`
* `Facilius Est Multa Facere Quam Diu <https://robots.org.nz/2020/04/24/facilius-est/>`

and the NZPRG wiki at:

* `KR01 Robot <https://service.robots.org.nz/wiki/Wiki.jsp?page=KR01>`


This project is part of the *New Zealand Personal Robotics (NZPRG)* "Robot
Operating System", not to be confused with other "ROS" projects. It is intended
that in the future this project will be migrated to a modular, Python distribution
via PyPy so that the components can be installed from the command line. The code
is currently still not stable enough to warrant that level of convenience.


Features
********

* `Behaviour-Based System (BBS) <https://en.wikipedia.org/wiki/Behavior-based_robotics>`
* `Subsumption Architecture <https://en.wikipedia.org/wiki/Subsumption_architecture>` [#f1]_
* Auto-configures by scanning I²C bus for available devices on startup
* Configuration via YAML file
* Motor control via a `PID controller <https://en.wikipedia.org/wiki/PID_controller>` with odometry support using encoders
* complex composite sensors include mini-LIDAR, scanning ultrasonic distance sensor
* supports analog and digital IR bumper sensors
* output via 11x7 white matrix LED and 5x5 RGB matrix LED displays
* supports Pimoroni Breakout Garden, Adafruit and other I²C sensors, and can be extended for others
* supports PiBorg ThunderBorg motor controller, UltraBorg servo and ultrasonic controller board
* written in Python 3

.. [#f1] Uses finite state machines, an asynchronous message queue, an arbitrator and controller for task prioritisation.


Status
******

This project should currently be considered a "**Technology Preview**".

The files in the repository function largely as advertised but the overall state
of the ROS is not yet complete — it's still very much a work-in-progress and
there are still some pieces missing that are not quite "ready for prime time."
Demonstrations and included tests (including the pytest suite) either pass
entirely or are close to passing.

The project is being exposed publicly so that those interested can follow its
progress. At such a time when the ROS is generally useable this status section
will be updated accordingly.


Installation
************

The ROS requires installation of a number of support libraries. In order to
begin you'll need Python3 (at least 3.8) and pip3, as well as the pigpio library.

Note that the current setup.py script is not yet functional (this is a work in
progress), and you may instead use the bespoke ros_setup.py to install the
dependency libraries. It may or not function properly on your system, in which
case you may need to manually install the libraries (you'll generally see an
error message indicating a missing library).


Support & Liability
*******************

This project comes with no promise of support or liability. Use at your own risk.


Further Information
*******************

For more information check out the `NZPRG Blog <https://robots.org.nz/>` and
`NZPRG Wiki <https://service.robots.org.nz/wiki/>`.

Please note that the documentation in the code will likely be more current
than this README file, so please consult it for the "canonical" information.


Execution
*********

To force the Raspberry Pi to prioritise execution of the python operating
system, use the 'chrt' command, e.g.::

    % chrt -f 5 python3 ./fusion_test.py



Copyright & License
*******************

All contents (including software, documentation and images) Copyright 2020-2021
by Murray Altheim. All rights reserved.

This file is part of the Robot Operating System project, released under the MIT License.

Software and documentation are distributed under the MIT License, see LICENSE
file included with project.

