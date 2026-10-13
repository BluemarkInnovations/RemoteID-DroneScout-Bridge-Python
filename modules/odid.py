# OpenDroneID functions
from bitstruct import *
from enum import IntEnum
import datetime

from modules import rid

def print_rx_information(msg):
    # radio technology name, without the long enum prefix
    tech = rid.enums['MAV_ODID_RADIO_TECHNOLOGY'].get(msg.radio_technology)
    tech_name = tech.name.replace('MAV_ODID_RADIO_TECHNOLOGY_', '') if tech else "UNKNOWN (%u)" % msg.radio_technology

    # Bluetooth and WLAN receptions carry a MAC address; otherwise try to show it as an ID string
    mac_techs = (rid.MAV_ODID_RADIO_TECHNOLOGY_BLE_LEGACY, rid.MAV_ODID_RADIO_TECHNOLOGY_BLE_LR,
                 rid.MAV_ODID_RADIO_TECHNOLOGY_WLAN_BEACON, rid.MAV_ODID_RADIO_TECHNOLOGY_WLAN_NAN)
    if msg.radio_technology in mac_techs:
        id_or_mac = ':'.join('%02X' % b for b in msg.id_or_mac[:6])
    else:
        id_or_mac = bytes(msg.id_or_mac).split(b'\x00', 1)[0].decode('ascii', errors='replace')

    rssi = "unknown" if msg.rssi == 127 else "%d dBm" % msg.rssi
    channel = "unknown" if msg.channel == 0 else "%u" % msg.channel
    msg_id = "none" if msg.msg_id == 0 else "%u" % msg.msg_id
    time_usec = "unknown" if msg.time_usec == 0 else "%u us" % msg.time_usec

    print("ID/MAC:\t\t\t%s" % id_or_mac)
    print("Radio technology:\t%s" % tech_name)
    print("Channel:\t\t%s" % channel)
    print("RSSI:\t\t\t%s" % rssi)
    print("Counter:\t\t%u" % msg.counter)
    print("Related MAVLink msg ID:\t%s" % msg_id)
    print("Receiver ID:\t\t%u" % msg.receiver_id)
    print("Timestamp:\t\t%s" % time_usec)
    print("Brand:\t\t\t%s" % (msg.brand if msg.brand else "unknown"))
    print("Model:\t\t\t%s" % (msg.model if msg.model else "unknown"))

#define MAVLink messages types
class ODID_MESSAGETYPE(IntEnum):
    ODID_MESSAGETYPE_BASIC_ID = 0
    ODID_MESSAGETYPE_LOCATION = 1
    ODID_MESSAGETYPE_AUTH = 2
    ODID_MESSAGETYPE_SELF_ID = 3
    ODID_MESSAGETYPE_SYSTEM = 4
    ODID_MESSAGETYPE_OPERATOR_ID = 5
    ODID_MESSAGETYPE_PACKED = 0xF

ODID_ID_SIZE = 20
ODID_STR_SIZE = 23
ODID_MESSAGE_SIZE = 25
ODID_PACK_MAX_MESSAGES = 9 # a MAVLink message pack holds at most 9 messages (225 bytes)

def split_message_pack(payload, size):
    # yields (message type, protocol version, message bytes) for each message in a message pack
    for x in range(min(size, ODID_PACK_MAX_MESSAGES)):
        message = payload[x*ODID_MESSAGE_SIZE:x*ODID_MESSAGE_SIZE + ODID_MESSAGE_SIZE]
        yield message[0] >> 4, message[0] & 0x0F, message

def decode_message_pack(payload, size):
    # returns {message type: decoded fields}; if a type occurs more than once, the last one is used
    decoded = {}
    for RIDtype, ProtoVersion, message in split_message_pack(payload, size):
        if RIDtype in DECODERS:
            decoded[RIDtype] = DECODERS[RIDtype](message)
    return decoded

def decode_altitude(raw):
    # altitudes are encoded as (altitude + 1000) * 2
    return (raw - 2000)/2

def decode_basicID(payload):
    return {
        'id_type': payload[1] >> 4,
        'ua_type': payload[1] & 0x0F,
        'uas_id': clean_SN(clean_id(payload[2:2 + ODID_ID_SIZE])),
    }

