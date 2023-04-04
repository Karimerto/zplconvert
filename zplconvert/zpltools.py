"""
Helpful ZPL tools.
"""
from __future__ import print_function

from builtins import hex
from builtins import object
import os
import re
import base64
import socket

SUPPORTED_FILETYPES = (
    # Extension, format, extension code
    ('bmp', 'B', 'B'), # Bitmap
    ('tte', 'B', 'E'), # TrueType Extension
    ('ttf', 'B', 'T'), # TrueType
    ('otf', 'B', 'T'), # OpenType
    ('png', 'P', 'P'), # PNG
    ('grf', 'A', 'G'), # Raw bitmap
    ('pcx', 'B', 'X'), # Paintbrush
    ('nrd', 'B', 'NRD'), # Non Readable File
    ('pac', 'B', 'PAC'), # Protected Access Credential
    ('wml', 'B', 'C'), # User define menu file
    ('htm', 'B', 'F'), # User define webpage file
    ('get', 'B', 'H'), # Printer feedback file
)

# Values:
# A = uncompressed (ZB64, ASCII)
# B = uncompressed (.TTE, .TTF, binary)
# P = portable network graphic (.PNG) - ZB64 encoded
# Default: a value must be specified

def _get_format(ext):
    """
    Get file format code.
    """
    ext = ext.lower()
    for row in SUPPORTED_FILETYPES:
        if row[0] in ext:
            return row[1]
    return None

def _get_extension(ext):
    """
    Get file extension code.
    """
    ext = ext.lower()
    for row in SUPPORTED_FILETYPES:
        if row[0] in ext:
            return row[2]
    return None

class PrinterError(Exception):
    """Base exception for Printer errors."""
    pass

