# Compose the Silksong map from Game_Map_Hornet room sprites in the game's own colours, plus the game's area labels.
# Output: ss_map.webp, ss_rooms.json {scene: [x, y, areaKey, w, h, pivotX, pivotY]}, ss_labels.json.
import json, sys, glob, warnings, re, base64, html
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from ss_env import *
from PIL import Image
from Crypto.Cipher import AES

SCALE = 100
files = [AA + r"\maps_assets_all.bundle"] + glob.glob(AA + r"\atlases_assets_assets\sprites\_atlases\hornet_map*.bundle")
env = UnityPy.load(*files)
res = UnityPy.load(DATA + r"\resources.assets")

def sheet(lang, name):
    o = next(o for o in res.objects if o.type.name == "TextAsset" and o.peek_name() == f"{lang}_{name}")
    s = o.read().m_Script
    s = s if isinstance(s, (bytes, bytearray)) else s.encode("utf-8", "surrogateescape")
    raw = AES.new(b"UKu52ePUBwetZ9wNX88o54dnfKRu0T1l", AES.MODE_ECB).decrypt(base64.b64decode(s))
    raw = raw[:-raw[-1]].decode("utf8")
    return {k: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(v))).strip() for k, v in re.findall(r'<entry name="([^"]+)">(.*?)</entry>', raw, re.S)}
ZONES = {"en": sheet("EN", "Map Zones"), "it": sheet("IT", "Map Zones")}

def tr(g):
    c = comps(g)
    return (c.get("Transform") or c.get("RectTransform"))[0].read()

def label_key(go):
    for mb in comps(go).get("MonoBehaviour", []):
        try:
            d = mb.parse_as_dict()
        except Exception:
            continue
        t = d.get("text")
        if isinstance(t, dict) and t.get("Sheet") == "Map Zones" and t.get("Key"):
            return t["Key"]
    return None

gm = next(o.read() for o in env.objects if o.type.name == "GameObject" and o.peek_name() == "Game_Map_Hornet")
placed, labels_raw, area_key, sub_key = [], [], {}, {}
SKIP = {"Pan Audio Loop", "Main Quest Pins", "Compass Icon", "Shade Pos", "Map Markers", "Flea Tracker Markers"}
for at in [c.read() for c in tr(gm).m_Children]:
    ago = at.m_GameObject.read()
    if ago.m_Name in SKIP:
        continue
    s = at.m_LocalScale
    for rt in [c.read() for c in at.m_Children]:
        rgo = rt.m_GameObject.read()
        x = at.m_LocalPosition.x + rt.m_LocalPosition.x * s.x
        y = at.m_LocalPosition.y + rt.m_LocalPosition.y * s.y
        if rgo.m_Name.startswith("Area Name"):          # the area's own title, placed by the game
            k = label_key(rgo)
            if k:
                labels_raw.append(("area", k, x, y)); area_key.setdefault(ago.m_Name, []).append((k, x, y))
            continue
        for ch in [c.read() for c in rt.m_Children]:    # sub-area titles sit under rooms
            cgo = ch.m_GameObject.read()
            if cgo.m_Name.startswith("Area Name Sub"):
                k = label_key(cgo)
                if k:
                    lx, ly = x + ch.m_LocalPosition.x * s.x, y + ch.m_LocalPosition.y * s.y
                    labels_raw.append(("sub", k, lx, ly)); sub_key.setdefault(ago.m_Name, []).append((k, lx, ly))
        srs = comps(rgo).get("SpriteRenderer")
        if not srs or re.search(r"destroyed|broken|shade_fader", rgo.m_Name, re.I):
            continue
        sr = srs[0].read()
        mbs = comps(rgo).get("MonoBehaviour") or []
        gms = next((m.read() for m in mbs if "fullSprite" in m.parse_as_dict()), None)
        ptr = gms.fullSprite if gms is not None and gms.fullSprite.path_id else sr.m_Sprite
        if not ptr.path_id:
            continue
        try:
            sp = ptr.read()
        except Exception as e:
            print("no sprite", rgo.m_Name, e); continue
        c = sr.m_Color
        placed.append((rgo.m_Name, x, y, sp, ago.m_Name, rt.m_LocalScale.x * s.x, rt.m_LocalScale.y * s.y, (c.r, c.g, c.b)))

boxes = []
for scene, x, y, sp, area, sx, sy, col in placed:
    w, h = sp.m_Rect.width / sp.m_PixelsToUnits * abs(sx), sp.m_Rect.height / sp.m_PixelsToUnits * abs(sy)
    px, py = sp.m_Pivot.x, sp.m_Pivot.y
    boxes.append((x - px * w, y - py * h, x + (1 - px) * w, y + (1 - py) * h, w, h))
minx = min(b[0] for b in boxes) - 1; maxx = max(b[2] for b in boxes) + 1
miny = min(b[1] for b in boxes) - 1; maxy = max(b[3] for b in boxes) + 1
W, H = int((maxx - minx) * SCALE), int((maxy - miny) * SCALE)
X = lambda v: round((v - minx) * SCALE, 1)
Y = lambda v: round((maxy - v) * SCALE, 1)

canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
rooms = {}
for (scene, x, y, sp, area, sx, sy, col), (x0, y0, x1, y1, w, h) in zip(placed, boxes):
    img = sp.image.convert("RGBA")
    if sx < 0: img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if sy < 0: img = img.transpose(Image.FLIP_TOP_BOTTOM)
    img = img.resize((max(1, round((x1 - x0) * SCALE)), max(1, round((y1 - y0) * SCALE))), Image.LANCZOS)
    r, g, b, a = img.split()
    img = Image.merge("RGBA", (r.point(lambda v: v * col[0]), g.point(lambda v: v * col[1]), b.point(lambda v: v * col[2]), a))
    canvas.alpha_composite(img, (round((x0 - minx) * SCALE), round((maxy - y1) * SCALE)))
    # zone of a room = nearest title inside its map area (area titles first, sub-area titles if the area has none)
    cands = area_key.get(area) or sub_key.get(area) or [(area.upper(), x, y)]
    zone = min(cands, key=lambda c: (c[1] - x) ** 2 + (c[2] - y) ** 2)[0]
    rooms[scene] = [X(x), Y(y), zone, round(w, 3), round(h, 3), round(sp.m_Pivot.x, 3), round(sp.m_Pivot.y, 3)]

labels, seen = [], set()
for kind, k, x, y in labels_raw:
    if k not in ZONES["en"] or (kind, k) in seen or ZONES["en"][k] in seen:
        continue
    seen.update([(kind, k), ZONES["en"][k]])
    labels.append({"k": kind, "x": X(x), "y": Y(y), "key": k, "en": ZONES["en"][k], "it": ZONES["it"].get(k, ZONES["en"][k])})

canvas.save("ss_map.webp", quality=90, method=6)
json.dump({"scale": SCALE, "size": [W, H], "rooms": rooms}, open("ss_rooms.json", "w"))
json.dump({"labels": labels, "zones": {k: [ZONES["en"][k], ZONES["it"].get(k, ZONES["en"][k])] for k in ZONES["en"]}},
          open("ss_labels.json", "w", encoding="utf8"), ensure_ascii=False)
print(len(rooms), "rooms,", len(labels), "labels, canvas", W, H)
