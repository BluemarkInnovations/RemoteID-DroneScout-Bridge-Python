#!/usr/bin/python3
# (c) Bluemark Innovations BV
# MIT license

import os
os.environ['MAVLINK20'] = '1'   # use the MAVLink 2 dialects; must be before importing mavutil

import time
from pymavlink import mavutil
from bitstruct import *
import threading

from modules import odid # opendroneID functions
from modules import adsb # ADSB vehicle functions
from modules import log_file # log opendroneID data to a CSV file
from modules import sbs # for SBS export
from modules import rid # extra message definitions (generated from rid.xml without includes)

def extend_dialect(ext):
    """Add messages and enums from a small generated dialect to the active pymavlink dialect."""
    base = mavutil.mavlink
    for msgid, cls in ext.mavlink_map.items():
        base.mavlink_map[msgid] = cls
        setattr(base, 'MAVLINK_MSG_ID_' + cls.msgname, msgid)
    for enum_name, entries in ext.enums.items():
        base.enums[enum_name] = entries
        for value, entry in entries.items():
            setattr(base, entry.name, value)

extend_dialect(rid)

import config # config.py with settings

if hasattr(config, 'sbs_server_ip_address'): # only enable SBS export if relevant vars have been defined
	if hasattr(config, 'sbs_server_port'):
		print("SBS export thread started")
		sbs_thread = threading.Thread(target=sbs.connect, args=(1,))
		sbs_thread.daemon = True
		sbs_thread.start()

#setup MAVLink serial link and wait until a heartbeat is received
master = mavutil.mavlink_connection(config.interface, config.baudrate)
master.wait_heartbeat()

# if this var is not defined, make it true
if not hasattr(config, 'print_messages'):
    config.print_messages = True

last_rx_info = {}           # id_or_mac -> (receive time, RX information message)
RX_INFO_MAX_AGE = 2.0       # seconds; older RX info is not attached to a pack

while True:
    try:
        msg = master.recv_match()
    except:
        msg = None # don't process the previous message again
    if not msg:
        time.sleep(0.1)
        continue
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)

    if msg.get_type() == 'HEARTBEAT':

        if config.print_messages == True:
            print("%s MAVLink heartbeat received" % current_time)
            #print("%s" % msg.to_dict())

    if msg.get_type() == 'ADSB_VEHICLE':
        if config.print_messages == True:
            print("\n%s MAVLink ADS-B vehicle message received" % current_time)
            #print("%s" % msg.to_dict())
            adsb.print_payload(msg)

    if msg.get_type() == 'OPEN_DRONE_ID_RADIO_RX_INFORMATION':
        last_rx_info[bytes(msg.id_or_mac)] = (time.time(), msg)

        if config.print_messages == True:
            print("\n%s MAVLink OpenDroneID Radio RX Information message received" % current_time)
            #print("\n%s" % msg.to_dict()) #print raw packet contents
            odid.print_rx_information(msg)

    if msg.get_type() == 'OPEN_DRONE_ID_MESSAGE_PACK':
        if config.print_messages == True:
            print("\n%s MAVLink OpenDroneID Message Pack message received" % current_time)
            #print("\n%s" % msg.to_dict()) #print raw packet contents
            odid.print_message_pack(msg.messages, msg.msg_pack_size)

        # find matching RX information for this transmitter, if recent enough
        rx = None
        entry = last_rx_info.get(bytes(msg.id_or_mac))
        if entry is not None and time.time() - entry[0] < RX_INFO_MAX_AGE and entry[1].msg_id == msg.get_msgId():
            rx = entry[1]

        if hasattr(config, 'log_path'):
            if 'filename' not in globals():
                global filename
                filename = log_file.open_csv(config.log_path)
            log_file.write_csv(msg.messages, msg.msg_pack_size, filename, rx)

        if hasattr(config, 'sbs_server_ip_address'):
            try:
                sbs.export(msg.messages, msg.msg_pack_size)
            except:
                pass
