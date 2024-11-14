#!/usr/bin/python3
# (c) Bluemark Innovations BV
# MIT license

import time
from pymavlink import mavutil
from enum import Enum
import config # config.py with settings

from bitstruct import *

class ODID_MESSAGETYPE(Enum):
    ODID_MESSAGETYPE_BASIC_ID = 0
    ODID_MESSAGETYPE_LOCATION = 1
    ODID_MESSAGETYPE_AUTH = 2
    ODID_MESSAGETYPE_SELF_ID = 3
    ODID_MESSAGETYPE_SYSTEM = 4
    ODID_MESSAGETYPE_OPERATOR_ID = 5
    ODID_MESSAGETYPE_PACKED = 0xF

ODID_ID_SIZE = 20

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
        print("%s MAVLink heartbeat received\n" % current_time)

    if msg.get_type() == 'ADSB_VEHICLE':
        print("%s MAVLink ADS-B vehicle message received\n" % current_time)
        #print("%s" % msg.to_dict())
        print("ADS-B vehicle")
        print("ICAO address: %x" % msg.ICAO_address)
        print("Latitude: %i" % msg.lat)
        print("Longitude: %i" % msg.lon)
        print("Altitude_type: %i" % msg.altitude_type)
        print("Altitude: %i" % msg.altitude)
        print("heading: %i" % msg.heading)
        print("hor_velocity: %i" % msg.hor_velocity)
        print("ver_velocity: %i" % msg.ver_velocity)
        print("callsign: %s" % msg.callsign)
        print("emitter_type: %i" % msg.emitter_type)
        print("tslc: %i" % msg.tslc)
        print("flags: %8.8x" % msg.flags)
        print("squawk: %i\n" % msg.squawk)

    if msg.get_type() == 'OPEN_DRONE_ID_MESSAGE_PACK':
        #print("\n%s" % msg.to_dict()) #print raw packet contents
        print("%s MAVLink OpenDroneID Message Pack message received\n" % current_time)
        for x in range(msg.msg_pack_size):
            RIDtype = msg.messages[x*25] >> 4
            ProtoVersion = msg.messages[x*25] & 0x0F
            if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_BASIC_ID):
                print("BasicID")
                print("RIDtype: %i" % RIDtype)
                print("ProtoVersion: %i" % ProtoVersion)

                UAType = msg.messages[x*25 + 1] >> 4
                IDType = msg.messages[x*25 + 1] & 0x0F
                UASID = msg.messages[x*25 + 2: x*25 + 2 + ODID_ID_SIZE]

                print("UAType: %i" % UAType)
                print("IDType: %i" % IDType)
                print("UASID: %s" % bytes(UASID).decode('ascii'))

            if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_LOCATION):
                print("Location")
                print("RIDtype: %i" % RIDtype)
                print("ProtoVersion: %i" % ProtoVersion)

                Status = msg.messages[x*25 + 1] & 0x0F
                SpeedMult = (msg.messages[x*25 + 1] >> 4) & 0x01
                EWDirection = (msg.messages[x*25 + 1] >> 5) & 0x01
                HeightType = (msg.messages[x*25 + 1] >> 6) & 0x01
                Direction = msg.messages[x*25 + 2]
                SpeedHorizontal = msg.messages[x*25 + 3]
                SpeedVertical = msg.messages[x*25 + 4]
                Latitude = struct.unpack('I', bytes(msg.messages)[x*25 + 5:x*25 + 5 + 4])
                Longitude = struct.unpack('I', bytes(msg.messages)[x*25 + 9:x*25 + 9 + 4])
                AltitudeBaro = struct.unpack('H', bytes(msg.messages)[x*25 + 13:x*25 + 13 + 2])
                AltitudeGeo = struct.unpack('H', bytes(msg.messages)[x*25 + 15:x*25 + 15 + 2])
                Height = struct.unpack('H', bytes(msg.messages)[x*25 + 17:x*25 + 17 + 2])

                print("Status: %i" % Status)
                print("SpeedMult: %i" % SpeedMult)
                print("EWDirection: %i" % EWDirection)
                print("HeightType: %i" % HeightType)
                print("Direction: %i" % Direction)
                print("SpeedHorizontal: %i" % SpeedHorizontal)
                print("SpeedVertical: %i" % SpeedVertical)
                print("Latitude: %i" % Latitude)
                print("Longitude: %i" % Longitude)
                print("AltitudeBaro: %f" % ((int(AltitudeBaro[0]) - int(2000))/2))
                print("AltitudeGeo: %f" % ((int(AltitudeGeo[0]) - int(2000))/2))
                print("Height: %f" % ((int(Height[0]) - int(2000))/2))
            if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_AUTH):
                print("Auth")
                print("RIDtype: %i" % RIDtype)
                print("ProtoVersion: %i" % ProtoVersion)
            if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_SELF_ID):
                print("SelfID")
                print("RIDtype: %i" % RIDtype)
                print("ProtoVersion: %i" % ProtoVersion)
            if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_SYSTEM):
                print("System")
                print("RIDtype: %i" % RIDtype)
                print("ProtoVersion: %i" % ProtoVersion)
            if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_OPERATOR_ID):
                print("OperatorID")
                print("RIDtype: %i" % RIDtype)
                print("ProtoVersion: %i" % ProtoVersion)
        print("\n")
