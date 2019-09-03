#!/usr/bin/env python

"""
Helper utility for using the ZPL converter.
"""

import argparse
from zplconvert import ZPLConvert

def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Convert image to ZPL format.",
                                     epilog="The higher the black pixel threshold, "
                                     "the more of the image is considered black.")
    compress = parser.add_mutually_exclusive_group(required=False)
    compress.add_argument('--compress', '-c', action='store_true', default=True,
                          help="Compress the result image (default yes)")
    compress.add_argument('--no-compress', '-n', action='store_false',
                          dest='compress', help="Do not compress the result")
    parser.add_argument('--position', '-p', help="Add position header (x,y)")
    convert = parser.add_mutually_exclusive_group(required=False)
    convert.add_argument('--threshold', '-t', default=128, type=int,
                         help="Set black pixel threshold (default 128)")
    convert.add_argument('--dither', '-d', action='store_true',
                         help="Dither the image instead using a hard limit")
    parser.add_argument('--label', '-l', action='store_true',
                        help="Add header and footer for a complete ZPL label")
    parser.add_argument('--output', '-o',
                        help="Output filename, or stdout if not defined")
    parser.add_argument('--upload', '-u',
                        help="Return data suitable for direct upload")
    parser.add_argument('filename', help="Source filename, or '-' for stdin")

    return parser.parse_args()

def main():
    """
    Main entrypoint.
    """

    # Read args and create converter
    args = parse_args()
    converter = ZPLConvert(args.filename)
    converter.set_compress_hex(args.compress)
    converter.set_black_threshold(args.threshold)
    converter.set_dither(args.dither)

    # Set position
    # pylint: disable=invalid-name
    x, y = None, None
    if args.position:
        x, y = (int(val) for val in args.position.split(','))

    if args.upload:
        result = converter.convert_for_upload(args.upload)
    else:
        result = converter.convert(label=args.label, x=x, y=y)

    # Write result to file or to stdout
    if args.output:
        with open(args.output, 'wb') as out:
            out.write(result)
    else:
        print result

if __name__ == '__main__':
    main()
