# OpenDroneID functions
from bitstruct import *
from enum import Enum
import datetime

#define MAVLink messages types
class ODID_MESSAGETYPE(Enum):
    ODID_MESSAGETYPE_BASIC_ID = 0
    ODID_MESSAGETYPE_LOCATION = 1
    ODID_MESSAGETYPE_AUTH = 2
    ODID_MESSAGETYPE_SELF_ID = 3
    ODID_MESSAGETYPE_SYSTEM = 4
    ODID_MESSAGETYPE_OPERATOR_ID = 5
    ODID_MESSAGETYPE_PACKED = 0xF

ODID_ID_SIZE = 20
ODID_STR_SIZE = 23

def print_message_pack(payload, size):

	for x in range(size):
		RIDtype = payload[x*25] >> 4
		ProtoVersion = payload[x*25] & 0x0F
		if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_BASIC_ID):
			print("\n===BasicID===")
			print("RIDtype: %i" % RIDtype)
			print("ProtoVersion: %i" % ProtoVersion)
			print_basicID(payload[x*25:x*25 + 25]) #each message is 25 bytes

		if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_LOCATION):
			print("\n===Location===")
			print("RIDtype: %i" % RIDtype)
			print("ProtoVersion: %i" % ProtoVersion)
			print_location(payload[x*25:x*25 + 25]) #each message is 25 bytes

		if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_AUTH):
			print("\n===Auth===")
			print("RIDtype: %i" % RIDtype)
			print("ProtoVersion: %i" % ProtoVersion)
			print_auth(payload[x*25:x*25 + 25]) #each message is 25 bytes

		if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_SELF_ID):
			print("\n===SelfID===")
			print("RIDtype: %i" % RIDtype)
			print("ProtoVersion: %i" % ProtoVersion)
			print_selfID(payload[x*25:x*25 + 25]) #each message is 25 bytes

		if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_SYSTEM):
			print("\n===System===")
			print("RIDtype: %i" % RIDtype)
			print("ProtoVersion: %i" % ProtoVersion)
			print_system(payload[x*25:x*25 + 25]) #each message is 25 bytes

		if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_OPERATOR_ID):
			print("\n===OperatorID===")
			print("RIDtype: %i" % RIDtype)
			print("ProtoVersion: %i" % ProtoVersion)
			print_operatorID(payload[x*25:x*25 + 25]) #each message is 25 bytes

def print_basicID(payload):
	IDType = payload[1] >> 4
	UAType = payload[1] & 0x0F
	UASID = payload[2:2 + ODID_ID_SIZE]

	print("UAType: %s" % decode_basicID_UA_type(UAType))
	print("IDType: %s" % decode_basicID_ID_type(IDType))
	print("UASID: %s" % clean_SN(bytes(UASID).decode('ascii')))

def print_location(payload):
	Status = (payload[1] >> 4) & 0x0F
	SpeedMult = payload[1] & 0x01
	EWDirection = (payload[1] >> 1) & 0x01
	HeightType = (payload[1] >> 2) & 0x01
	Direction = payload[2]
	SpeedHorizontal = payload[3]
	SpeedVertical = payload[4]
	Latitude = int(struct.unpack('i', bytes(payload)[5:9])[0])
	Longitude = int(struct.unpack('i', bytes(payload)[9:13])[0])
	AltitudeBaro = struct.unpack('H', bytes(payload)[13:15])
	AltitudeGeo = struct.unpack('H', bytes(payload)[15:17])
	Height = struct.unpack('H', bytes(payload)[17:19])
	HorizAccuracy = payload[19] & 0x0F
	VertAccuracy = (payload[19] >> 4)& 0x0F
	BaroAccuracy = (payload[20] >> 4)& 0x0F
	SpeedAccuracy = payload[20] & 0x0F
	TimeStamp = struct.unpack('<H', bytes(payload[21:23]))
	TSAccuracy = payload[23] & 0x0F

	print("Status: %s" % decode_location_status(Status))
	print("Speed Mult: %i" % SpeedMult)
	print("EW Direction: %i" % EWDirection)
	print("Height Type: %s" % decode_location_height_type(HeightType))
	print("Direction: %i" % Direction)
	print("Speed Horizontal: %i" % SpeedHorizontal)
	print("Speed Vertical: %i" % SpeedVertical)
	print("Latitude: %f" % (float(Latitude)/(10*1000*1000)))
	print("Longitude: %f" % (float(Longitude)/(10*1000*1000)))
	print("Altitude Baro: %f" % ((int(AltitudeBaro[0]) - int(2000))/2))
	print("Altitude Geo: %f" % ((int(AltitudeGeo[0]) - int(2000))/2))
	print("Height: %f" % ((int(Height[0]) - int(2000))/2))
	print("Horiz Accuracy: %i" % int(HorizAccuracy))
	print("Vert Accuracy: %i" % int(VertAccuracy))
	print("Speed Accuracy: %i" % int(SpeedAccuracy))
	print("Timestamp: %s" % decode_location_timestamp(TimeStamp))
	print("Timestamp Accuracy: %i" % int(TSAccuracy))