def decode_location(payload):
    data = bytes(payload)
    speed_mult = payload[1] & 0x01
    ew_direction = (payload[1] >> 1) & 0x01
    speed_vertical = struct.unpack('<b', data[4:5])[0]*0.5 # signed value
    latitude, longitude, altitude_baro, altitude_geo, height = struct.unpack('<iiHHH', data[5:19])
    return {
        'status': (payload[1] >> 4) & 0x0F,
        'height_type': (payload[1] >> 2) & 0x01,
        'ew_direction': ew_direction,
        'speed_mult': speed_mult,
        'direction': payload[2] + 180*ew_direction, # direction is encoded as 0-179 plus an east/west flag
        'speed_horizontal': location_decode_speed_horizontal(payload[3], speed_mult),
        'speed_vertical': float('NaN') if speed_vertical == 63 else speed_vertical,
        'latitude': latitude/(10*1000*1000),
        'longitude': longitude/(10*1000*1000),
        'altitude_baro': decode_altitude(altitude_baro),
        'altitude_geo': decode_altitude(altitude_geo),
        'height': decode_altitude(height),
        'horiz_accuracy': payload[19] & 0x0F,
        'vert_accuracy': (payload[19] >> 4) & 0x0F,
        'baro_accuracy': (payload[20] >> 4) & 0x0F,
        'speed_accuracy': payload[20] & 0x0F,
        'timestamp': struct.unpack('<H', data[21:23])[0], # tenths of seconds since the full hour
        'ts_accuracy': payload[23] & 0x0F,
    }

def decode_selfID(payload):
    return {
        'type': payload[1],
        'text': clean_id(payload[2:2 + ODID_STR_SIZE]),
    }

def decode_system(payload):
    data = bytes(payload)
    operator_latitude, operator_longitude, area_count, area_radius, area_ceiling, area_floor = struct.unpack('<iiHBHH', data[2:17])
    operator_altitude, timestamp = struct.unpack('<HI', data[18:24])
    return {
        'classification_type': (payload[1] >> 2) & 0x07,
        'operator_location_type': payload[1] & 0x03,
        'operator_latitude': operator_latitude/(10*1000*1000),
        'operator_longitude': operator_longitude/(10*1000*1000),
        'area_count': area_count,
        'area_radius': area_radius*10, # encoded in steps of 10 m
        'area_ceiling': decode_altitude(area_ceiling),
        'area_floor': decode_altitude(area_floor),
        'ua_category': (payload[17] >> 4) & 0x0F,
        'ua_class': payload[17] & 0x0F,
        'operator_altitude': decode_altitude(operator_altitude),
        'timestamp': timestamp, # seconds since 01/01/2019
    }

def decode_operatorID(payload):
    return {
        'type': payload[1],
        'operator_id': clean_id(payload[2:2 + ODID_ID_SIZE]),
    }

DECODERS = {
    ODID_MESSAGETYPE.ODID_MESSAGETYPE_BASIC_ID: decode_basicID,
    ODID_MESSAGETYPE.ODID_MESSAGETYPE_LOCATION: decode_location,
    ODID_MESSAGETYPE.ODID_MESSAGETYPE_SELF_ID: decode_selfID,
    ODID_MESSAGETYPE.ODID_MESSAGETYPE_SYSTEM: decode_system,
    ODID_MESSAGETYPE.ODID_MESSAGETYPE_OPERATOR_ID: decode_operatorID,
}

def print_message_pack(payload, size):
    for RIDtype, ProtoVersion, message in split_message_pack(payload, size):
        if RIDtype in PRINTERS:
            title, print_message = PRINTERS[RIDtype]
            print("\n===%s===" % title)
            print("RID Type: %i" % RIDtype)
            print("Proto Version: %i" % ProtoVersion)
            print_message(message)

def print_basicID(payload):
    msg = decode_basicID(payload)
    print("UAType: %s" % decode_basicID_UA_type(msg['ua_type']))
    print("IDType: %s" % decode_basicID_ID_type(msg['id_type']))
    print("UASID: %s" % msg['uas_id'])

