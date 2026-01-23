"""Convert an SVG to a transparent PNG using cairosvg.

Usage:
  python tools/svg_to_png.py public/logo-bank-dark.svg public/logo-bank-dark.png --width 880 --height 192

Requires: pip install cairosvg
"""
import sys
import argparse
from pathlib import Path

try:
    import cairosvg
except Exception as e:
    print("cairosvg is required. Install with: python -m pip install cairosvg")
    raise


def convert(src: Path, dst: Path, width: int | None = None, height: int | None = None):
    args = {}
    if width:
        args['output_width'] = width
    if height:
        args['output_height'] = height
    dst.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(url=str(src), write_to=str(dst), **args)
    print(f"Wrote {dst}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('src', help='Source SVG path')
    p.add_argument('dst', help='Destination PNG path')
    p.add_argument('--width', type=int, help='Output width in px')
    p.add_argument('--height', type=int, help='Output height in px')
    args = p.parse_args()
    convert(Path(args.src), Path(args.dst), args.width, args.height)
