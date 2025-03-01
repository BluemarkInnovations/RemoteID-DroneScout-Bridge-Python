#!/usr/bin/python3
# (c) Bluemark Innovations BV
# MIT license
# settings file

import random

#ther serial interface where the DroneScout Bridge outputs data
interface = "/dev/ttyACM0" 
baudrate = 115200 # for now only 115200 is supported

# save the detected Remote ID signals to a CSV file in the log_path folder
# uncomment to enable logging
# only basic information like SN, drone location/altitude and pilot location/alitude
#log_path = './logs'
