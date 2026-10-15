# logs packets that could not be decoded to a CSV file, e.g. to detect corruption on the USB link
import csv
import os
from datetime import datetime, timezone

HEADER = ['Time', 'MessageType', 'Reason', 'Length', 'Data']

def open_csv(log_path):
    # no colons or spaces in the filename; colons are not allowed on Windows
    filename = os.path.join(log_path, datetime.now(tz=timezone.utc).strftime('%Y-%m-%d_%H-%M-%S') + '_decode_errors.csv')
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        csv.writer(csvfile, quoting=csv.QUOTE_NONNUMERIC).writerow(HEADER)
    return filename

def write_csv(filename, msg_type, reason, data=b''):
    # data is written as hex so the raw bytes can be inspected afterwards
    data = bytes(data)
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        Detection_Time = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + " UTC"
        csv.writer(csvfile, quoting=csv.QUOTE_NONNUMERIC).writerow(
            [Detection_Time, msg_type, reason, len(data), data.hex(' ')])
