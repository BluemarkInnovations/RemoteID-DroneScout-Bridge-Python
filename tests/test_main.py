import csv
import glob
import os
import runpy
import tempfile
import time
import unittest

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

def rx_msg(n, rssi):
    return rid.MAVLink_open_drone_id_radio_rx_information_message(
        0, 0, mac(n), mavutil.mavlink.MAVLINK_MSG_ID_OPEN_DRONE_ID_MESSAGE_PACK, 1, 0, 7, 1, 37, rssi, b'b', b'm')

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

    def test_rx_information_matched_in_any_order(self):
        rows = self.run_main([rx_msg(1, -40), pack_msg(1, b'RXFIRST'),
                              pack_msg(2, b'PACKFIRST'), rx_msg(2, -50),
                              pack_msg(3, b'NORX'), 'wait'])
        self.assertEqual([(r['BasicID'], r['RSSI']) for r in rows],
                         [('RXFIRST', '-40'), ('PACKFIRST', '-50'), ('NORX', '')])

    def test_old_rx_information_is_not_used(self):
        rows = self.run_main([rx_msg(1, -40), 'wait', pack_msg(1, b'SN1'), 'wait'])
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
