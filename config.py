#!/usr/bin/python3
# (c) Bluemark Innovations BV
# MIT license
# settings file

# the serial interface where the DroneScout Bridge outputs data
# /dev/ttyUSB0 is the UART interface via a USB-UART adapter, /dev/ttyACM0 the USB port of the bridge
interface = "/dev/ttyUSB0"
baudrate = 115200  # only 115200 is supported on USB, UART allows higher and lower baud rates

# set to False to disable printing messages on the console
print_messages = True

# save the detected Remote ID signals to a CSV file in the log_path folder
# uncomment to enable logging
# only basic information like SN, drone location/altitude and pilot location/altitude
#log_path = './logs'

# export data to Virtual Radar Server or FlightAirMap that support sources with SBS BaseStation output
#sbs_server_ip_address = "0.0.0.0"  # listen on all network interfaces
#sbs_server_port = 30003  # port
