import csv
import os
from enum import Enum
from datetime import datetime, timezone
from bitstruct import *

from modules import odid # opendroneID functions
from modules import rid  # OPEN_DRONE_ID_RADIO_RX_INFORMATION definitions

RX_HEADER = ['RadioTechnology', 'MAC', 'Channel', 'RSSI', 'Counter', 'ReceiverID', 'Brand', 'Model']

def open_csv(log_path):

    # no colons or spaces in the filename; colons are not allowed on Windows
    filename = os.path.join(log_path, datetime.now(tz=timezone.utc).strftime('%Y-%m-%d_%H-%M-%S') + '_remoteID_log.csv')
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        #write header
        csv_writer.writerow(
         ['Detection Time'] + ['BasicID'] + ['IDType'] + ['UAType']
         + ['Latitude'] + ['Longitude'] + ['AltitudeGeo'] + ['Height']
         + ['OperatorLatitude'] + ['OperatorLongitude'] + ['OperatorAltitudeGeo']
         + ['OperatorID']
         + RX_HEADER
         )
    return filename

def rx_columns(rx):
    # returns the RX information columns, or empty columns if no RX info is available
    if rx is None:
        return [''] * len(RX_HEADER)

    tech = rid.enums['MAV_ODID_RADIO_TECHNOLOGY'].get(rx.radio_technology)
    tech_name = tech.name.replace('MAV_ODID_RADIO_TECHNOLOGY_', '') if tech else str(rx.radio_technology)

    mac_techs = (rid.MAV_ODID_RADIO_TECHNOLOGY_BLE_LEGACY, rid.MAV_ODID_RADIO_TECHNOLOGY_BLE_LR,
                 rid.MAV_ODID_RADIO_TECHNOLOGY_WLAN_BEACON, rid.MAV_ODID_RADIO_TECHNOLOGY_WLAN_NAN)
    mac = ':'.join('%02X' % b for b in rx.id_or_mac[:6]) if rx.radio_technology in mac_techs else ''

    channel = '' if rx.channel == 0 else rx.channel
    rssi = '' if rx.rssi == 127 else rx.rssi

    return [tech_name, mac, channel, rssi, rx.counter, rx.receiver_id, rx.brand, rx.model]

def write_csv(payload, size, filename, rx=None):

    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        Detection_Time = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + " UTC"

        pack = odid.decode_message_pack(payload, size)
        basicID = pack.get(odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_BASIC_ID, {})
        location = pack.get(odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_LOCATION, {})
        system = pack.get(odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_SYSTEM, {})
        operatorID = pack.get(odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_OPERATOR_ID, {})

        csv_writer.writerow([Detection_Time,
            basicID.get('uas_id', ''), basicID.get('id_type', ''), basicID.get('ua_type', ''),
            location.get('latitude', ''), location.get('longitude', ''), location.get('altitude_geo', ''), location.get('height', ''),
            system.get('operator_latitude', ''), system.get('operator_longitude', ''), system.get('operator_altitude', ''),
            operatorID.get('operator_id', '')] + rx_columns(rx))
