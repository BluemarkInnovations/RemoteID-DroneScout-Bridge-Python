#!/usr/bin/python3
# (c) Bluemark Innovations BV
# MIT license
# upload a new firmware image to the DroneScout Bridge using MAVLink FTP
# (FILE_TRANSFER_PROTOCOL message).
#
# usage: python3 firmware_upgrade.py firmware.bin [--device /dev/ttyUSB0] [--baudrate 115200]
#        python3 firmware_upgrade.py --reboot-only
#        python3 firmware_upgrade.py --info

import os
os.environ['MAVLINK20'] = '1'   # use the MAVLink 2 dialects; must be before importing mavutil

import sys
import time
import random
import struct
import argparse
from pymavlink import mavutil
from serial.tools import list_ports

import config # config.py with settings

# virtual file on the bridge; writing to it streams the data into the next OTA partition
FIRMWARE_PATH = "@ota/firmware.bin"

# MAVLink FTP opcodes, see https://mavlink.io/en/services/ftp.html
OP_NONE = 0
OP_TERMINATE_SESSION = 1
OP_RESET_SESSIONS = 2
OP_CREATE_FILE = 6
OP_WRITE_FILE = 7
OP_CALC_FILE_CRC32 = 14
OP_ACK = 128
OP_NAK = 129

NAK_ERRORS = {
    0: "None", 1: "Fail", 2: "FailErrno", 3: "InvalidDataSize", 4: "InvalidSession",
    5: "NoSessionsAvailable", 6: "EOF", 7: "UnknownCommand", 8: "FileExists",
    9: "FileProtected", 10: "FileNotFound",
}

PAYLOAD_LEN = 251           # size of FILE_TRANSFER_PROTOCOL.payload
HEADER_FMT = '<HBBBBBBI'    # seq, session, opcode, size, req_opcode, burst_complete, padding, offset
HEADER_LEN = struct.calcsize(HEADER_FMT)
MAX_DATA = PAYLOAD_LEN - HEADER_LEN  # 239 bytes of data per message

ESP_IMAGE_MAGIC = 0xE9
ESP_CHIP_IDS = {0x0005: "ESP32-C3", 0x0017: "ESP32-C5"}  # chips used in the DroneScout Bridge

# AUTOPILOT_VERSION.vendor_id/product_id of the bridge
BRIDGE_VENDOR_ID = 0xB1E0
BRIDGE_MODELS = {1: "DroneScout Bridge (2.4 GHz)", 2: "DroneScout Bridge triple-band (2.4/5 GHz)"}
BRIDGE_CHIPS = {1: "ESP32-C3", 2: "ESP32-C5"}  # chip of each bridge model


class FtpError(Exception):
    pass


class FtpReply:
    def __init__(self, payload):
        raw = bytes(payload)
        (self.seq, self.session, self.opcode, self.size, self.req_opcode,
         self.burst_complete, _, self.offset) = struct.unpack_from(HEADER_FMT, raw)
        self.data = raw[HEADER_LEN:HEADER_LEN + self.size]

    def nak_reason(self):
        if self.size == 0:
            return "unknown"
        reason = NAK_ERRORS.get(self.data[0], "error %d" % self.data[0])
        if self.data[0] == 2 and self.size > 1: # FailErrno has the errno in the second byte
            reason += " (errno %d)" % self.data[1]
        return reason


