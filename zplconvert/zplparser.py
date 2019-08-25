"""
Convert ZPL image back to regular image.
"""

import re
import sys
import argparse
from cStringIO import StringIO
from PIL import Image

GFA_MATCHER = re.compile(r"\^GFA,([1-9][0-9]*),([1-9][0-9]*),([1-9][0-9]*),([^\^]+)\^FS")

def _hex_nibble_to_bytes(value):
    """
    Convert ZPL byte to image bytes.
    """
    val = int(value, 16)
    return (('\x00' if val & 8 == 8 else '\xff') +
            ('\x00' if val & 4 == 4 else '\xff') +
            ('\x00' if val & 2 == 2 else '\xff') +
            ('\x00' if val & 1 == 1 else '\xff'))

def zpl_parse(filename):
    """
    Convert a ZPL file back to an image.
    """

    # pylint: disable=too-many-locals,too-many-statements

    if not filename:
        raise ValueError("No filename given, or empty")

    source = sys.stdin if filename == '-' else open(filename)
    data = source.read()

    # Find start of an image
    match = GFA_MATCHER.match(data)

    if not match:
        raise ValueError("Could not find ZPL image")

    # Calculate image size
    total = int(match.group(1))
    width_bytes = int(match.group(3))
    height = total / width_bytes
    width = width_bytes * 8
    bytecount = width * height

    print "Calculated image size: %d x %d" % (width, height)
    print "Expected byte count: %d" % bytecount

    # Convert length multiplier to character code
    # G - Y = 1 - 19, g - z = 20 - 400
    multiplier = dict([(chr(ord('F') + i), i) for i in xrange(1, 20)] + \
                      [(chr(ord('f') + i), 20 * i) for i in xrange(1, 21)])

    # Read byte by byte
    row = 0
    col = 0
    counter = 0
    nextrow = False
    result = ""
    rowdata = ""
    lastrow = ""
    for char in match.group(4):
        # Continue current line until the end with white
        if char == ',':
            rowdata += '\xff' * (width - col)
            nextrow = True

        # Continue current line until the end with black
        elif char == '!':
            rowdata += '\x00' * (width - col)
            nextrow = True

        # Repeat last row
        elif char == ':':
            rowdata = lastrow
            nextrow = True

        # Counter byte(s)
        elif char in multiplier:
            counter += multiplier[char]

        # Regular bytes
        else:
            bytedata = _hex_nibble_to_bytes(char)
            rowdata += bytedata * (counter or 1)
            col += (counter or 1) * 4
            counter = 0
            if col == width:
                nextrow = True

        if nextrow:
            result += rowdata
            lastrow = rowdata
            rowdata = ""
            nextrow = False
            col = 0
            row += 1

    assert row == height, "Image height does not match"
    assert len(result) == bytecount, "Parsed byte count does not match"

    # Create new image from data
    image = Image.frombytes('L', (width, height), result).convert('1')

    return image

def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Parse ZPL image back to image.")
    parser.add_argument('--format', '-f',
                        help="Image format, overrides provided filename extension")
    parser.add_argument('--output', '-o',
                        help="Output filename, or stdout if not defined")
    parser.add_argument('--show', '-s', action='store_true',
                        help="Show result image")
    parser.add_argument('filename',
                        help="Source filename, or '-' for stdin")

    return parser.parse_args()

def main():
    """
    Main entrypoint.
    """

    args = parse_args()

    if not args.format and not args.output and not args.show:
        print >> sys.stderr, "Either filename or image format must be provided"
        return 1

    image = zpl_parse(args.filename)

    if args.show:
        image.show()

    if args.format or args.output:
        output = args.output or StringIO()
        image.save(output, format=args.format)
        if not args.output:
            print output.getvalue()

    return 0

if __name__ == '__main__':
    sys.exit(main())
