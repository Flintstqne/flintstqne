"""
Turn a photo into ASCII art for the profile card.

    python photo_to_ascii.py PHOTO.jpg --rotate 90 --crop 0.47 0.12 0.86 0.86 --cols 66

--rotate    degrees clockwise to turn the photo upright (default 0)
--crop      crop box as fractions of the ROTATED image: left top right bottom
--cols      characters per row (default 66)
--vignette  0 to 1, how strongly the background fades out (default 0.85)

Writes ascii_dark.txt and ascii_light.txt. Both draw dark areas of the photo with
dense characters, so the subject stands out against the faded background on either
card theme. The photo itself is not stored in the repo.
"""
import argparse

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

RAMP = ' .,:;i1tfLCG08@'  # sparse to dense


def vignette_mask(size, strength):
    """White in the middle, fading to black at the edges (soft ellipse)."""
    w, h = size
    mask = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((w * 0.04, h * 0.02, w * 0.96, h * 0.98), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=min(w, h) * 0.12))
    return mask.point(lambda v: int(255 * (1 - strength) + v * strength))


def convert(path, rotate, crop, cols, strength):
    im = ImageOps.exif_transpose(Image.open(path)).convert('L')
    if rotate:
        im = im.rotate(-rotate, expand=True)  # PIL turns counter-clockwise, so negate
    w, h = im.size
    l, t, r, b = crop
    im = im.crop((int(l * w), int(t * h), int(r * w), int(b * h)))
    im = ImageOps.autocontrast(im, cutoff=1)
    im = im.filter(ImageFilter.UnsharpMask(radius=im.width / 60, percent=220, threshold=2))
    # Fade the background toward white so only the subject gets dense characters.
    white = Image.new('L', im.size, 255)
    im = Image.composite(im, white, vignette_mask(im.size, strength))
    im = ImageOps.autocontrast(im, cutoff=0.5)
    rows = max(1, round(cols * im.height / im.width * 0.5))  # characters are ~2x taller than wide
    im = im.filter(ImageFilter.GaussianBlur(radius=max(1, im.width / cols / 3)))
    im = im.resize((cols, rows), Image.LANCZOS)
    dense_first = RAMP[::-1]  # dark pixel -> index 0 -> densest character
    return [''.join(dense_first[im.getpixel((x, y)) * (len(RAMP) - 1) // 255] for x in range(cols))
            for y in range(rows)]


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('photo')
    ap.add_argument('--rotate', type=int, default=0)
    ap.add_argument('--crop', type=float, nargs=4, default=[0, 0, 1, 1])
    ap.add_argument('--cols', type=int, default=66)
    ap.add_argument('--vignette', type=float, default=0.85)
    a = ap.parse_args()
    lines = convert(a.photo, a.rotate, a.crop, a.cols, a.vignette)
    for name in ('ascii_dark.txt', 'ascii_light.txt'):
        with open(name, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        print(f'wrote {name}: {a.cols} cols x {len(lines)} rows')