class MavFtp:
    def __init__(self, master, timeout):
        self.master = master
        self.timeout = timeout
        # the bridge answers a request with the same seq as its previous one from a cache, also
        # when that request came from an earlier run; a random start avoids those stale replies
        self.seq = random.randrange(0x10000)
        self.session = 0

    def send(self, opcode, offset=0, data=b'', seq=None):
        """Send one FTP request and return the sequence number used."""
        if seq is None:
            seq = self.seq
            self.seq = (self.seq + 1) & 0xFFFF
        payload = struct.pack(HEADER_FMT, seq, self.session, opcode, len(data), 0, 0, 0, offset) + data
        payload = payload.ljust(PAYLOAD_LEN, b'\0')
        self.master.mav.file_transfer_protocol_send(0, self.master.target_system,
                                                    self.master.target_component, list(payload))
        return seq

    def receive(self, timeout):
        """Return the next FTP reply addressed to us, or None on timeout."""
        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            msg = self.master.recv_match(type='FILE_TRANSFER_PROTOCOL', blocking=True, timeout=remaining)
            if msg is None:
                return None
            if msg.target_system not in (0, self.master.mav.srcSystem):
                continue
            return FtpReply(msg.payload)

    def request(self, opcode, offset=0, data=b'', timeout=None, retries=5):
        """Send a request and wait for its ACK; a retry reuses the sequence number so the
        bridge can recognise it and resend its previous reply."""
        timeout = timeout or self.timeout
        seq = None
        for _ in range(retries):
            seq = self.send(opcode, offset, data, seq)
            deadline = time.time() + timeout
            while time.time() < deadline:
                reply = self.receive(deadline - time.time())
                if reply is None:
                    break
                if reply.req_opcode != opcode or reply.seq != ((seq + 1) & 0xFFFF):
                    continue # stale reply of an earlier request
                if reply.opcode == OP_NAK:
                    raise FtpError("opcode %d refused: %s" % (opcode, reply.nak_reason()))
                return reply
        raise FtpError("no reply for opcode %d" % opcode)

    def write_file(self, image, window, max_retries, progress):
        """Write the image using a sliding window of outstanding WriteFile requests (go-back-N).
        The bridge writes strictly sequentially, so an ACK for offset X means all data before
        X has been stored. A lost message causes NAKs/timeouts and a rewind to the last ACK."""
        size = len(image)
        acked = 0       # bytes confirmed by the bridge
        next_off = 0    # next offset to send
        inflight = {}   # seq -> (offset, length, send time)
        retries = 0
        reason = None   # why the last rewind happened
        stats = {'sent': 0, 'naks': 0, 'timeouts': 0, 'rtt_sum': 0.0, 'rtt_n': 0, 'rtt_max': 0.0}

        while acked < size:
            while len(inflight) < window and next_off < size:
                chunk = image[next_off:next_off + MAX_DATA]
                seq = self.send(OP_WRITE_FILE, next_off, chunk)
                inflight[seq] = (next_off, len(chunk), time.time())
                next_off += len(chunk)
                stats['sent'] += 1

            rewind = False
            reply = self.receive(0.05)
            if reply is not None and reply.req_opcode == OP_WRITE_FILE:
                req_seq = (reply.seq - 1) & 0xFFFF
                if req_seq in inflight:
                    offset, length, sent_at = inflight.pop(req_seq)
                    rtt = time.time() - sent_at
                    stats['rtt_sum'] += rtt
                    stats['rtt_n'] += 1
                    stats['rtt_max'] = max(stats['rtt_max'], rtt)
                    if reply.opcode == OP_ACK:
                        if offset + length > acked:
                            acked = offset + length
                            progress(acked, size)
                        retries = 0
                        inflight = {s: v for s, v in inflight.items() if v[0] + v[1] > acked}
                    else:
                        reason = "NAK %s at offset %d" % (reply.nak_reason(), offset)
                        stats['naks'] += 1
                        rewind = True

            if inflight and time.time() - min(v[2] for v in inflight.values()) > self.timeout:
                reason = "no reply within %.1f s" % self.timeout
                stats['timeouts'] += 1
                rewind = True

            if rewind:
                retries += 1
                if retries > max_retries:
                    raise FtpError("too many retries at offset %d, last: %s" % (acked, reason))
                inflight.clear()
                next_off = acked
        return stats


ESPRESSIF_USB_VID = 0x303A  # native USB of the ESP chip (USB-Serial-JTAG / TinyUSB CDC)


def detect_link(device):
    """Return 'usb' when the device is the native USB port of the bridge, 'uart' for a
    serial port or USB-UART adapter, or None when it is not a local serial device (e.g. UDP)."""
    if not os.path.exists(device):
        return None
    path = os.path.realpath(device) # resolve /dev/serial/by-id/... symlinks
    for port in list_ports.comports():
        if os.path.realpath(port.device) == path:
            return 'usb' if port.vid == ESPRESSIF_USB_VID else 'uart'
    return 'uart'


