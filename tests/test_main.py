import csv
import glob
import os
import runpy
import tempfile
import time
import unittest
import zlib

from pymavlink import mavutil

import config
from modules import rid
from tests import builder

MAIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'main.py')

class Stop(BaseException):
    pass

class FakeMaster:
    # replays a script of messages; 'wait' sleeps past RX_INFO_MAX_AGE, exceptions are raised
    def __init__(self, script):
        self.script = list(script)
    def wait_heartbeat(self):
        pass
    def recv_match(self):
        if not self.script:
            raise Stop()
        item = self.script.pop(0)
        if item == 'wait':
            time.sleep(2.2)
            return None
        if isinstance(item, BaseException):
            raise item
        return item

def mac(n):
    return [n, 2, 3, 4, 5, 6] + [0]*14

def pack_msg(n, serial):
    payload, size = builder.pack(builder.basic_id(serial))
    return mavutil.mavlink.MAVLink_open_drone_id_message_pack_message(0, 0, mac(n), 25, size, payload)

def crc(pack):
    # msg_crc of the RX information that belongs to the message pack
    return zlib.crc32(bytes(pack.messages[:pack.msg_pack_size * 25]))

def rx_msg(n, rssi, pack):
    # RX information that belongs to the message pack
    return rid.MAVLink_open_drone_id_radio_rx_information_message(
        0, 0, mac(n), crc(pack), 1, 0, 7, 1, 37, rssi, b'b', b'm')

def encode(msg, seq):
    # returns the bytes of a MAVLink packet as sent by the bridge
    mav = mavutil.mavlink.MAVLink(None, 1, 1)
    mav.seq = seq
    return bytes(msg.pack(mav))

def heartbeat():
    return mavutil.mavlink.MAVLink_heartbeat_message(6, 8, 0, 0, 0, 3)

class StreamMaster:
    # parses a byte stream with pymavlink, like a serial connection; stops when the stream is read twice
    def __init__(self, connect, path):
        self.conn = connect(path, notimestamps=True) # the real mavutil.mavlink_connection
        self.empty = 0
    def __getattr__(self, name):
        return getattr(self.conn, name)
    def wait_heartbeat(self):
        pass
    def recv_match(self):
        msg = self.conn.recv_match()
        if msg is None:
            self.empty += 1
            if self.empty > 1:
                raise Stop()
        return msg