def print_location(payload):
    msg = decode_location(payload)
    print("Status: %s" % decode_location_status(msg['status']))
    print("Speed Mult: %i" % msg['speed_mult'])
    print("EW Direction: %i" % msg['ew_direction'])
    print("Height Type: %s" % decode_location_height_type(msg['height_type']))
    print("Direction: %i" % msg['direction'])
    print("Speed Horizontal: %2.1f" % msg['speed_horizontal'])
    print("Speed Vertical: %2.1f" % msg['speed_vertical'])
    print("Latitude: %2.7f" % msg['latitude'])
    print("Longitude: %2.7f" % msg['longitude'])
    print("Altitude Baro: %2.1f" % msg['altitude_baro'])
    print("Altitude Geo: %2.1f" % msg['altitude_geo'])
    print("Height: %2.1f" % msg['height'])
    print("Horiz Accuracy: %i" % msg['horiz_accuracy'])
    print("Vert Accuracy: %i" % msg['vert_accuracy'])
    print("Speed Accuracy: %i" % msg['speed_accuracy'])
    print("Timestamp: %s" % decode_location_timestamp(msg['timestamp']))
    print("Timestamp Accuracy: %i" % msg['ts_accuracy'])

def print_auth(payload):
    #todo
    print("todo")

def print_selfID(payload):
    msg = decode_selfID(payload)
    print("Type: %s" % decode_selfID_type(msg['type']))
    print("Text: %s" % msg['text'])

def print_system(payload):
    msg = decode_system(payload)
    print("Classification Type: %s" % decode_system_classification_type(msg['classification_type']))
    print("Operator Location Type: %s" % decode_system_operator_location_type(msg['operator_location_type']))
    print("Operator Latitude: %2.7f" % msg['operator_latitude'])
    print("Operator Longitude: %2.7f" % msg['operator_longitude'])
    print("Area Count: %i" % msg['area_count'])
    print("Area Radius: %i" % msg['area_radius'])
    print("Area Ceiling: %2.1f" % msg['area_ceiling'])
    print("Area Floor: %2.1f" % msg['area_floor'])
    print("UA category: %s" % decode_system_ua_category(msg['ua_category']))
    print("UA class: %s" % decode_system_ua_class(msg['ua_class']))
    print("Operator Altitude: %2.1f" % msg['operator_altitude'])
    print("Timestamp: %s" % decode_system_timestamp(msg['timestamp']))

def print_operatorID(payload):
    msg = decode_operatorID(payload)
    print("Type: %s" % decode_operatorID_type(msg['type']))
    print("Text: %s" % msg['operator_id'])

PRINTERS = {
    ODID_MESSAGETYPE.ODID_MESSAGETYPE_BASIC_ID: ("BasicID", print_basicID),
    ODID_MESSAGETYPE.ODID_MESSAGETYPE_LOCATION: ("Location", print_location),
    ODID_MESSAGETYPE.ODID_MESSAGETYPE_AUTH: ("Auth", print_auth),
    ODID_MESSAGETYPE.ODID_MESSAGETYPE_SELF_ID: ("SelfID", print_selfID),
    ODID_MESSAGETYPE.ODID_MESSAGETYPE_SYSTEM: ("System", print_system),
    ODID_MESSAGETYPE.ODID_MESSAGETYPE_OPERATOR_ID: ("OperatorID", print_operatorID),
}

#removes characters like \t \n \r space from string
def clean_SN(string):
    string = string.replace(" ", "")
    string = string.replace("\t", "")
    string = string.replace("\n", "")
    string = string.replace("\r", "")

    return string

#removes characters like \t \n \r from string
def clean_string(string):
    string = string.replace("\t", "")
    string = string.replace("\n", "")
    string = string.replace("\r", "")

    return string

#keeps printable ASCII only and stops at the first NUL; fields can contain binary data (e.g. session IDs)
def clean_id(raw):
    raw = bytes(raw).split(b'\x00', 1)[0]
    return ''.join(chr(b) for b in raw if 32 <= b < 127)