def print_auth(payload):
	#todo
	print("todo")

def print_selfID(payload):
	selfID_type = payload[1]
	selfID_text = payload[2:2 + ODID_STR_SIZE]

	print("Type: %s" % decode_selfID_type(selfID_type))
	print("Text: %s" % clean_string(bytes(selfID_text).decode('ascii')))

def print_system(payload):
	flags = payload[1]
	classification_type = (flags >> 2) & 0x03
	operator_location_type = flags & 0x03
	OperatorLatitude = int(struct.unpack('i', bytes(payload)[2:6])[0])
	OperatorLongitude = int(struct.unpack('i', bytes(payload)[6:10])[0])
	AreaCount = struct.unpack('<H', bytes(payload[10:12]))[0]
	AreaRadius = int(payload[12])
	AreaCeiling = struct.unpack('<h', bytes(payload[13:15]))
	AreaFloor = struct.unpack('<h', bytes(payload[15:17]))
	UA_category = (payload[17] >> 4) & 0x0F
	UA_class = payload[17] & 0x0F
	OperatordAltitude = struct.unpack('<h', bytes(payload)[18:20])
	TimeStamp = struct.unpack('<I', bytes(payload[20:24]))

	print("Classification Type: %s" % decode_system_classification_type(classification_type))
	print("Operator Location Type: %s" % decode_system_operator_location_type(operator_location_type))
	print("Operator Latitude: %f" % (float(OperatorLatitude)/(10*1000*1000)))
	print("Operator Longitude: %f" % (float(OperatorLongitude)/(10*1000*1000)))
	print("Area Count: %i" % AreaCount)
	print("Area Radius: %i" % AreaRadius)
	print("Area Ceiling: %i" % ((int(AreaCeiling[0]) - int(2000))/2))
	print("Area Floor: %i" % ((int(AreaFloor[0]) - int(2000))/2))
	print("UA category: %s" % decode_system_ua_category(UA_category))
	print("UA class: %s" % decode_system_ua_class(UA_class))
	print("Operator Altitude: %f" % ((int(OperatordAltitude[0]) - int(2000))/2))
	print("Timestamp: %s" % decode_system_timestamp(TimeStamp))

def print_operatorID(payload):
	operatorID_type = payload[1]
	operatorID = payload[2:2 + ODID_ID_SIZE]

	print("Type: %i" % operatorID_type)
	print("Text: %s" % clean_string(bytes(operatorID).decode('ascii')))

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
    string = ""
    timestamp = int(timestamp[0])
    minutes = int(timestamp/10/60)
    seconds = int((timestamp - minutes*60*10)/10)
    seconds_decimals = int((timestamp - minutes*60*10)/10 - seconds)
    string = str(f"{minutes:02}") + ":" + str(f"{seconds:02}") + "." + str(f"{seconds_decimals:02}")

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

def decode_system_ua_classification_type(ua_classification_type):
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
    timestamp = int(timestamp[0]) + 1546300800 # add 01/01/2019
    string = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') + " UTC"

    return string

