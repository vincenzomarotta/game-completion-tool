# Compose the Silksong map from Game_Map_Hornet room sprites.
# Output: ss_map.webp + ss_rooms.json {scene: [x, y, area, w, h]} (x/y = room position in image px, w/h = sprite size in map units).
import json, sys, glob, warnings, re
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from ss_env import *
from PIL import Image

SCALE = 100
files = [AA + r"\maps_assets_all.bundle"] + glob.glob(AA + r"\atlases_assets_assets\sprites\_atlases\hornet_map*.bundle")
env = UnityPy.load(*files)

def tr(g):
    c = comps(g)
    return (c.get("Transform") or c.get("RectTransform"))[0].read()

gm = next(o.read() for o in env.objects if o.type.name == "GameObject" and o.peek_name() == "Game_Map_Hornet")
placed = []
SKIP = {"Pan Audio Loop", "Main Quest Pins", "Compass Icon", "Shade Pos", "Map Markers", "Flea Tracker Markers"}
for at in [c.read() for c in tr(gm).m_Children]:
    ago = at.m_GameObject.read()
    if ago.m_Name in SKIP:
        continue
    for rt in [c.read() for c in at.m_Children]:
        rgo = rt.m_GameObject.read()
        srs = comps(rgo).get("SpriteRenderer")
        if not srs:
            continue
        sr = srs[0].read()
        # Act 3 replacement rooms (destroyed/broken variants) would overlap the originals.
        if re.search(r"destroyed|broken", rgo.m_Name, re.I):
            continue
        # GameMapScene: fullSprite is the finished room art (the renderer holds the rough sketch).
        mbs = comps(rgo).get("MonoBehaviour") or []
        gms = next((m.read() for m in mbs if "fullSprite" in m.parse_as_dict()), None)
        ptr = gms.fullSprite if gms is not None and gms.fullSprite.path_id else sr.m_Sprite
        if not ptr.path_id:
            continue
        try:
            sp = ptr.read()
        except Exception as e:
            print("no sprite", rgo.m_Name, e); continue
        s = at.m_LocalScale
        x = at.m_LocalPosition.x + rt.m_LocalPosition.x * s.x
        y = at.m_LocalPosition.y + rt.m_LocalPosition.y * s.y
        placed.append((rgo.m_Name, x, y, sp, ago.m_Name, rt.m_LocalScale.x * s.x, rt.m_LocalScale.y * s.y))

print("rooms", len(placed))
boxes = []
for scene, x, y, sp, area, sx, sy in placed:
    w, h = sp.m_Rect.width / sp.m_PixelsToUnits * abs(sx), sp.m_Rect.height / sp.m_PixelsToUnits * abs(sy)
    px, py = sp.m_Pivot.x, sp.m_Pivot.y
    boxes.append((x - px * w, y - py * h, x + (1 - px) * w, y + (1 - py) * h, w, h))
minx = min(b[0] for b in boxes) - 1; maxx = max(b[2] for b in boxes) + 1
miny = min(b[1] for b in boxes) - 1; maxy = max(b[3] for b in boxes) + 1
W, H = int((maxx - minx) * SCALE), int((maxy - miny) * SCALE)
print("canvas", W, H)

TINT = {}  # area -> rgb, assigned from a fixed palette in area order
PALETTE = [(214, 196, 160), (190, 170, 200), (150, 190, 160), (200, 160, 140), (150, 175, 210), (210, 200, 130),
           (170, 210, 205), (220, 160, 180), (180, 180, 185), (160, 200, 120), (230, 190, 140), (140, 160, 200)]
canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
rooms = {}
for (scene, x, y, sp, area, sx, sy), (x0, y0, x1, y1, w, h) in zip(placed, boxes):
    r, g, b = TINT.setdefault(area, PALETTE[len(TINT) % len(PALETTE)])
    img = sp.image.convert("RGBA")
    if sx < 0: img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if sy < 0: img = img.transpose(Image.FLIP_TOP_BOTTOM)
    img = img.resize((max(1, round((x1 - x0) * SCALE)), max(1, round((y1 - y0) * SCALE))), Image.LANCZOS)
    lum, a = img.convert("L"), img.getchannel("A")
    img = Image.merge("RGBA", (lum.point(lambda v: v * r // 255), lum.point(lambda v: v * g // 255), lum.point(lambda v: v * b // 255), a))
    canvas.alpha_composite(img, (round((x0 - minx) * SCALE), round((maxy - y1) * SCALE)))
    rooms[scene] = [round((x - minx) * SCALE, 1), round((maxy - y) * SCALE, 1), area, round(w, 3), round(h, 3), round(sp.m_Pivot.x, 3), round(sp.m_Pivot.y, 3)]

canvas.save("ss_map.webp", quality=88, method=6)
json.dump({"scale": SCALE, "size": [W, H], "rooms": rooms}, open("ss_rooms.json", "w"))
print("saved")
