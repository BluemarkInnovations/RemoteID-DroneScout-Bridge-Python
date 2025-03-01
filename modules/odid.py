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

def print_message_pack(payload, size):

	for x in range(size):
		RIDtype = payload[x*25] >> 4
		ProtoVersion = payload[x*25] & 0x0F
		if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_BASIC_ID):
			print("\n===BasicID===")
			print("RIDtype: %i" % RIDtype)
			print("ProtoVersion: %i" % ProtoVersion)

			UAType = payload[x*25 + 1] >> 4
			IDType = payload[x*25 + 1] & 0x0F
			UASID = payload[x*25 + 2: x*25 + 2 + ODID_ID_SIZE]

			print("UAType: %i" % UAType)
			print("IDType: %i" % IDType)
			print("UASID: %s" % clean_string(bytes(UASID).decode('ascii')))

		if (ODID_MESSAGETYPE(RIDtype) == ODID_MESSAGETYPE.ODID_MESSAGETYPE_LOCATION):
			print("\n===Location===")
			print("RIDtype: %i" % RIDtype)
			print("ProtoVersion: %i" % ProtoVersion)

			Status = payload[x*25 + 1] & 0x0F
			SpeedMult = (payload[x*25 + 1] >> 4) & 0x01
			EWDirection = (payload[x*25 + 1] >> 5) & 0x01
			HeightType = (payload[x*25 + 1] >> 6) & 0x01
			Direction = payload[x*25 + 2]
			SpeedHorizontal = payload[x*25 + 3]
			SpeedVertical = payload[x*25 + 4]
			Latitude = struct.unpack('I', bytes(payload)[x*25 + 5:x*25 + 5 + 4])
			Longitude = struct.unpack('I', bytes(payload)[x*25 + 9:x*25 + 9 + 4])
			AltitudeBaro = struct.unpack('H', bytes(payload)[x*25 + 13:x*25 + 13 + 2])
			AltitudeGeo = struct.unpack('H', bytes(payload)[x*25 + 15:x*25 + 15 + 2])
			Height = struct.unpack('H', bytes(payload)[x*25 + 17:x*25 + 17 + 2])

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
