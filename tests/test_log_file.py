import csv
import os
import tempfile
import unittest
from types import SimpleNamespace

from modules import log_file
from tests import builder

class TestLogFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.filename = log_file.open_csv(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def rows(self):
        with open(self.filename, newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    def test_filename_has_no_colons_or_spaces(self):
        name = os.path.basename(self.filename)
        self.assertNotIn(':', name)
        self.assertNotIn(' ', name)

    def test_row(self):
        payload, size = builder.pack(
            builder.basic_id(b'SN 123\xff'),
            builder.location(52.1, 4.2, alt_geo=120.5, height=30.0),
            builder.system(52.0, 4.0, op_alt=2.5),
            builder.operator_id(b'NLD87astrdge12k8'))
        log_file.write_csv(payload, size, self.filename)
        row = self.rows()[0]
        self.assertEqual(row['BasicID'], 'SN123')
        self.assertEqual(row['IDType'], '1')
        self.assertEqual(row['UAType'], '2')
        self.assertEqual(float(row['Latitude']), 52.1)
        self.assertEqual(float(row['Longitude']), 4.2)
        self.assertEqual(float(row['AltitudeGeo']), 120.5)
        self.assertEqual(float(row['Height']), 30.0)
        self.assertEqual(float(row['OperatorLatitude']), 52.0)
        self.assertEqual(float(row['OperatorLongitude']), 4.0)
        self.assertEqual(float(row['OperatorAltitudeGeo']), 2.5)
        self.assertEqual(row['OperatorID'], 'NLD87astrdge12k8')
        self.assertEqual(row['RSSI'], '')

    def test_row_with_rx_information(self):
        rx = SimpleNamespace(radio_technology=1, id_or_mac=[1, 2, 3, 4, 5, 0xAB] + [0]*14, channel=37,
                             rssi=-60, counter=5, receiver_id=7, brand='brand', model='model')
        payload, size = builder.pack(builder.basic_id(b'SN1'))
        log_file.write_csv(payload, size, self.filename, rx)
        row = self.rows()[0]
        self.assertEqual(row['RadioTechnology'], 'BLE_LEGACY')
        self.assertEqual(row['MAC'], '01:02:03:04:05:AB')
        self.assertEqual(row['Channel'], '37')
        self.assertEqual(row['RSSI'], '-60')

    def test_unknown_rssi_and_channel_are_empty(self):
        rx = SimpleNamespace(radio_technology=0, id_or_mac=[0]*20, channel=0, rssi=127, counter=0,
                             receiver_id=0, brand='', model='')
        payload, size = builder.pack(builder.basic_id(b'SN1'))
        log_file.write_csv(payload, size, self.filename, rx)
        row = self.rows()[0]
        self.assertEqual(row['RadioTechnology'], 'UNKNOWN')
        self.assertEqual(row['MAC'], '')
        self.assertEqual(row['Channel'], '')
        self.assertEqual(row['RSSI'], '')
