# ADSB vehicle functions

def print_payload(payload):
    print("ADS-B vehicle")
    print("ICAO address: %x" % payload.ICAO_address)
    print("Latitude: %2.7f" % (payload.lat/(10*1000*1000))) # degE7 to degrees
    print("Longitude: %2.7f" % (payload.lon/(10*1000*1000)))
    print("Altitude_type: %s" % decode_altitude_type(payload.altitude_type))
    print("Altitude: %2.1f m" % (payload.altitude/1000)) # mm to m
    print("heading: %2.1f deg" % (payload.heading/100)) # cdeg to deg
    print("hor_velocity: %2.2f m/s" % (payload.hor_velocity/100)) # cm/s to m/s
    print("ver_velocity: %2.2f m/s" % (payload.ver_velocity/100))
    print("callsign: %s" % payload.callsign)
    print("emitter_type: %s" % decode_emitter_type(payload.emitter_type))
    print("tslc: %i s" % payload.tslc)
    print("flags: %8.8x" % payload.flags)
    print("squawk: %i\n" % payload.squawk)

ALTITUDE_TYPE = {
    0: "Baro",
    1: "GNSS",
}

def decode_altitude_type(altitude_type):
    return ALTITUDE_TYPE.get(altitude_type, "")

EMITTER_TYPE = {
    0: "no info",
    1: "light",
    2: "small",
    3: "large",
    4: "high vortex large",
    5: "heavy",
    6: "highly maneuverable",
    7: "rotorcraft",
    8: "unassigned",
    9: "glider",
    10: "lighter than air",
    11: "parachute",
    12: "ultra light",
    13: "unassigned 2",
    14: "UAV",
    15: "space",
    16: "unassigned 3",
    17: "emergency surface",
    18: "service surface",
    19: "point obstacle",
}

def decode_emitter_type(emitter_type):
    return EMITTER_TYPE.get(emitter_type, "")
