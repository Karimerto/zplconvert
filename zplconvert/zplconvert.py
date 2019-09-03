"""
Converter for generating ZPL images.
"""

import sys
from cStringIO import StringIO
from PIL import Image

def _int_to_hex(value, upper=False):
    """
    Convert int value to hex.
    """
    result = ('0' + hex(value)[2:])[-2:]
    return result.upper() if upper else result

def _get_compress(counter, char):
    """
    Get compressed bytes for a character.
    """
    retval = ""
    if counter > 20:
        mult = (counter / 20) * 20
        rest = (counter % 20)
        retval = ZPLConvert.multiplier[mult]
        if rest != 0:
            retval += ZPLConvert.multiplier[rest]
    # Add multiplier only if counter is larger than 2
    elif counter > 2:
        retval = ZPLConvert.multiplier[counter]
    # Repeat twice, if necessary
    elif counter == 2:
        retval = char

    # Always add the actual character
    return retval + char

class ZPLConvert(object):
    """
    Convert any image to ZPL representation.
    """

    # pylint: disable=no-self-use,invalid-name

    # Convert length multiplier to character code
    # G - Y = 1 - 19, g - z = 20 - 400
    multiplier = dict([(i, chr(ord('F') + i)) for i in xrange(1, 20)] + \
                      [(20 * i, chr(ord('f') + i)) for i in xrange(1, 21)])

    def __init__(self, filename=None):
        self._filename = filename
        self._compress = False
        self._threshold = 128
        self._total = 0
        self._width_bytes = 0
        self._dither = False

    def set_compress_hex(self, compress=True):
        """
        Compress hex result or not.
        """
        self._compress = compress

    def set_black_threshold(self, threshold):
        """
        Set black pixel threshold.
        """
        if threshold < 0 or threshold > 255:
            raise ValueError("Black threshold must be between 0 and 255 (%d given)" % threshold)
        self._threshold = threshold

    def set_dither(self, dither):
        """
        Dither the image instead of using a hard limit.
        """
        self._dither = dither

    def convert_for_upload(self, targetfile, filename=None):
        """
        Returns code suitable for uploading graphics directly on the printer.
        """
        filename = filename or self._filename
        if not filename:
            raise ValueError("No filename given")

        # Create image body
        body = self._create_body(filename)

        return self._get_upload_header(targetfile) + body

    def convert(self, filename=None, label=False, x=None, y=None):
        """
        Convert a file to ZPL.
        Returns a full ZPL-compatible image with optional headers.
        """
        filename = filename or self._filename
        if not filename:
            raise ValueError("No filename given")

        # Create image body
        body = self._create_body(filename)

        # Compress it, if selected
        if self._compress:
            body = self._compress_hex(body)

        # Add header and footer, with optional coordinates
        image = self._get_header(len(body), x, y) + body + self._get_footer()

        # Add label start and stop bytes
        if label:
            image = "^XA\n" + image + "\n^XZ\n"

        return image

    def _get_header(self, size, x=None, y=None):
        """
        Get header, with optional positioning.
        """
        pos = ""
        if x is not None and y is not None:
            pos = "^FO{x},{y}".format(x=x, y=y)
        return pos + "^GFA,{size},{total},{width_bytes},".format(
            size=size, total=self._total, width_bytes=self._width_bytes)

    def _get_footer(self):
        """
        Get footer bytes.
        """
        return "^FS"

    def _get_upload_header(self, targetfile):
        """
        Returns the graphics upload header.
        """
        # Target file must include location, if not then assume RAM
        if ':' not in targetfile:
            targetfile = 'R:' + targetfile

        return "~DG{targetfile},{total},{width_bytes},".format(
            targetfile=targetfile, total=self._total, width_bytes=self._width_bytes)

    def _get_bw_image(self, filename):
        """
        Convert image to black and white.
        Also update image size.
        """

        source = StringIO(sys.stdin.read()) if filename == '-' else filename

        # Load image and get dimensions
        image = Image.open(source)
        width, height = image.size

        if self._dither:
            # Dither image by converting to mode '1' and invert result
            bwimage = image.convert('1').point(lambda x: 255 - x)
        else:
            # Convert to black and white (via grayscale)
            # conv = lambda x: 255 if x >= self._threshold else 0
            conv = lambda x: 0 if x >= self._threshold else 255
            bwimage = image.convert('L').point(conv, mode='1')

        # Calculate image size
        self._width_bytes = (width + 7) / 8
        self._total = self._width_bytes * height

        return bwimage

    def _create_body(self, filename):
        """
        Create uncompressed body.
        Filename can be '-' for reading data from stdin.
        """

        bwimage = self._get_bw_image(filename)

        # Convert bytes to simple hex
        idx = 0
        result = []
        row = ""
        for char in bwimage.tobytes():
            row += _int_to_hex(ord(char))
            idx += 1
            if idx == self._width_bytes:
                result.append(row)
                idx = 0
                row = ""

        return '\n'.join(result) + '\n'

    def _compress_hex(self, body):
        """
        Compress the hex result.
        """
        last_line = ""
        line = ""
        result = ""
        counter = 1
        prev = ''
        first_char = True

        for char in body:
            if first_char:
                prev = char
                first_char = False
                continue

            # New line, add result of previously processed line
            if char == '\n':
                # Continue white
                if prev == '0':
                    line += ','
                # Continue black
                elif prev == 'f':
                    line += '!'
                # Repeat last character
                else:
                    line += _get_compress(counter, prev)

                # Reset line
                counter = 1
                first_char = True
                # Add new line or repeat previous line
                result += ':' if line == last_line else line
                last_line = line
                line = ""
                continue

            # Process bytes
            if prev == char:
                counter += 1
            else:
                line += _get_compress(counter, prev)
                counter = 1
                prev = char

        return result