class TestMainLoop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = dict(vars(config))
        config.log_path = self.tmp.name
        config.print_messages = False
        for name in ('sbs_server_ip_address', 'sbs_server_port'):
            if hasattr(config, name):
                delattr(config, name)
        self.saved_connection = mavutil.mavlink_connection

    def tearDown(self):
        mavutil.mavlink_connection = self.saved_connection
        for name in list(vars(config)):
            if not name.startswith('__') and name not in self.saved:
                delattr(config, name)
        for name, value in self.saved.items():
            setattr(config, name, value)
        self.tmp.cleanup()

    def run_main(self, script):
        mavutil.mavlink_connection = lambda *args, **kwargs: FakeMaster(script)
        with self.assertRaises(Stop):
            runpy.run_path(MAIN, run_name='__main__')
        files = glob.glob(os.path.join(self.tmp.name, '*.csv'))
        if not files:
            return []
        with open(files[0], newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    def run_stream(self, data):
        # runs main.py on a MAVLink byte stream and returns the rows of the decode error log
        path = os.path.join(self.tmp.name, 'stream.raw') # not .bin, which pymavlink opens as a DataFlash log
        with open(path, 'wb') as f:
            f.write(data)
        mavutil.mavlink_connection = lambda *args, **kwargs: StreamMaster(self.saved_connection, path)
        with self.assertRaises(Stop):
            runpy.run_path(MAIN, run_name='__main__')
        files = glob.glob(os.path.join(self.tmp.name, '*_decode_errors.csv'))
        if not files:
            return []
        with open(files[0], newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    def test_valid_stream_has_no_decode_errors(self):
        data = encode(heartbeat(), 0) + encode(pack_msg(1, b'SN1'), 1) + encode(heartbeat(), 2)
        self.assertEqual(self.run_stream(data), [])

    def test_corrupted_packets_are_logged(self):
        corrupt = bytearray(encode(pack_msg(1, b'SN1'), 1))
        corrupt[20] ^= 0xFF
        data = encode(heartbeat(), 0) + bytes(corrupt) + b'junk' + encode(heartbeat(), 2)
        rows = self.run_stream(data)
        self.assertEqual([r['MessageType'] for r in rows], ['BAD_DATA', 'BAD_DATA', 'HEARTBEAT'])
        self.assertIn('invalid MAVLink CRC', rows[0]['Reason'])
        self.assertEqual(rows[0]['Data'], bytes(corrupt).hex(' '))
        self.assertEqual((rows[1]['Reason'], rows[1]['Data']), ('Bad prefix', b'junk'.hex(' ')))
        self.assertIn('1 packet(s) lost', rows[2]['Reason'])

    def test_corrupted_pack_is_not_logged_as_detection(self):
        corrupt = bytearray(encode(pack_msg(1, b'SN1'), 0))
        corrupt[20] ^= 0xFF
        self.run_stream(bytes(corrupt) + encode(heartbeat(), 1))
        self.assertEqual(glob.glob(os.path.join(self.tmp.name, '*_remoteID_log.csv')), [])

    def test_rx_information_matched_in_any_order(self):
        first, second = pack_msg(1, b'RXFIRST'), pack_msg(2, b'PACKFIRST')
        rows = self.run_main([rx_msg(1, -40, first), first,
                              second, rx_msg(2, -50, second),
                              pack_msg(3, b'NORX'), 'wait'])
        self.assertEqual([(r['BasicID'], r['RSSI']) for r in rows],
                         [('RXFIRST', '-40'), ('PACKFIRST', '-50'), ('NORX', '')])

    def test_rx_information_of_other_message_is_not_used(self):
        # same transmitter, but the RX information belongs to a different message pack
        rows = self.run_main([rx_msg(1, -40, pack_msg(1, b'OTHER')), pack_msg(1, b'SN1'),
                              pack_msg(2, b'SN2'), rx_msg(2, -50, pack_msg(2, b'OTHER')), 'wait'])
        self.assertEqual([(r['BasicID'], r['RSSI']) for r in rows], [('SN1', ''), ('SN2', '')])

    def test_rx_information_matched_after_mavlink_decode(self):
        # the CRC must also match for packs that are decoded from a (truncated MAVLink 2) byte stream
        pack = pack_msg(1, b'SN1')
        mav = mavutil.mavlink.MAVLink(None)
        decoded = mav.decode(bytearray(encode(pack, 0)))
        rows = self.run_main([rx_msg(1, -40, pack), decoded, 'wait'])
        self.assertEqual([(r['BasicID'], r['RSSI']) for r in rows], [('SN1', '-40')])

    def test_old_rx_information_is_not_used(self):
        pack = pack_msg(1, b'SN1')
        rows = self.run_main([rx_msg(1, -40, pack), 'wait', pack, 'wait'])
        self.assertEqual([(r['BasicID'], r['RSSI']) for r in rows], [('SN1', '')])

    def test_read_error_does_not_repeat_previous_message(self):
        rows = self.run_main([pack_msg(1, b'SN1'), OSError('device disconnected'), 'wait'])
        self.assertEqual(len(rows), 1)

    def test_keyboard_interrupt_is_not_swallowed(self):
        mavutil.mavlink_connection = lambda *args, **kwargs: FakeMaster([KeyboardInterrupt()])
        with self.assertRaises(KeyboardInterrupt):
            runpy.run_path(MAIN, run_name='__main__')

    def test_message_id_collision_is_detected(self):
        msgid = rid.MAVLINK_MSG_ID_OPEN_DRONE_ID_RADIO_RX_INFORMATION
        base = mavutil.mavlink.mavlink_map
        saved = base.get(msgid)
        base[msgid] = mavutil.mavlink.MAVLink_heartbeat_message
        try:
            with self.assertRaises(RuntimeError):
                runpy.run_path(MAIN, run_name='__main__')
        finally:
            if saved is None:
                del base[msgid]
            else:
                base[msgid] = saved