def decode_basicID_ID_type(IDType):
    string = ""
    if IDType == 0:
        string = "None"
    elif IDType == 1:
        string = "Serial Number"
    elif IDType == 2:
        string = "CAA Registration ID"
    elif IDType == 3:
        string = "UTM Assigned UUID"
    elif IDType == 4:
        string = "specific session ID"

    return string

def decode_basicID_UA_type(UAType):
    string = ""
    if UAType == 0:
        string = "None"
    elif UAType == 1:
        string = "Aeroplane"
    elif UAType == 2:
        string = "Helicopter (or Multirotor)"
    elif UAType == 3:
        string = "Gyroplane"
    elif UAType == 4:
        string = "Hybrid Lift"
    elif UAType == 5:
        string = "Ornithopter"
    elif UAType == 6:
        string = "Glider"
    elif UAType == 7:
        string = "Kite"
    elif UAType == 8:
        string = "Free Balloon"
    elif UAType == 9:
        string = "Captive Balloon"
    elif UAType == 10:
        string = "Airship (such as a blimp)"
    elif UAType == 11:
        string = "Free Fall/Parachute (unpowered)"
    elif UAType == 12:
        string = "Rocket"
    elif UAType == 13:
        string = "Tethered Powered Aircraft"
    elif UAType == 14:
        string = "Ground Obstacle"
    elif UAType == 15:
        string = "Other"

    return string

def decode_location_status(status):
    string = ""
    if status == 0:
        string = "Undeclared"
    elif status == 1:
        string = "Ground"
    elif status == 2:
        string = "Airborne"
    elif status == 3:
        string = "Emergency"
    elif status == 4:
        string = "Remote ID System Failure"

    return string

def decode_location_timestamp(timestamp):
    string = "unknown"
    if timestamp != 0xFFFF: # tenths of seconds since the full hour
        minutes = timestamp // 600
        seconds = (timestamp % 600) // 10
        tenths = timestamp % 10
        string = f"{minutes:02}:{seconds:02}.{tenths}"

    return string

def decode_location_height_type(height_type):
    string = ""
    if height_type == 0:
        string = "Above Takeoff"
    elif height_type == 1:
        string = "Above Ground Level"

    return string

def decode_selfID_type(selfID_type):
    string = ""
    if selfID_type == 0:
        string = "Text"
    elif selfID_type == 1:
        string = "Emergency"
    elif selfID_type == 2:
        string = "Extended Status"

    return string

def decode_system_classification_type(system_classification_type):
    string = ""
    if system_classification_type == 0:
        string = "Undeclared"
    elif system_classification_type == 1:
        string = "European Union"

    return string

def decode_system_operator_location_type(operator_location_type):
    string = ""
    if operator_location_type == 0:
        string = "Take Off"
    elif operator_location_type == 1:
        string = "Dynamic"
    elif operator_location_type == 2:
        string = "Fixed"

    return string

def decode_system_ua_category(ua_category):
    string = ""
    if ua_category == 0:
        string = "Undefined"
    elif ua_category == 1:
        string = "Open"
    elif ua_category == 2:
        string = "Specific"
    elif ua_category == 3:
        string = "Certified"

    return string

def decode_system_ua_class(ua_class):
    string = ""
    if ua_class == 0:
        string = "Undefined"
    elif ua_class == 1:
        string = "Class 0"
    elif ua_class == 2:
        string = "Class 1"
    elif ua_class == 3:
        string = "Class 2"
    elif ua_class == 4:
        string = "Class 3"
    elif ua_class == 5:
        string = "Class 4"
    elif ua_class == 6:
        string = "Class 5"
    elif ua_class == 7:
        string = "Class 6"

    return string

def decode_system_timestamp(timestamp):
    string = ""
    timestamp = timestamp + 1546300800 # add 01/01/2019
    string = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') + " UTC"

    return string

def location_decode_speed_horizontal(speed_enc, speed_mult):
    if speed_enc == 255:
        return float('NaN')
    speed_enc = float (speed_enc)
    if speed_mult == 1:
        return float ((float(speed_enc) * 0.75) + (255 * 0.25))
    else:
        return speed_enc * 0.75

def decode_operatorID_type(operatorID_type):
    string = ""
    if operatorID_type == 0:
        string = "Operator ID"

    return string