def check_image(image):
    """Basic sanity check of a firmware image (not the merged/factory image)."""
    if len(image) < 24 or image[0] != ESP_IMAGE_MAGIC:
        raise SystemExit("error: not a valid firmware image (magic byte 0x%02X)" % (image[0] if image else 0))
    chip_id = struct.unpack_from('<H', image, 12)[0]
    if chip_id not in ESP_CHIP_IDS:
        raise SystemExit("error: firmware image is for chip id 0x%04X, the bridge uses %s" %
                         (chip_id, " or ".join(ESP_CHIP_IDS.values())))
    print("Firmware image: %d bytes, %d segments, chip %s" % (len(image), image[1], ESP_CHIP_IDS[chip_id]))
    return ESP_CHIP_IDS[chip_id]


def print_progress(done, total, start=[None]):
    if start[0] is None:
        start[0] = time.time()
    elapsed = max(time.time() - start[0], 1e-3)
    sys.stdout.write("\rUploading: %5.1f%%  %7d/%d bytes  %5.1f kB/s" %
                     (100.0 * done / total, done, total, done / elapsed / 1000.0))
    sys.stdout.flush()


def reboot(master):
    master.mav.command_long_send(master.target_system, master.target_component,
                                 mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN, 0,
                                 1, 0, 0, 0, 0, 0, 0)
    ack = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
    if ack is None or ack.result != mavutil.mavlink.MAV_RESULT_ACCEPTED:
        print("warning: reboot command not acknowledged; power cycle the bridge to start the new firmware")
    else:
        print("Bridge is rebooting")


def format_version(version):
    """Decode the firmware version, the build date as decimal YYMMDDHHMM
    into YYYYMMDD-HHMM"""
    if version == 0:
        return "unknown"
    digits = "%010d" % version
    return "20%s-%s" % (digits[:6], digits[6:])


def read_info(master, timeout=2.0, retries=3):
    """Request the AUTOPILOT_VERSION message from the bridge (MAV_CMD_REQUEST_MESSAGE)."""
    for _ in range(retries):
        master.mav.command_long_send(master.target_system, master.target_component,
                                     mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE, 0,
                                     mavutil.mavlink.MAVLINK_MSG_ID_AUTOPILOT_VERSION, 0, 0, 0, 0, 0, 0)
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = master.recv_match(type=['COMMAND_ACK', 'AUTOPILOT_VERSION'], blocking=True,
                                    timeout=deadline - time.time())
            if msg is None:
                break
            if msg.get_type() == 'AUTOPILOT_VERSION':
                return msg
            if (msg.command == mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE and
                    msg.result != mavutil.mavlink.MAV_RESULT_ACCEPTED):
                raise SystemExit("error: bridge refused the version request (result %d)" % msg.result)
    raise SystemExit("error: no version information received from the bridge")


def print_info(info):
    if info.vendor_id == BRIDGE_VENDOR_ID:
        model = BRIDGE_MODELS.get(info.product_id, "unknown model %d" % info.product_id)
    else:
        model = "unknown (vendor 0x%04X, product %d)" % (info.vendor_id, info.product_id)
    print("Model:            %s" % model)
    print("Hardware version: %d" % info.board_version)
    print("Firmware version: %s" % format_version(info.flight_sw_version))
    # serial number as text
    serial = (bytes(info.uid2) + info.uid.to_bytes(8, 'big')).rstrip(b'\0').decode('ascii', errors='replace')
    print("Serial number:    %s" % (serial or "unknown"))


