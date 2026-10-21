# Compose the Silksong map from Game_Map_Hornet room sprites in the game's own colours, plus the game's area labels.
# Output: ss_map.webp, ss_rooms.json {scene: [x, y, areaKey, w, h, pivotX, pivotY]}, ss_labels.json.
import json, sys, glob, warnings, re, base64, html
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from ss_env import *
from PIL import Image
from Crypto.Cipher import AES

SCALE = 100
REFERENCE_SAVE = "ss/save.json"  # decrypted JSON of a 100% save (its scenesMapped decides which room variants to draw)
REF = json.load(open(REFERENCE_SAVE))["playerData"]
ACT3 = bool(REF.get("act3MapUpdated"))  # draw the map as it looks at the end of the game
files = [AA + r"\maps_assets_all.bundle"] + glob.glob(AA + r"\atlases_assets_assets\sprites\_atlases\hornet_map*.bundle")
env = UnityPy.load(*files)
res = UnityPy.load(DATA + r"\resources.assets")


def full_image(sp):
    """Sprite pixels at full rect size: atlas sprites come back trimmed, so put them back at their offset."""
    im = sp.image.convert("RGBA")
    rw, rh = round(sp.m_Rect.width), round(sp.m_Rect.height)
    if im.size == (rw, rh):
        return im
    off = sp.m_RD.textureRectOffset
    out = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
    out.paste(im, (round(off.x), rh - round(off.y) - im.height))
    return out

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

ATLAS = {}
for o in env.objects:
    if o.type.name == "Sprite":
        try:
            ATLAS.setdefault(o.peek_name(), o)
        except Exception:
            pass

def read(ptr):
    try:
        return ptr.read() if ptr is not None and ptr.path_id else None
    except Exception:
        return None

def is_sketch(sp):
    """Finished room art has a dark filled interior; pre-mapping sketches are bright dashed outlines only."""
    px = [p for p in sp.image.convert("RGBA").getdata() if p[3] > 60]
    return not px or sum(1 for r, g, b, a in px if (r + g + b) / 3 < 150) / len(px) < 0.1

ROOM_NAMES = {o.peek_name() for o in env.objects if o.type.name == "GameObject"}

def pick_sprite(name, gms, sr):
    sp = _pick_sprite(name, gms, sr)
    if sp is not None and is_sketch(sp):  # placeholder/sketch chosen: prefer finished art named after the room
        o = ATLAS.get(name)
        if o is not None and not is_sketch(o.read()):
            return o.read()
    return sp

def _pick_sprite(name, gms, sr):
    """The art the game shows for a fully mapped room. GameMapScene.fullSprite is usually right, but:
    - a later state (altFullSprites, e.g. after a boss) replaces it;
    - placeholders (_blank/_empty) or another room's art (Hang_03_top -> Hang_03) lose to the renderer's own sprite
      when that one is named after the room;
    - rooms with no sprite at all get the atlas sprite with their name, if any (e.g. Peak_06, Shellwood_11b)."""
    full = read(gms.fullSprite) if gms is not None else None
    own = read(sr.m_Sprite)
    alts = [read(a.Sprite) for a in (gms.altFullSprites if gms is not None else [])]
    alts = [a for a in alts if a is not None]
    if alts:
        return alts[-1]
    if full is not None and own is not None and full.m_Name.lower() != name.lower():
        # A piece whose "full" art is another room's sprite: once mapped the other room covers it. Keep the piece's
        # own art only when it is real filled art (e.g. Hang_03_top), not a dashed pre-mapping sketch.
        if not is_sketch(own):
            return own
        if full.m_Name in ROOM_NAMES or re.search(r"blank|empty", full.m_Name, re.I):
            return None
        return full
    if full is not None:
        return full
    if own is not None:
        return own
    o = ATLAS.get(name)
    return o.read() if o is not None else None

