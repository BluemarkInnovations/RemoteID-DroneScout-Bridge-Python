# builds encoded OpenDroneID messages (ASTM F3411) for the tests
import io
import struct
from contextlib import redirect_stdout

def encode_altitude(meters):
    return int(round((meters + 1000) * 2))

def basic_id(uas_id, id_type=1, ua_type=2):
    return bytes([0x02, (id_type << 4) | ua_type]) + uas_id.ljust(20, b'\0') + bytes(3)

def location(lat, lon, alt_baro=0.0, alt_geo=0.0, height=0.0, direction=0, speed_enc=0, speed_mult=0,
             speed_vertical=0.0, status=2, height_type=0, timestamp=0):
    ew = 1 if direction >= 180 else 0
    flags = (status << 4) | (height_type << 2) | (ew << 1) | speed_mult
    return struct.pack('<BBBBbiiHHHBBHB', 0x12, flags, direction - 180*ew, speed_enc, int(speed_vertical*2),
                       int(round(lat*1e7)), int(round(lon*1e7)), encode_altitude(alt_baro),
                       encode_altitude(alt_geo), encode_altitude(height), 0, 0, timestamp, 0) + bytes(1)

def self_id(text, desc_type=0):
    return bytes([0x32, desc_type]) + text.ljust(23, b'\0')

def system(op_lat, op_lon, op_alt=0.0, classification=1, location_type=1, area_count=1, area_radius=0,
           area_ceiling=0.0, area_floor=0.0, category=1, ua_class=2, timestamp=0):
    flags = (classification << 2) | location_type
    return struct.pack('<BBiiHBHHBHI', 0x42, flags, int(round(op_lat*1e7)), int(round(op_lon*1e7)),
                       area_count, area_radius // 10, encode_altitude(area_ceiling),
                       encode_altitude(area_floor), (category << 4) | ua_class,
                       encode_altitude(op_alt), timestamp) + bytes(1)

def operator_id(op_id, op_id_type=0):
    return bytes([0x52, op_id_type]) + op_id.ljust(20, b'\0') + bytes(3)

def pack(*messages):
    # returns (messages, msg_pack_size) as found in a MAVLink OPEN_DRONE_ID_MESSAGE_PACK
    return list(b''.join(messages).ljust(225, b'\0')), len(messages)

def printed(func, *args):
    # runs a print function and returns its "Key: value" lines as a dict
    out = io.StringIO()
    with redirect_stdout(out):
        func(*args)
    lines = [line.split(': ', 1) for line in out.getvalue().splitlines() if ': ' in line]
    return {key: value for key, value in lines}
