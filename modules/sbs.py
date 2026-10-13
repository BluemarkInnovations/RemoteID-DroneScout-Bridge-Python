from bitstruct import *
from enum import Enum
import socket
import config

from modules import odid # opendroneID functions

def connect(name):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((config.sbs_server_ip_address, config.sbs_server_port))
        print("Listen for TCP connection")
        s.listen()
        while True:
            global sbs_connection
            sbs_connection, addr = s.accept()
            print("Accepted")

def ICAO(data):
    ICAO = "FF" # start with FF to indicate an invalid ICAO 24-digit code
    i = 0
    checksum1 = 0
    checksum2 = 0

    data_hex = data.encode("utf-8").hex()
    while i < len(data_hex):
        checksum1 = checksum1 ^ ord(data_hex[i])
        checksum2 = checksum1 ^ checksum2
        i += 1

    ICAO += str(format(checksum1, '02X')) # add two bytes checksum as ICAO code
    ICAO += str(format(checksum2, '02X'))
    return ICAO

def callsign(data):
    callsign = str(data)
    if len(data) > 8:
        callsign = str(data[0:4]) # call sign is manufacturer code
        callsign += str(data[-4:]) # last 4 digit SN
        callsign = callsign.ljust(8)
    return callsign

def transmit(data):
    try:
        sbs_connection.sendall(bytes(data,"ascii"))

    except (OSError, socket.error) as e:
        print("Error:", e)
        # reset connection
        sbs_connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
        sbs_connection.close()
    return

def export(payload, size):

    try:
        sbs_connection
    except NameError:
        pass
    else:
        Emergency_flag = 0
        Is_on_ground_flag = 1

        pack = odid.decode_message_pack(payload, size)
        basicID = pack.get(odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_BASIC_ID)
        location = pack.get(odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_LOCATION)
        BasicIDpresent = 1 if basicID else 0
        Locationpresent = 1 if location else 0
        if basicID:
            IDType = basicID['id_type']
            UASID = basicID['uas_id']
        if location:
            Status = location['status']
            Latitude = location['latitude']
            Longitude = location['longitude']
            AltitudeGeo = location['altitude_geo']
            SpeedHorizontal = location['speed_horizontal']
            Direction = location['direction']
            if Direction > 360 or Direction < 0:
                Direction = 0.0

        # decode the entire message pack, now create SBS messages
        if BasicIDpresent == 1:
            #send MSG 1 identification
            output_str = ""
            output_str += str("MSG,1,,,")

            if IDType == 1: #only include serial number type
                icao = ICAO(UASID)

                # MSG 1 generation and transmit
                output_str += icao
                output_str += str(",,,,,,")
                output_str += callsign(UASID)
                output_str += str(",,,,,,,,0,0,0,0\n")

                transmit(output_str)

                # MSG 2, 3, or 4 generation depending on in air or on ground status
                if Locationpresent == 1 and Status > 0:
                    output_str = str("MSG,2,,,")
                    if Status == 2: #in air
                        output_str = str("MSG,3,,,")
                        Is_on_ground_flag = 0

                    if Status in (3, 4): # emergency codes
                        Emergency_flag = 1

                    flag_str = str(",,,0,") + str(Emergency_flag) + ",0," + str(Is_on_ground_flag) + str("\n")
                    output_str += icao
                    output_str += str(",,,,,,,")

                    # for MSG 2 include these fields
                    if Status == 1: #ground
                        output_str += str(round(AltitudeGeo*3.28084))

                    output_str += str(",")
                    if Status == 1: #ground
                        output_str += str(round(SpeedHorizontal*3.28084))

                    output_str += str(",")
                    output_str += str(round(Direction))
                    output_str += str(",")
                    output_str += str(Latitude)
                    output_str += str(",")
                    output_str += str(Longitude)
                    output_str += flag_str

                    transmit(output_str)

                    if Status == 2: #air, send msg 4 also
                        output_str = str("MSG,4,,,")
                        output_str += icao
                        output_str += str(",,,,,,,")
                        output_str += str(round(AltitudeGeo*3.28084))
                        output_str += str(",")
                        output_str += str(round(SpeedHorizontal*3.28084))
                        output_str += str(",")
                        output_str += str(round(Direction))
                        output_str += str(",,,,0,0,0,0\n")

                        transmit(output_str)