gm = next(o.read() for o in env.objects if o.type.name == "GameObject" and o.peek_name() == "Game_Map_Hornet")
placed, ghosts, labels_raw, area_key, sub_key = [], [], [], {}, {}
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
                labels_raw.append(("area", k, x, y, rt.m_LocalPosition.x == 0 and rt.m_LocalPosition.y == 0)); area_key.setdefault(ago.m_Name, []).append((k, x, y))
            continue
        for ch in [c.read() for c in rt.m_Children]:    # sub-area titles sit under rooms
            cgo = ch.m_GameObject.read()
            if cgo.m_Name.startswith("Area Name Sub"):
                k = label_key(cgo)
                if k:
                    lx, ly = x + ch.m_LocalPosition.x * s.x, y + ch.m_LocalPosition.y * s.y
                    labels_raw.append(("sub", k, lx, ly, False)); sub_key.setdefault(ago.m_Name, []).append((k, lx, ly))
        srs = comps(rgo).get("SpriteRenderer")
        if not srs or re.search(r"broken|shade_fader", rgo.m_Name, re.I):
            continue
        sr = srs[0].read()
        mbs = comps(rgo).get("MonoBehaviour") or []
        gms_d = next((m.parse_as_dict() for m in mbs if "fullSprite" in m.parse_as_dict()), None)
        gms = next((m.read() for m in mbs if "fullSprite" in m.parse_as_dict()), None)
        # Act 3 map: rooms hidden once act3MapUpdated is set give way to their "_Destroyed" replacements.
        hide = [t.get("FieldName") for g in (gms_d or {}).get("hideCondition", {}).get("TestGroups", []) for t in g.get("Tests", [])]
        if not ACT3 and re.search(r"destroyed", rgo.m_Name, re.I):
            continue
        sp = pick_sprite(rgo.m_Name, gms, sr)
        if sp is None:
            print("no sprite", rgo.m_Name); continue
        c = sr.m_Color
        # not drawn, but items and enemies in these scenes still need a position
        (ghosts if ACT3 and "act3MapUpdated" in hide else placed).append((rgo.m_Name, x, y, sp, ago.m_Name, rt.m_LocalScale.x * s.x, rt.m_LocalScale.y * s.y, (c.r, c.g, c.b)))

boxes = []
for scene, x, y, sp, area, sx, sy, col in placed:
    w, h = sp.m_Rect.width / sp.m_PixelsToUnits * abs(sx), sp.m_Rect.height / sp.m_PixelsToUnits * abs(sy)
    px, py = sp.m_Pivot.x, sp.m_Pivot.y
    boxes.append((x - px * w, y - py * h, x + (1 - px) * w, y + (1 - py) * h, w, h))

# The prefab holds alternative states of some rooms (e.g. Abyss layers, bell variants) stacked on top of each other.
# A 100% save's scenesMapped lists the pieces the game actually draws: keep those, plus unmapped pieces that don't
# overlap them (real rooms the reference save simply never visited).
mapped = set(REF["scenesMapped"])
M = 20  # coarse pixels per map unit for the overlap test, on the rooms' drawn pixels rather than their boxes
mx0, my1 = min(b[0] for b in boxes), max(b[3] for b in boxes)
def room_mask(p, b):
    img = full_image(p[3])
    if p[5] < 0: img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if p[6] < 0: img = img.transpose(Image.FLIP_TOP_BOTTOM)
    a = img.getchannel("A").resize((max(1, round(b[4] * M)), max(1, round(b[5] * M))))
    return a.point(lambda v: 255 if v > 40 else 0), (round((b[0] - mx0) * M), round((my1 - b[3]) * M))
mask = Image.new("L", (round((max(b[2] for b in boxes) - mx0) * M) + 1, round((my1 - min(b[1] for b in boxes)) * M) + 1))
for p, b in zip(placed, boxes):
    if p[0] in mapped:
        a, pos = room_mask(p, b)
        mask.paste(255, pos, a)
def covered(p, b):
    a, (ox, oy) = room_mask(p, b)
    under = mask.crop((ox, oy, ox + a.width, oy + a.height))
    own = sum(1 for v in a.getdata() if v)
    both = sum(1 for v, u in zip(a.getdata(), under.getdata()) if v and u)
    return own and both / own
cov = {p[0]: covered(p, b) for p, b in zip(placed, boxes) if p[0] not in mapped}
print("unmapped coverage:", sorted((round(v, 2), k) for k, v in cov.items()))
keep = [p[0] in mapped or cov[p[0]] < 0.15 for p, b in zip(placed, boxes)]
print("dropped overlapping variants:", [p[0] for p, k in zip(placed, keep) if not k])
ghosts += [p for p, k in zip(placed, keep) if not k]
placed = [p for p, k in zip(placed, keep) if k]
if "--sketchy" in sys.argv:
    for p in placed:
        if is_sketch(p[3]):
            print("SKETCH", p[0], p[3].m_Name)
    sys.exit()
boxes = [b for b, k in zip(boxes, keep) if k]

