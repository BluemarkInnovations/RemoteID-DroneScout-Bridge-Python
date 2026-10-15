#!/usr/bin/python3
# (c) Bluemark Innovations BV
# MIT license

import os
os.environ['MAVLINK20'] = '1'   # use the MAVLink 2 dialects; must be before importing mavutil

import time
from pymavlink import mavutil
import threading

from modules import odid # opendroneID functions
from modules import adsb # ADSB vehicle functions
from modules import log_file # log opendroneID data to a CSV file
from modules import error_log # log packets that could not be decoded to a CSV file
from modules import sbs # for SBS export
from modules import rid # extra message definitions (generated from rid.xml without includes)

def extend_dialect(ext):
    """Add messages and enums from a small generated dialect to the active pymavlink dialect."""
    base = mavutil.mavlink
    for msgid, cls in ext.mavlink_map.items():
        # don't silently replace a different message that uses the same ID
        if msgid in base.mavlink_map and base.mavlink_map[msgid].msgname != cls.msgname:
            raise RuntimeError("MAVLink message ID %u (%s) is already used by %s"
                               % (msgid, cls.msgname, base.mavlink_map[msgid].msgname))
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
        sbs_thread = threading.Thread(target=sbs.connect)
        sbs_thread.daemon = True
        sbs_thread.start()

#setup MAVLink serial link and wait until a heartbeat is received
master = mavutil.mavlink_connection(config.interface, config.baudrate)
master.wait_heartbeat()

# if this var is not defined, make it true
if not hasattr(config, 'print_messages'):
    config.print_messages = True

last_rx_info = {}           # id_or_mac -> (receive time, RX information message)
pending_packs = {}          # id_or_mac -> (receive time, message pack) waiting for RX information
RX_INFO_MAX_AGE = 2.0       # seconds; older RX info is not attached to a pack
filename = None             # CSV log file, created when the first pack is logged
error_filename = None       # CSV log file for decode errors, created when the first error is logged
bad_bytes = bytearray()     # consecutive bytes that are not part of a MAVLink packet
mav_loss = 0                # packets lost so far according to the MAVLink sequence numbers

def rx_matches(rx, pack):
    # RX information refers to the MAVLink message it belongs to by message ID
    return rx.msg_id == pack.get_msgId()

def log_pack(pack, rx):
    # write a message pack, with its RX information if available, to the CSV file
    global filename
    if not hasattr(config, 'log_path'):
        return
    if filename is None:
        filename = log_file.open_csv(config.log_path)
    log_file.write_csv(pack.messages, pack.msg_pack_size, filename, rx)

def log_decode_error(msg_type, reason, data=b''):
    # report a packet that could not be decoded on the console and in the decode error CSV file
    global error_filename
    if config.print_messages == True:
        print("\n%s Decode error in %s: %s (%u bytes)" % (time.strftime("%H:%M:%S"), msg_type, reason, len(data)))
    if not hasattr(config, 'log_path'):
        return
    if error_filename is None:
        error_filename = error_log.open_csv(config.log_path)
    error_log.write_csv(error_filename, msg_type, reason, data)

def flush_bad_bytes():
    # pymavlink reports bytes outside a MAVLink packet one at a time; log them as one error
    if bad_bytes:
        log_decode_error('BAD_DATA', 'Bad prefix', bad_bytes)
        bad_bytes.clear()

while True:
    try:
        msg = master.recv_match()
    except Exception:
        msg = None # don't process the previous message again

    # forget RX info of transmitters not heard recently (BLE MAC addresses change often)
    now = time.time()
    for key in [k for k, v in last_rx_info.items() if now - v[0] >= RX_INFO_MAX_AGE]:
        del last_rx_info[key]

    # log message packs for which no RX information arrived in time
    for key in [k for k, v in pending_packs.items() if now - v[0] >= RX_INFO_MAX_AGE]:
        log_pack(pending_packs.pop(key)[1], None)

    if not msg:
        flush_bad_bytes() # no more data, so a run of bad bytes has ended
        time.sleep(0.1)
        continue
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)

    if msg.get_type() == 'BAD_DATA': # CRC error, invalid length or bytes outside a MAVLink packet
        if msg.reason == 'Bad prefix':
            bad_bytes.extend(msg.data)
            continue
        flush_bad_bytes()
        log_decode_error('BAD_DATA', msg.reason, msg.data)
        continue
    flush_bad_bytes()

    # pymavlink counts gaps in the sequence numbers; a corrupted packet often also swallows the next one
    if getattr(master, 'mav_loss', 0) > mav_loss:
        log_decode_error(msg.get_type(), "%u packet(s) lost before this one (sequence number gap)"
                         % (master.mav_loss - mav_loss), msg.get_msgbuf())
        mav_loss = master.mav_loss

    if msg.get_type().startswith('UNKNOWN_'): # valid CRC, but a message ID that is not in the dialect
        log_decode_error(msg.get_type(), "unknown MAVLink message ID", msg.get_msgbuf())
        continue

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
        # the RX information can arrive before or after its message pack
        key = bytes(msg.id_or_mac)
        pending = pending_packs.get(key)
        if pending is not None and rx_matches(msg, pending[1]):
            log_pack(pending_packs.pop(key)[1], msg)
        else:
            last_rx_info[key] = (now, msg)

        if config.print_messages == True:
            print("\n%s MAVLink OpenDroneID Radio RX Information message received" % current_time)
            #print("\n%s" % msg.to_dict()) #print raw packet contents
            odid.print_rx_information(msg)

    if msg.get_type() == 'OPEN_DRONE_ID_MESSAGE_PACK':
        if config.print_messages == True:
            print("\n%s MAVLink OpenDroneID Message Pack message received" % current_time)
            #print("\n%s" % msg.to_dict()) #print raw packet contents
            odid.print_message_pack(msg.messages, msg.msg_pack_size)

        # log with matching RX information if it already arrived, otherwise wait for it
        key = bytes(msg.id_or_mac)
        entry = last_rx_info.get(key)
        if entry is not None and rx_matches(entry[1], msg):
            log_pack(msg, last_rx_info.pop(key)[1])
        else:
            if key in pending_packs: # previous pack of this transmitter got no RX information
                log_pack(pending_packs[key][1], None)
            pending_packs[key] = (now, msg)

        if hasattr(config, 'sbs_server_ip_address'):
            try:
                sbs.export(msg.messages, msg.msg_pack_size)
            except Exception:
                pass
