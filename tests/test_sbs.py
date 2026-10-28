import io
import unittest
from contextlib import redirect_stdout

from modules import sbs
from tests import builder

class FakeConnection:
    def __init__(self):
        self.data = b''
        self.closed = False
    def sendall(self, data):
        self.data += data
    def setsockopt(self, *args):
        pass
    def close(self):
        self.closed = True

class BrokenConnection(FakeConnection):
    def sendall(self, data):
        raise ConnectionResetError("connection reset by peer")

class TestSBS(unittest.TestCase):
    def setUp(self):
        self.connection = FakeConnection()
        sbs.sbs_connection = self.connection

    def tearDown(self):
        sbs.sbs_connection = None

    def lines(self):
        return [line.split(',') for line in self.connection.data.decode('ascii').splitlines()]

    def test_airborne(self):
        payload, size = builder.pack(builder.basic_id(b'1581F5FJB22130'),
                                     builder.location(52.1, 4.2, alt_geo=100.0, direction=270, speed_enc=20))
        sbs.export(payload, size)
        msg1, msg3, msg4 = self.lines()
        icao = sbs.ICAO('1581F5FJB22130')
        self.assertEqual(msg1[:5], ['MSG', '1', '', '', icao])
        self.assertEqual(msg1[10], '1581' + '2130')
        self.assertEqual(msg3[:5], ['MSG', '3', '', '', icao])
        self.assertEqual(msg3[13], '270')
        self.assertEqual((float(msg3[14]), float(msg3[15])), (52.1, 4.2))
        self.assertEqual(msg3[21], '0') # not on ground
        self.assertEqual(msg4[:2], ['MSG', '4'])
        self.assertEqual(msg4[11], str(round(100.0*3.28084)))
        self.assertEqual(msg4[12], str(round(15.0*3.28084)))

    def test_unknown_speed_is_left_empty(self):
        payload, size = builder.pack(builder.basic_id(b'SN1'), builder.location(52.1, 4.2, speed_enc=255))
        sbs.export(payload, size)
        msg1, msg3, msg4 = self.lines()
        self.assertEqual(msg4[12], '')

    def test_only_serial_numbers_are_exported(self):
        payload, size = builder.pack(builder.basic_id(b'\xc3\xa9AB', id_type=4))
        sbs.export(payload, size)
        self.assertEqual(self.connection.data, b'')

    def test_disconnected_client_is_dropped(self):
        broken = BrokenConnection()
        sbs.sbs_connection = broken
        payload, size = builder.pack(builder.basic_id(b'SN1'), builder.location(52.1, 4.2))
        with redirect_stdout(io.StringIO()):
            sbs.export(payload, size)
        self.assertTrue(broken.closed)
        self.assertIsNone(sbs.sbs_connection)
        sbs.export(payload, size) # no client: nothing is sent and nothing fails

    def test_no_client(self):
        sbs.sbs_connection = None
        payload, size = builder.pack(builder.basic_id(b'SN1'), builder.location(52.1, 4.2))
        sbs.export(payload, size)
