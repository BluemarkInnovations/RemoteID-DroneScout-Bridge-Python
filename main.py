#!/usr/bin/python3
# (c) Bluemark Innovations BV
# MIT license

import time
from pymavlink import mavutil
from bitstruct import *

import config # config.py with settings

from modules import odid # opendroneID functions
from modules import adsb # ADSB vehicle functions
from modules import log_file # log opendroneID data to a CSV file

#setup MAVLink serial link and wait until a heartbeat is received
master = mavutil.mavlink_connection(config.interface, config.baudrate)
master.wait_heartbeat()



while True:
    try:
        msg = master.recv_match()
    except:
        pass
    if not msg:
        time.sleep(0.1)
        continue
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)

    if msg.get_type() == 'HEARTBEAT':
        #print("%s" % msg.to_dict())
        print("%s MAVLink heartbeat received" % current_time)

    if msg.get_type() == 'ADSB_VEHICLE':
        print("\n%s MAVLink ADS-B vehicle message received" % current_time)
        #print("%s" % msg.to_dict())
        adsb.print_payload(msg)

    if msg.get_type() == 'OPEN_DRONE_ID_MESSAGE_PACK':
        print("\n%s MAVLink OpenDroneID Message Pack message received" % current_time)
        #print("\n%s" % msg.to_dict()) #print raw packet contents
        odid.print_message_pack(msg.messages, msg.msg_pack_size)
        if hasattr(config, 'log_path'):
            if 'filename' not in globals():
                global filename
                filename = log_file.open_csv(config.log_path)
            log_file.write_csv(msg.messages, msg.msg_pack_size,filename)
