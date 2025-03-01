# OpenDroneID functions
from bitstruct import *
from enum import Enum

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

#removes characters like \t \n \r space from string
def clean_string(string):
    string = string.replace(" ", "")
    string = string.replace("\t", "")
    string = string.replace("\n", "")
    string = string.replace("\r", "")

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
		if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_SELF_ID):
			print("\n===SelfID===")
			print("RIDtype: %i" % RIDtype)
			print("ProtoVersion: %i" % ProtoVersion)
		if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_SYSTEM):
			print("\n===System===")
			print("RIDtype: %i" % RIDtype)
			print("ProtoVersion: %i" % ProtoVersion)
		if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_OPERATOR_ID):
			print("\===OperatorID===")
			print("RIDtype: %i" % RIDtype)
			print("ProtoVersion: %i" % ProtoVersion)

def print_basicID(payload):
	UAType = payload[1] >> 4
	IDType = payload[1] & 0x0F
	UASID = payload[2:2 + ODID_ID_SIZE]

	print("UAType: %i" % UAType)
	print("IDType: %i" % IDType)
	print("UASID: %s" % clean_string(bytes(UASID).decode('ascii')))

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
	print("SpeedMult: %i" % SpeedMult)
	print("EWDirection: %i" % EWDirection)
	print("HeightType: %s" % decode_location_height_type(HeightType))
	print("Direction: %i" % Direction)
	print("SpeedHorizontal: %i" % SpeedHorizontal)
	print("SpeedVertical: %i" % SpeedVertical)
	print("Latitude: %f" % (float(Latitude)/(10*1000*1000)))
	print("Longitude: %f" % (float(Longitude)/(10*1000*1000)))
	print("AltitudeBaro: %f" % ((int(AltitudeBaro[0]) - int(2000))/2))
	print("AltitudeGeo: %f" % ((int(AltitudeGeo[0]) - int(2000))/2))
	print("Height: %f" % ((int(Height[0]) - int(2000))/2))
	print("HorizAccuracy: %i" % int(HorizAccuracy))
	print("VertAccuracy: %i" % int(VertAccuracy))
	print("SpeedAccuracy: %i" % int(SpeedAccuracy))
	print("Timestamp: %s" % decode_location_timestamp(TimeStamp))
	print("Timestamp Accuracy: %i" % int(TSAccuracy))
