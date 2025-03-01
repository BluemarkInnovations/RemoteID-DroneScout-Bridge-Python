from bitstruct import *
from enum import Enum

def print_payload(payload):
	print("ADS-B vehicle")
	print("ICAO address: %x" % payload.ICAO_address)
	print("Latitude: %i" % payload.lat)
	print("Longitude: %i" % payload.lon)
	print("Altitude_type: %i" % payload.altitude_type)
	print("Altitude: %i" % payload.altitude)
	print("heading: %i" % payload.heading)
	print("hor_velocity: %i" % payload.hor_velocity)
	print("ver_velocity: %i" % payload.ver_velocity)
	print("callsign: %s" % payload.callsign)
	print("emitter_type: %i" % payload.emitter_type)
	print("tslc: %i" % payload.tslc)
	print("flags: %8.8x" % payload.flags)
	print("squawk: %i\n" % payload.squawk)
