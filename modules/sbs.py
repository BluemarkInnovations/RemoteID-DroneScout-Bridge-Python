from bitstruct import *
from enum import Enum
import socket
import config

ODID_ID_SIZE = 20
ODID_MESSAGE_SIZE = 25

#define MAVLink messages types
class ODID_MESSAGETYPE(Enum):
    ODID_MESSAGETYPE_BASIC_ID = 0
    ODID_MESSAGETYPE_LOCATION = 1
    ODID_MESSAGETYPE_AUTH = 2
    ODID_MESSAGETYPE_SELF_ID = 3
    ODID_MESSAGETYPE_SYSTEM = 4
    ODID_MESSAGETYPE_OPERATOR_ID = 5
    ODID_MESSAGETYPE_PACKED = 0xF

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

#removes characters like \t \n \r space from string
def clean_SN(string):
    string = string.replace(" ", "")
    string = string.replace("\t", "")
    string = string.replace("\n", "")
    string = string.replace("\r", "")

    return string

def transmit(data):
    try:
        sbs_connection.sendall(bytes(data,"ascii"))

    except (OSError, socket.error) as e:
        print("Error:", e)
        # reset connection
        sbs_connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
        sbs_connection.close()
    return

def location_decode_speed_horizontal(speed_enc, speed_mult):
    if speed_enc == 255:
	    return float('NaN')
    speed_enc = float (speed_enc)
    if speed_mult == 1:
        return float ((float(speed_enc) * 0.75) + (255 * 0.25))
    else:
        return speed_enc * 0.75

def export(payload, size):

    try:
        sbs_connection
    except NameError:
        pass
    else:
        IDType = 0
        UASID = ''
        Status = 0
        Emergency_flag = 0
        Is_on_ground_flag = 1
        SpeedMult = 0
        Latitude = 0
        Longitude = 0
        AltitudeGeo = 0
        AltitudeGeo = 0
        Direction = 0
        SpeedHorizontal = 0
        BasicIDpresent = 0
        Locationpresent = 0
        for x in range(size):
            RIDtype = payload[x*ODID_MESSAGE_SIZE] >> 4
            if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_BASIC_ID):
                BasicIDpresent = 1
                IDType = int(payload[x*ODID_MESSAGE_SIZE + 1] >> 4)
                UASID = (payload[x*ODID_MESSAGE_SIZE + 2: x*ODID_MESSAGE_SIZE + 2 + ODID_ID_SIZE])
                UASID = clean_SN(bytes(UASID).decode('ascii'))
                output_str = ""

            if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_LOCATION):
                Locationpresent = 1
                Status = (payload[x*ODID_MESSAGE_SIZE + 1] >> 4) & 0x0F
                SpeedMult = payload[x*ODID_MESSAGE_SIZE + 1] & 0x01
                Latitude = float(struct.unpack('i', bytes(payload)[x*ODID_MESSAGE_SIZE + 5: x*ODID_MESSAGE_SIZE + 9])[0])/(10*1000*1000)
                Longitude = float(struct.unpack('i', bytes(payload)[x*ODID_MESSAGE_SIZE + 9: x*ODID_MESSAGE_SIZE + 13])[0])/(10*1000*1000)
                AltitudeGeo = struct.unpack('H', bytes(payload)[x*ODID_MESSAGE_SIZE + 15:x*ODID_MESSAGE_SIZE + 17])
                AltitudeGeo = (int(AltitudeGeo[0]) - int(2000))/2
                Direction = int(payload[x*ODID_MESSAGE_SIZE + 2])
                if Direction > 360 or Direction < 0:
                    Direction = 0.0

                SpeedHorizontal = location_decode_speed_horizontal(payload[x*ODID_MESSAGE_SIZE + 3], SpeedMult)

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
