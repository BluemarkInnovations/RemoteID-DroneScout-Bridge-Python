import unittest

from modules import odid
from tests import builder

class TestBasicID(unittest.TestCase):
    def test_serial_number(self):
        out = builder.printed(odid.print_basicID, list(builder.basic_id(b'1581F5FJB2 21 3\t')))
        self.assertEqual(out['UASID'], '1581F5FJB2213')
        self.assertEqual(out['IDType'], 'Serial Number')
        self.assertEqual(out['UAType'], 'Helicopter (or Multirotor)')

    def test_binary_session_id_does_not_crash(self):
        out = builder.printed(odid.print_basicID, list(builder.basic_id(b'\xc3\xa9AB\x00\xff', id_type=4)))
        self.assertEqual(out['UASID'], 'AB')
        self.assertEqual(out['IDType'], 'specific session ID')

class TestLocation(unittest.TestCase):
    def decode(self, **kwargs):
        return builder.printed(odid.print_location, list(builder.location(52.1234567, -4.7654321, **kwargs)))

    def test_position_and_altitudes(self):
        out = self.decode(alt_baro=10.5, alt_geo=120.0, height=-3.5)
        self.assertEqual(out['Latitude'], '52.1234567')
        self.assertEqual(out['Longitude'], '-4.7654321')
        self.assertEqual(out['Altitude Baro'], '10.5')
        self.assertEqual(out['Altitude Geo'], '120.0')
        self.assertEqual(out['Height'], '-3.5')
        self.assertEqual(out['Status'], 'Airborne')

    def test_direction_west(self):
        out = self.decode(direction=270)
        self.assertEqual(out['EW Direction'], '1')
        self.assertEqual(out['Direction'], '270')

    def test_direction_east(self):
        self.assertEqual(self.decode(direction=179)['Direction'], '179')

    def test_vertical_speed_negative(self):
        self.assertEqual(self.decode(speed_vertical=-2.5)['Speed Vertical'], '-2.5')

    def test_vertical_speed_invalid(self):
        self.assertEqual(self.decode(speed_vertical=63)['Speed Vertical'], 'nan')

    def test_horizontal_speed(self):
        self.assertEqual(self.decode(speed_enc=20)['Speed Horizontal'], '15.0')
        self.assertEqual(self.decode(speed_enc=20, speed_mult=1)['Speed Horizontal'], '78.8')
        self.assertEqual(self.decode(speed_enc=255)['Speed Horizontal'], 'nan')

    def test_timestamp(self):
        self.assertEqual(self.decode(timestamp=12345)['Timestamp'], '20:34.5')
        self.assertEqual(self.decode(timestamp=0xFFFF)['Timestamp'], 'unknown')

class TestSystem(unittest.TestCase):
    def test_fields(self):
        msg = builder.system(52.5, 4.25, op_alt=10.5, area_radius=50, area_ceiling=100.5, area_floor=-0.5,
                             classification=1, location_type=2, timestamp=86400)
        out = builder.printed(odid.print_system, list(msg))
        self.assertEqual(out['Operator Latitude'], '52.5000000')
        self.assertEqual(out['Operator Longitude'], '4.2500000')
        self.assertEqual(out['Operator Altitude'], '10.5')
        self.assertEqual(out['Classification Type'], 'European Union')
        self.assertEqual(out['Operator Location Type'], 'Fixed')
        self.assertEqual(out['Area Radius'], '50')
        self.assertEqual(out['Area Ceiling'], '100.5')
        self.assertEqual(out['Area Floor'], '-0.5')
        self.assertEqual(out['UA category'], 'Open')
        self.assertEqual(out['UA class'], 'Class 1')
        self.assertEqual(out['Timestamp'], '2019-01-02 00:00:00 UTC')

class TestTextMessages(unittest.TestCase):
    def test_self_id(self):
        out = builder.printed(odid.print_selfID, list(builder.self_id(b'survey\tflight\xff')))
        self.assertEqual(out['Type'], 'Text')
        self.assertEqual(out['Text'], 'surveyflight')

    def test_operator_id(self):
        out = builder.printed(odid.print_operatorID, list(builder.operator_id(b'NLD87astrdge12k8')))
        self.assertEqual(out['Type'], 'Operator ID')
        self.assertEqual(out['Text'], 'NLD87astrdge12k8')

class TestMessagePack(unittest.TestCase):
    def test_unknown_message_type_is_skipped(self):
        unknown = bytes([0x62]) + bytes(24)
        payload, size = builder.pack(unknown, builder.basic_id(b'SN1'))
        out = builder.printed(odid.print_message_pack, payload, size)
        self.assertEqual(out['UASID'], 'SN1')

    def test_pack_size_is_limited(self):
        payload, _ = builder.pack(*[builder.basic_id(b'SN1')] * 9)
        builder.printed(odid.print_message_pack, payload, 255) # must not raise IndexError