def main():
    parser = argparse.ArgumentParser(description="Upload firmware to a DroneScout Bridge via MAVLink FTP")
    parser.add_argument("firmware", nargs="?", help="firmware image (.bin)")
    parser.add_argument("--device", default=config.interface, help="serial interface (default: %(default)s)")
    parser.add_argument("--baudrate", type=int, default=config.baudrate, help="baudrate (default: %(default)s)")
    parser.add_argument("--window", type=int, default=4, help="number of outstanding write requests (default: %(default)s)")
    parser.add_argument("--timeout", type=float, default=1.0, help="reply timeout in seconds (default: %(default)s)")
    parser.add_argument("--retries", type=int, default=10, help="maximum retries per block (default: %(default)s)")
    parser.add_argument("--no-reboot", action="store_true", help="do not reboot the bridge after the upload")
    parser.add_argument("--reboot-only", action="store_true", help="only reboot the bridge, no firmware upload")
    parser.add_argument("--info", action="store_true", help="only read the firmware version and bridge model")
    args = parser.parse_args()

    if args.reboot_only or args.info:
        if args.firmware or args.no_reboot or (args.reboot_only and args.info):
            parser.error("--reboot-only and --info cannot be combined with each other, a firmware file or --no-reboot")
    elif not args.firmware:
        parser.error("a firmware file is required (or use --reboot-only or --info)")
    else:
        with open(args.firmware, "rb") as f:
            image = f.read()
        image_chip = check_image(image)

    # the native USB port of the bridge only outputs data; MAVLink commands are not received
    if detect_link(args.device) == 'usb':
        raise SystemExit("error: %s is the native USB port of the bridge, which only sends data.\n"
                         "Connect the bridge via its UART interface (e.g. a USB-UART adapter)." % args.device)

    master = mavutil.mavlink_connection(args.device, args.baudrate)
    print("Waiting for heartbeat on %s..." % args.device)
    heartbeat = master.wait_heartbeat(timeout=10)
    if heartbeat is None:
        raise SystemExit("error: no heartbeat received from the bridge")
    # pymavlink only takes the ids from heartbeats it considers a vehicle, which the bridge is not
    master.target_system = heartbeat.get_srcSystem()
    master.target_component = heartbeat.get_srcComponent()
    print("Bridge found: system %d component %d" % (master.target_system, master.target_component))

    if args.reboot_only:
        reboot(master)
        return
    if args.info:
        print_info(read_info(master))
        return

    # the bridge also rejects an image for another chip, but only after the whole upload
    info = read_info(master)
    if info.vendor_id != BRIDGE_VENDOR_ID or info.product_id not in BRIDGE_CHIPS:
        raise SystemExit("error: unknown bridge model (vendor 0x%04X, product %d)" % (info.vendor_id, info.product_id))
    if BRIDGE_CHIPS[info.product_id] != image_chip:
        raise SystemExit("error: firmware image is for %s, but the %s uses %s" %
                         (image_chip, BRIDGE_MODELS[info.product_id], BRIDGE_CHIPS[info.product_id]))
    print("Bridge model:   %s" % BRIDGE_MODELS[info.product_id])

    ftp = MavFtp(master, args.timeout)
    try:
        ftp.request(OP_RESET_SESSIONS)
        print("Erasing firmware partition on the bridge...")
        # the bridge erases the whole OTA partition first, which takes a few seconds
        reply = ftp.request(OP_CREATE_FILE, data=FIRMWARE_PATH.encode(), timeout=10, retries=3)
        ftp.session = reply.session

        stats = ftp.write_file(image, max(1, args.window), args.retries, print_progress)
        print()
        blocks = (len(image) + MAX_DATA - 1) // MAX_DATA
        print("Sent %d blocks for %d needed, %d rewinds after a NAK, %d after a timeout" %
              (stats['sent'], blocks, stats['naks'], stats['timeouts']))
        if stats['rtt_n']:
            print("Reply time: average %.1f ms, maximum %.1f ms" %
                  (1000 * stats['rtt_sum'] / stats['rtt_n'], 1000 * stats['rtt_max']))

        # closing the session makes the bridge validate the image and select it for the next boot
        ftp.request(OP_TERMINATE_SESSION, timeout=10)
        print("Firmware validated and activated by the bridge")
    except FtpError as e:
        print()
        raise SystemExit("error: %s" % e)

    if not args.no_reboot:
        reboot(master)


if __name__ == "__main__":
    main()
