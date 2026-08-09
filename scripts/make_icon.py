"""Generate the application icon (ICO for Windows, PNG for Android)."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

SIZES = [16, 24, 32, 48, 64, 128, 256]
FG = (37, 99, 235)
FG_DARK = (30, 64, 175)
BG = (14, 22, 48)
WHITE = (255, 255, 255)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    r = int(size * 0.20)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=BG)

    sw = max(2, size // 28)
    lw = size * 0.28
    lm = size * 0.13

    pts = {
        "green": [(lm + lw * 0.0, size * 0.78), (lm + lw * 0.25, size * 0.56), (lm + lw * 0.45, size * 0.62)],
        "blue": [(lm + lw * 0.45, size * 0.62), (lm + lw * 0.62, size * 0.40), (lm + lw * 0.82, size * 0.48)],
        "last": [(lm + lw * 0.82, size * 0.48), (lm + lw * 1.0, size * 0.30)],
    }
    d.line(pts["green"], fill=(34, 197, 94), width=sw)
    d.line(pts["blue"], fill=FG, width=sw)
    d.line(pts["last"], fill=FG_DARK, width=sw)

    for x, y in [pts["green"][0], pts["blue"][-1]]:
        pr = max(2, size // 26)
        d.ellipse((x - pr, y - pr, x + pr, y + pr), fill=WHITE)

    font_size = max(10, int(size * 0.16))
    try:
        from PIL import ImageFont

        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
    except Exception:  # noqa: BLE001
        font = None
    if font is not None:
        text = "SM"
        d.text((size * 0.5, size * 0.12), text, font=font, fill=WHITE, anchor="ma")

    return img


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)

    png_512 = ASSETS / "icon_512.png"
    draw_icon(512).save(png_512)
    print("wrote", png_512)

    ico = ASSETS / "icon.ico"
    img = draw_icon(256)
    img.save(ico, sizes=[(s, s) for s in SIZES])
    print("wrote", ico)


if __name__ == "__main__":
    main()
