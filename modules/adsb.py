# ADSB vehicle functions

def print_payload(payload):
	print("ADS-B vehicle")
	print("ICAO address: %x" % payload.ICAO_address)
	print("Latitude: %i" % payload.lat)
	print("Longitude: %i" % payload.lon)
	print("Altitude_type: %s" % decode_altitude_type(payload.altitude_type))
	print("Altitude: %i" % payload.altitude)
	print("heading: %i" % payload.heading)
	print("hor_velocity: %i" % payload.hor_velocity)
	print("ver_velocity: %i" % payload.ver_velocity)
	print("callsign: %s" % payload.callsign)
	print("emitter_type: %s" % decode_emitter_type(payload.emitter_type))
	print("tslc: %i" % payload.tslc)
	print("flags: %8.8x" % payload.flags)
	print("squawk: %i\n" % payload.squawk)

def decode_altitude_type(altitude_type):
    string = ""
    if altitude_type == 0:
        string = "Baro"
    elif altitude_type == 1:
        string = "GNSS"

    return string

def decode_emitter_type(emitter_type):
    string = ""
    if emitter_type == 0:
        string = "no info"
    elif emitter_type == 1:
        string = "light"
    elif emitter_type == 2:
        string = "small"
    elif emitter_type == 3:
        string = "large"
    elif emitter_type == 4:
        string = "high vortex large"
    elif emitter_type == 5:
        string = "heavy"
    elif emitter_type == 6:
        string = "highly maneuverable"
    elif emitter_type == 7:
        string = "rotocraft"
    elif emitter_type == 8:
        string = "unassigned"
    elif emitter_type == 9:
        string = "glider"
    elif emitter_type == 10:
        string = "lighter than air"
    elif emitter_type == 11:
        string = "parachute"
    elif emitter_type == 12:
        string = "ultra light"
    elif emitter_type == 13:
        string = "unassigned 2"
    elif emitter_type == 14:
        string = "UAV"
    elif emitter_type == 15:
        string = "space"
    elif emitter_type == 16:
        string = "unassigned 3"
    elif emitter_type == 17:
        string = "emergency surface"
    elif emitter_type == 18:
        string = "service surface"
    elif emitter_type == 19:
        string = "point obstacle"
    return string
