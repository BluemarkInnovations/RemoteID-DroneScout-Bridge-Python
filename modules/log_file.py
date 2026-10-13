import csv
from enum import Enum
from datetime import datetime, timezone
from bitstruct import *

from modules import odid # opendroneID functions
from modules import rid  # OPEN_DRONE_ID_RADIO_RX_INFORMATION definitions

RX_HEADER = ['RadioTechnology', 'MAC', 'Channel', 'RSSI', 'Counter', 'ReceiverID', 'Brand', 'Model']

def open_csv(log_path):

    filename = log_path + '/' + datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + '_remoteID_log.csv'
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
        IDType = ''
        UAType = ''
        UASID = ''
        Latitude = ''
        Longitude = ''
        AltitudeGeo = ''
        Height = ''
        OperatorLatitude = ''
        OperatorLongitude = ''
        OperatorAltitudeGeo = ''
        TimeStamp = ''
        operatorID = ''

        for x in range(min(size, odid.ODID_PACK_MAX_MESSAGES)):
            RIDtype = payload[x*odid.ODID_MESSAGE_SIZE] >> 4
            if (RIDtype == odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_BASIC_ID):
                IDType = payload[x*odid.ODID_MESSAGE_SIZE + 1] >> 4
                UAType = payload[x*odid.ODID_MESSAGE_SIZE + 1] & 0x0F
                UASID = odid.clean_SN(odid.clean_id(payload[x*odid.ODID_MESSAGE_SIZE + 2: x*odid.ODID_MESSAGE_SIZE + 2 + odid.ODID_ID_SIZE]))

            if (RIDtype == odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_LOCATION):
                Latitude = float(struct.unpack('i', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 5: x*odid.ODID_MESSAGE_SIZE + 9])[0])/(10*1000*1000)
                Longitude = float(struct.unpack('i', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 9: x*odid.ODID_MESSAGE_SIZE + 13])[0])/(10*1000*1000)
                AltitudeGeo = struct.unpack('H', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 15:x*odid.ODID_MESSAGE_SIZE + 17])
                AltitudeGeo = (int(AltitudeGeo[0]) - int(2000))/2
                Height = struct.unpack('H', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 17:x*odid.ODID_MESSAGE_SIZE + 19])
                Height = (int(Height[0]) - int(2000))/2

            if (RIDtype == odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_SYSTEM):
                OperatorLatitude = float(struct.unpack('i', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 2: x*odid.ODID_MESSAGE_SIZE + 6])[0])/(10*1000*1000)
                OperatorLongitude = float(struct.unpack('i', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 6: x*odid.ODID_MESSAGE_SIZE + 10])[0])/(10*1000*1000)
                OperatorAltitudeGeo = struct.unpack('<h', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 18:x*odid.ODID_MESSAGE_SIZE + 20])
                OperatorAltitudeGeo = (int(OperatorAltitudeGeo[0]) - int(2000))/2

            if (RIDtype == odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_OPERATOR_ID):
                operatorID = odid.clean_id(payload[x*odid.ODID_MESSAGE_SIZE + 2:x*odid.ODID_MESSAGE_SIZE + 2 + odid.ODID_ID_SIZE])

        csv_writer.writerow([Detection_Time, UASID, IDType, UAType, Latitude, Longitude, AltitudeGeo, Height,
            OperatorLatitude, OperatorLongitude, OperatorAltitudeGeo, operatorID] + rx_columns(rx))