if "--overlaps" in sys.argv:  # diagnostic: pairs of drawn rooms whose pixels overlap a lot
    masks = [(p[0], *room_mask(p, bb)) for p, bb in zip(placed, boxes)]
    for i, (n1, a1, (x1, y1)) in enumerate(masks):
        for n2, a2, (x2, y2) in masks[i + 1:]:
            ox0, oy0 = max(x1, x2), max(y1, y2)
            ox1, oy1 = min(x1 + a1.width, x2 + a2.width), min(y1 + a1.height, y2 + a2.height)
            if ox0 >= ox1 or oy0 >= oy1:
                continue
            c1 = a1.crop((ox0 - x1, oy0 - y1, ox1 - x1, oy1 - y1)).getdata()
            c2 = a2.crop((ox0 - x2, oy0 - y2, ox1 - x2, oy1 - y2)).getdata()
            both = sum(1 for u, v in zip(c1, c2) if u and v)
            small = min(sum(1 for v in a1.getdata() if v), sum(1 for v in a2.getdata() if v)) or 1
            if both / small > 0.25:
                print(f"OVERLAP {both / small:.2f} {n1} <> {n2}")
    sys.exit()

minx =min(b[0] for b in boxes) - 1; maxx = max(b[2] for b in boxes) + 1
miny = min(b[1] for b in boxes) - 1; maxy = max(b[3] for b in boxes) + 1
W, H = int((maxx - minx) * SCALE), int((maxy - miny) * SCALE)
X = lambda v: round((v - minx) * SCALE, 1)
Y = lambda v: round((maxy - v) * SCALE, 1)

def room_entry(scene, x, y, sp, area, w, h):
    # zone of a room = nearest title inside its map area (area titles first, sub-area titles if the area has none)
    cands = area_key.get(area) or sub_key.get(area) or [(area.upper(), x, y)]
    zone = min(cands, key=lambda c: (c[1] - x) ** 2 + (c[2] - y) ** 2)[0]
    return [X(x), Y(y), zone, round(w, 3), round(h, 3), round(sp.m_Pivot.x, 3), round(sp.m_Pivot.y, 3)]

canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
rooms = {}
for (scene, x, y, sp, area, sx, sy, col), (x0, y0, x1, y1, w, h) in zip(placed, boxes):
    img = full_image(sp)
    if sx < 0: img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if sy < 0: img = img.transpose(Image.FLIP_TOP_BOTTOM)
    img = img.resize((max(1, round((x1 - x0) * SCALE)), max(1, round((y1 - y0) * SCALE))), Image.LANCZOS)
    r, g, b, a = img.split()
    img = Image.merge("RGBA", (r.point(lambda v: v * col[0]), g.point(lambda v: v * col[1]), b.point(lambda v: v * col[2]), a))
    canvas.alpha_composite(img, (round((x0 - minx) * SCALE), round((maxy - y1) * SCALE)))
    rooms[scene] = room_entry(scene, x, y, sp, area, w, h)
for scene, x, y, sp, area, sx, sy, col in ghosts:
    if scene not in rooms:
        rooms[scene] = room_entry(scene, x, y, sp, area, sp.m_Rect.width / sp.m_PixelsToUnits * abs(sx), sp.m_Rect.height / sp.m_PixelsToUnits * abs(sy))

zone_boxes = {}
for (scene, *_), b in zip(placed, boxes):
    zone_boxes.setdefault(rooms[scene][2], []).append(b)

labels, seen = [], set()
for kind, k, x, y, at_origin in labels_raw:
    if k not in ZONES["en"] or (kind, k) in seen or ZONES["en"][k] in seen:
        continue
    seen.update([(kind, k), ZONES["en"][k]])
    zb = zone_boxes.get(k)
    if kind == "area" and zb:
        # some titles are anchored far from their rooms (e.g. The Abyss): move those to the zone's centre
        near = any(b[0] - 2 <= x <= b[2] + 2 and b[1] - 2 <= y <= b[3] + 2 for b in zb)
        if not near or at_origin:  # titles left at the area origin were never placed by hand
            # median of room centres: a few far-off connector rooms (e.g. the Abyss ascent) can't drag it away
            xs, ys = sorted((b[0] + b[2]) / 2 for b in zb), sorted((b[1] + b[3]) / 2 for b in zb)
            x, y = xs[len(xs) // 2], ys[len(ys) // 2]
    labels.append({"k": kind, "x": X(x), "y": Y(y), "key": k, "en": ZONES["en"][k], "it": ZONES["it"].get(k, ZONES["en"][k])})

canvas.save("ss_map.webp", quality=90, method=6)
json.dump({"scale": SCALE, "size": [W, H], "rooms": rooms}, open("ss_rooms.json", "w"))
json.dump({"labels": labels, "zones": {k: [ZONES["en"][k], ZONES["it"].get(k, ZONES["en"][k])] for k in ZONES["en"]}},
          open("ss_labels.json", "w", encoding="utf8"), ensure_ascii=False)
print(len(rooms), "rooms,", len(labels), "labels, canvas", W, H)