class Printer(object):
    """
    Helper class for communicating with a printer.
    """

    def __init__(self, host, port=9100):
        """
        Initialize new printer.
        """
        self._host = host
        self._port = port
        self._ident = {}
        self._status = {}

    def send_command(self, command, read=False):
        """
        Send a command to printer, optionally waiting for a reply.
        """
        try:
            # Create a new connection each time, so printer is not kept busy
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self._host, self._port))
            sock.send(command)
            result = ""
            if read:
                # Read until printer sends 0x03 to signify end-of-reply
                # This is not the best method, as some replies are more than one
                while True:
                    data = sock.recv(32768)
                    result += data
                    if '\x03' in data:
                        break
            return result
        except socket.error as err:
            raise PrinterError(err)
        finally:
            sock.close()

    def get_host_identification(self):
        """
        Get printer identification data.
        """

        # Send command
        info = self.send_command("~HI", True)
        match = re.match(r"\x02(?P<model>[^,]+),(?P<version>[^,]+),(?P<dpm>[0-9]+),"
                          "(?P<memory>[0-9]+)KB,(?P<options>[^\x03]+)\x03", info)

        # If we get a valid response, parse data and convert memory and dpm to int
        if match:
            self._ident = match.groupdict()
            self._ident['dpm'] = int(self._ident['dpm'])
            self._ident['memory'] = int(self._ident['memory'])
        return self._ident

    def get_host_ram(self):
        """
        Get current and total amounts of RAM available.
        """

        # Send command
        info = self.send_command("~HM", True)
        match = re.match(r"\x02(?P<max>[0-9]+),(?P<total>[0-9]+),(?P<free>[0-9]+)\x03", info)

        # If we get a valid response, parse data and convert memory and dpm to int
        if match:
            values = match.groupdict()
            for key in values:
                values[key] = int(values[key])
            return values
        return None

    def get_host_status(self):
        """
        Get printer status data.
        """

        int_types = ('interface', 'label_length', 'num_formats', 'function_settings',
            'print_width_mode', 'labels_remaining', 'graphics_in_mem')
        bool_types = ('paper_out', 'pause', 'buffer_full', 'diagnostic_mode',
            'format_in_progress', 'corrupt_ram', 'under_temp', 'over_temp',
            'head_up', 'ribbon_out', 'thermal_transfer_mode', 'label_waiting',
            'static_ram')

        print_mode = {
            '0': 'Rewind',
            '1': 'Peel-Off',
            '2': 'Tear-Off',
            '3': 'Cutter',
            '4': 'Applicator',
            '5': 'Delayed cut',
            '6': 'Linerless Peel',
            '7': 'Linerless Rewind',
            '8': 'Partial Cutter',
            '9': 'RFID',
            'K': 'Kiosk',
            'S': 'Stream',
        }

        # Send command
        info = self.send_command("~HS", True)
        match = re.match(r"\x02(?P<interface>\d{3}),"
                        r"(?P<paper_out>\d),"
                        r"(?P<pause>\d),"
                        r"(?P<label_length>\d{4}),"
                        r"(?P<num_formats>\d{3}),"
                        r"(?P<buffer_full>\d),"
                        r"(?P<diagnostic_mode>\d),"
                        r"(?P<format_in_progress>\d),"
                         "000,"
                        r"(?P<corrupt_ram>\d),"
                        r"(?P<under_temp>\d),"
                        r"(?P<over_temp>\d)\x03\r\n"
                        r"\x02(?P<function_settings>\d{3}),"
                         "0,"
                        r"(?P<head_up>\d),"
                        r"(?P<ribbon_out>\d),"
                        r"(?P<thermal_transfer_mode>\d),"
                        r"(?P<print_mode>\w),"
                        r"(?P<print_width_mode>\d),"
                        r"(?P<label_waiting>\d),"
                        r"(?P<labels_remaining>\d+),"
                         "1,"
                        r"(?P<graphics_in_mem>\d{3})\x03\r\n"
                        r"\x02(?P<password>[^,]+),"
                        r"(?P<static_ram>\d)\x03", info)

        if match:
            status = match.groupdict()
            for key in int_types:
                status[key] = int(status[key])
            for key in bool_types:
                status[key] = bool(int(status[key]))
            status['print_mode_string'] = print_mode.get(status['print_mode'], 'Unknown')
            self._status = status
        return self._status

    def upload_file(self, source, targetfile):
        """
        Upload a file to Zebra printer, or output as string
        """

        from PyCRC.CRCCCITT import CRCCCITT

        with open(source) as infile:
            indata = infile.read()

            # Target file must include location, if not then assume RAM
            if ':' not in targetfile:
                targetfile = 'R:' + targetfile

            # Encode as base64
            b64data = base64.b64encode(indata)

            # Calculate and append CRC-16
            crc = hex(CRCCCITT().calculate(b64data))[2:]

            # Create data stream
            data = ':B64:{data}:{crc}'.format(data=b64data, crc=crc)

            # Get format and extension
            _, ext = os.path.splitext(source)
            fmt = _get_format(ext)
            extension = _get_extension(ext)

            # Setup the full command
            command = "~DY{targetfile},{fmt},{extension},{size},,{data}".format(
                targetfile=targetfile, fmt=fmt, extension=extension,
                size=len(b64data), data=data)

            if self._host is None:
                print(command)
            else:
                self.send_command(command)

    def upload_bounded_font(self, source, targetfile):
        """
        Upload bounded font to Zebra printer.
        """

        with open(source) as infile:
            indata = infile.read()

            # Target file must include location, if not then assume RAM
            if not targetfile:
                # Filename up to 8 characters
                name, _ = os.path.splitext(source)
                targetfile = 'R:' + name[:8].upper()

            elif ':' not in targetfile:
                targetfile = 'R:' + targetfile

            # Convert to two-digit hex string
            hexdata = ''.join(('0' + hex(ord(char))[2:])[-2:].upper() for char in indata)

            command = "~DT{targetfile},{size},{data}".format(
                targetfile=targetfile, size=len(indata), data=hexdata)

            if self._host is None:
                print(command)
            else:
                self.send_command(command)

    def upload_unbounded_font(self, source, targetfile):
        """
        Upload unbounded font to Zebra printer.
        """

        with open(source) as infile:
            indata = infile.read()

            # Target file must include location, if not then assume RAM
            if not targetfile:
                # Filename up to 8 characters
                name, _ = os.path.splitext(source)
                targetfile = 'R:' + name[:8].upper()

            elif ':' not in targetfile:
                targetfile = 'R:' + targetfile

            # Convert to two-digit hex string
            hexdata = ''.join(('0' + hex(ord(char))[2:])[-2:].upper() for char in indata)

            command = "~DU{targetfile},{size},{data}".format(
                targetfile=targetfile, size=len(indata), data=hexdata)

            if self._host is None:
                print(command)
            else:
                self.send_command(command)

    def map_font(self, identifier, font):
        """
        Map font to an identifier.
        """

        command = "\x02^CW{identifier},{font}\x03".format(
            identifier=identifier, font=font)
        self.send_command(command)
