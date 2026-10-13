import unittest
from types import SimpleNamespace

from modules import adsb
from tests import builder

class TestADSB(unittest.TestCase):
    def test_units(self):
        msg = SimpleNamespace(ICAO_address=0xABC123, lat=521234567, lon=47654321, altitude_type=1,
                              altitude=123456, heading=27050, hor_velocity=1234, ver_velocity=-150,
                              callsign='DRONE1', emitter_type=7, tslc=1, flags=3, squawk=0)
        out = builder.printed(adsb.print_payload, msg)
        self.assertEqual(out['ICAO address'], 'abc123')
        self.assertEqual(out['Latitude'], '52.1234567')
        self.assertEqual(out['Longitude'], '4.7654321')
        self.assertEqual(out['Altitude_type'], 'GNSS')
        self.assertEqual(out['Altitude'], '123.5 m')
        self.assertEqual(out['heading'], '270.5 deg')
        self.assertEqual(out['hor_velocity'], '12.34 m/s')
        self.assertEqual(out['ver_velocity'], '-1.50 m/s')
        self.assertEqual(out['emitter_type'], 'rotorcraft')
