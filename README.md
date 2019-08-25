# ZPLConvert

ZPLConvert provides a simple tool for converting images to [ZPL](https://www.zebra.com/content/dam/zebra/manuals/printers/common/programming/zpl-zbi2-pm-en.pdf) compatible strings.

## Installation

    pip install zplconvert

## Requirements

ZPLConvert needs one of the following:

 * [PIL](http://www.pythonware.com/products/pil/) or
 * [Pillow](https://pillow.readthedocs.io/)

## Example use

Included is a simple main program that can be used from the command line to convert images.

    zplconvert zebra_logo.png

will read `zebra_logo.png`, convert it to black and white, then to compressed ZPL Ascii and print the result to stdout.

If you want more control, you can use the following flags:

Flag     | Description
---------|------------
`--no-compress` | Do not compress the result image (useful for debugging).
`--position x,y` | Add a positional header to the output.
`--threshold value` | Set black pixel threshold (0-255, default 128).
`--dither` | Dither the result instead of hard limit for black pixels.
`--label` | Add header and footer needed for a complete ZPL label. This allows the result to be sent directly to a printer (e.g. with `curl`).
`--output filename` | Write result to file instead of `stdout`.

## Contributing

Bug reports and pull requests are welcome on GitHub at https://github.com/Karimerto/zplconvert.

## License

This source is released under the standard [MIT License](https://opensource.org/licenses/MIT)

## Zebra logo

![Zebra Logo](zplconvert/zebra_logo.png?raw=true)

The Zebra Logo was copied from [Zebra Design](https://www.zebra.com/us/en/design.html).
