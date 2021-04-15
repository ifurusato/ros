#!/usr/bin/env python3

from setuptools import setup

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='kros-core',
    version='0.7.0',  # Use bumpversion!
    description="Robot Operating System - Core, K-Series Robots",
    long_description=long_description,
    author='Ichiro Furusato',
    author_email='ichiro.furusato@gmail.com',
    packages=['kros-core'],
    include_package_data=True,
    install_requires=['numpy', 'pytest', 'pyyaml', 'colorama', 'gpiozero', 'board', 'readchar', 'pyquaternion'],
    zip_safe=False,
    url='https://github.com/ifurusato/ros',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Other OS',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Topic :: Robot Framework',
        'Topic :: Robot Framework :: Library',
        'Topic :: Robot Framework :: Tool',
    ],
)
# future requries:
#   'rpi.gpio', \
#   'adafruit-extended-bus', \
#   'pymessagebus==1.*', \
#   'ht0740', \
#   'pimoroni-ioexpander', \
#   'adafruit-circuitpython-bno08x', \
#   'matrix11x7', \
#   'rgbmatrix5x5', \
