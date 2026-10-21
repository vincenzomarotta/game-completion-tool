# og.png (1200x630 link preview) + apple-touch-icon.png, same mark as favicon.svg.
# Needs Pillow and Bricolage Grotesque (OFL, github.com/google/fonts ofl/bricolagegrotesque) saved as fonts/bricolage.ttf.
import sys
from PIL import Image, ImageDraw, ImageFont
R = sys.argv[1]
BG, INK, DIM, TRACK, AMBER = "#1e2029", "#ecebe6", "#9a9caa", "#3a3d4b", "#f0b45a"
def mark(size):
    k = 4; S = size * k; im = Image.new("RGBA", (S, S)); d = ImageDraw.Draw(im)
    u = S / 64
    d.rounded_rectangle((0, 0, S - 1, S - 1), 14 * u, fill=BG)
    w = round(6 * u); box = (12 * u - w / 2, 12 * u - w / 2, 52 * u + w / 2, 52 * u + w / 2)  # PIL strokes inside the box
    d.ellipse(box, outline=TRACK, width=w)
    d.arc(box, -90, -90 + 270, fill=INK, width=w)
    for a in (-90, 180):  # round caps
        import math; r = 20 * u; cx = cy = 32 * u
        x, y = cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)); d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=INK)
    d.line([(24 * u, 32 * u), (30 * u, 38 * u), (41 * u, 26 * u)], fill=AMBER, width=round(5 * u), joint="curve")
    for x, y in [(24, 32), (41, 26)]: d.ellipse(((x - 2.5) * u, (y - 2.5) * u, (x + 2.5) * u, (y + 2.5) * u), fill=AMBER)
    return im.resize((size, size), Image.LANCZOS)
def font(sz, wght):
    f = ImageFont.truetype("fonts/bricolage.ttf", sz); f.set_variation_by_axes([min(96, sz), wght, 100]); return f
og = Image.new("RGBA", (1200, 630), BG)
og.alpha_composite(mark(150), (90, 90))
d = ImageDraw.Draw(og)
d.text((86, 270), "Game Completion", font=font(96, 800), fill=INK)
d.text((86, 370), "Tool", font=font(96, 800), fill=INK)
d.text((90, 500), "Load your save, see what's left for 100% and where to find it.", font=font(34, 500), fill=DIM)
d.text((90, 548), "Death's Door · Hollow Knight · Silksong · Tunic", font=font(30, 500), fill=AMBER)
x = 1110
for f in ["hornet.png", "knight.png"]:
    ic = Image.open(f"{R}/{f}").convert("RGBA"); ic = ic.resize((ic.width * 2, ic.height * 2), Image.LANCZOS)
    x -= ic.width + 30; og.alpha_composite(ic, (x, 120))
og.convert("RGB").save(f"{R}/og.png", optimize=True)
mark(180).save(f"{R}/apple-touch-icon.png", optimize=True)
