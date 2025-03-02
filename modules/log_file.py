import csv
from enum import Enum
from datetime import datetime, timezone
from bitstruct import *

from modules import odid # opendroneID functions

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
         )
    return filename

def write_csv(payload, size, filename):

    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        Detection_Time = datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " UTC"
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

        for x in range(size):
            RIDtype = payload[x*odid.ODID_MESSAGE_SIZE] >> 4
            if (odid.ODID_MESSAGETYPE(RIDtype) == odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_BASIC_ID):
                IDType = payload[x*odid.ODID_MESSAGE_SIZE + 1] >> 4
                UAType = payload[x*odid.ODID_MESSAGE_SIZE + 1] & 0x0F
                UASID = (payload[x*odid.ODID_MESSAGE_SIZE + 2: x*odid.ODID_MESSAGE_SIZE + 2 + odid.ODID_ID_SIZE])
                UASID = odid.clean_SN(bytes(UASID).decode('ascii'))

            if (odid.ODID_MESSAGETYPE(RIDtype) == odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_LOCATION):
                Latitude = float(struct.unpack('i', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 5: x*odid.ODID_MESSAGE_SIZE + 9])[0])/(10*1000*1000)
                Longitude = float(struct.unpack('i', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 9: x*odid.ODID_MESSAGE_SIZE + 13])[0])/(10*1000*1000)
                AltitudeGeo = struct.unpack('H', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 15:x*odid.ODID_MESSAGE_SIZE + 17])
                AltitudeGeo = (int(AltitudeGeo[0]) - int(2000))/2
                Height = struct.unpack('H', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 17:x*odid.ODID_MESSAGE_SIZE + 19])
                Height = (int(Height[0]) - int(2000))/2

            if (odid.ODID_MESSAGETYPE(RIDtype) == odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_SYSTEM):
                OperatorLatitude = float(struct.unpack('i', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 2: x*odid.ODID_MESSAGE_SIZE + 6])[0])/(10*1000*1000)
                OperatorLongitude = float(struct.unpack('i', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 6: x*odid.ODID_MESSAGE_SIZE + 10])[0])/(10*1000*1000)
                OperatorAltitudeGeo = struct.unpack('<h', bytes(payload)[x*odid.ODID_MESSAGE_SIZE + 18:x*odid.ODID_MESSAGE_SIZE + 20])
                OperatorAltitudeGeo = (int(OperatorAltitudeGeo[0]) - int(2000))/2

            if (odid.ODID_MESSAGETYPE(RIDtype) == odid.ODID_MESSAGETYPE.ODID_MESSAGETYPE_OPERATOR_ID):
                operatorID = payload[x*odid.ODID_MESSAGE_SIZE + 2:x*odid.ODID_MESSAGE_SIZE + 2 + odid.ODID_ID_SIZE]
                operatorID = odid.clean_string(bytes(operatorID).decode('ascii'))

        csv_writer.writerow([Detection_Time, UASID, IDType, UAType, Latitude, Longitude, AltitudeGeo, Height,
            OperatorLatitude, OperatorLongitude, OperatorAltitudeGeo, operatorID])
