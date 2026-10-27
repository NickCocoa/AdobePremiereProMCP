#!/usr/bin/env python3
"""Put a reference frame and a test render side by side (plus an optional difference view).

Usage: python3 compare.py REFERENCE.png RENDER.png OUT.jpg [--label "step 3: plants"] [--diff]

The render is scaled/cropped to the reference's aspect ratio so composition is comparable.
Read OUT.jpg and list concrete differences (framing, lens, light direction and colour, density,
scale of plants/rocks, contrast, haze) before moving to the next build step.
"""
import argparse

from PIL import Image, ImageChops, ImageDraw, ImageOps


def fit(img, size):
    return ImageOps.fit(img.convert("RGB"), size, method=Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("render")
    ap.add_argument("out")
    ap.add_argument("--label", default="")
    ap.add_argument("--diff", action="store_true", help="add a third panel: amplified difference")
    ap.add_argument("--height", type=int, default=540)
    args = ap.parse_args()

    ref = Image.open(args.reference).convert("RGB")
    w = round(ref.width * args.height / ref.height)
    size = (w, args.height)
    panels = [("REFERENCE", fit(ref, size)), ("RENDER", fit(Image.open(args.render), size))]
    if args.diff:
        d = ImageChops.difference(panels[0][1], panels[1][1])
        panels.append(("DIFFERENCE x3", d.point(lambda v: min(255, v * 3))))

    bar = 36
    sheet = Image.new("RGB", (w * len(panels) + 8 * (len(panels) - 1), args.height + bar), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    for i, (name, img) in enumerate(panels):
        x = i * (w + 8)
        sheet.paste(img, (x, bar))
        draw.text((x + 8, 10), name, fill=(235, 235, 235))
    if args.label:
        draw.text((sheet.width - 8 - 7 * len(args.label), 10), args.label, fill=(255, 200, 80))
    sheet.save(args.out, quality=90)
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
