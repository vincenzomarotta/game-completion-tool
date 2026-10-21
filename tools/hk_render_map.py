# Compose the full Hollow Knight map from the Game_Map prefab, in the game's own colours, plus area/sub-area labels.
# Output: hk_map.webp, hk_rooms.json {scale, size, rooms: {scene: [x, y, areaKey, w, h]}}, hk_labels.json.
import UnityPy, json, re, base64, html
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
from Crypto.Cipher import AES
from PIL import Image

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Hollow Knight"
SCALE = 100  # output pixels per map unit (the sprites' native resolution)
env = UnityPy.load(GAME + r"\hollow_knight_Data\resources.assets")
gen = TypeTreeGenerator(env.objects[0].assets_file.unity_version)
gen.load_local_game(GAME)
env.typetree_generator = gen

def sheet(lang, name):
    o = next(o for o in env.objects if o.type.name == "TextAsset" and o.peek_name() == f"{lang}_{name}")
    s = o.read().m_Script
    s = s if isinstance(s, str) else s.decode("utf8", "surrogateescape")
    raw = AES.new(b"UKu52ePUBwetZ9wNX88o54dnfKRu0T1l", AES.MODE_ECB).decrypt(base64.b64decode(s))
    raw = raw[:-raw[-1]].decode("utf8")
    return {k: html.unescape(v).replace("<br>", " ").strip() for k, v in re.findall(r'<entry name="([^"]+)">(.*?)</entry>', raw, re.S)}
ZONES = {"en": sheet("EN", "Map Zones"), "it": sheet("IT", "Map Zones")}

AREA_KEY = {"Crossroads": "CROSSROADS", "Town_Tutorial": "TOWN", "Green_Path": "GREEN_PATH", "Fungal Wastes": "WASTES",
            "Fog_Canyon": "FOG_CANYON", "Queens_Gardens": "ROYAL_GARDENS", "City of Tears": "CITY", "Waterways": "WATERWAYS",
            "Deepnest": "DEEPNEST", "Kingdoms_Edge": "OUTSKIRTS", "Crystal Peak": "MINES", "Resting_Grounds": "RESTING_GROUNDS",
            "Ancient Basin": "ABYSS", "Cliffs": "CLIFFS"}

sprites = {}
for o in env.objects:
    if o.type.name == "Sprite":
        try:
            sprites.setdefault(o.peek_name(), o)
        except Exception:
            pass

def comps(go):
    out = {}
    for c in go.m_Components:
        r = (c.component if hasattr(c, "component") else c).deref()
        out.setdefault(r.type.name, []).append(r)
    return out

def tr(go):
    c = comps(go)
    return (c.get("Transform") or c.get("RectTransform"))[0].read()

def lj(p):
    t = open(p, encoding="utf-8-sig").read()
    t = re.sub(r"^\s*//.*$", "", t, flags=re.M)
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", t))
wanted = {p for v in lj("hk/MapChanger/MapChanger/Resources/roomSprites.json").values() for p in v["RoomSprites"]}

gm = next(o for o in env.objects if o.type.name == "GameObject" and o.peek_name() == "Game_Map").read()
placed, subs = [], []
for at in [c.read() for c in tr(gm).m_Children]:
    ago = at.m_GameObject.read()
    for rt in [c.read() for c in at.m_Children]:
        rgo = rt.m_GameObject.read()
        rx, ry = at.m_LocalPosition.x + rt.m_LocalPosition.x, at.m_LocalPosition.y + rt.m_LocalPosition.y
        # sub-area labels live under rooms ("Sub Area Name"), with their text key from the Map Zones sheet
        for ch in [c.read() for c in rt.m_Children]:
            cgo = ch.m_GameObject.read()
            if cgo.m_Name.startswith("Sub Area Name"):
                key = None
                for mb in comps(cgo).get("MonoBehaviour", []):
                    try:
                        d = mb.parse_as_dict()
                    except Exception:
                        continue
                    if d.get("sheetName") == "Map Zones":
                        key = d["convName"]
                if key:
                    subs.append((key, rx + ch.m_LocalPosition.x, ry + ch.m_LocalPosition.y))
        if f"{ago.m_Name}/{rgo.m_Name}" not in wanted:
            continue
        srs = comps(rgo).get("SpriteRenderer")
        if not srs:
            continue
        sr = srs[0].read()
        if not sr.m_Sprite.path_id:
            continue
        name = sr.m_Sprite.read().m_Name
        sp = (sprites.get(re.sub(r"_Cornifer$", "", name)) or sprites.get(name)).read()
        c = sr.m_Color
        placed.append((rgo.m_Name, rx, ry, sp, ago.m_Name, (c.r, c.g, c.b)))

boxes = []
for scene, x, y, sp, area, col in placed:
    w, h = sp.m_Rect.width / sp.m_PixelsToUnits, sp.m_Rect.height / sp.m_PixelsToUnits
    px, py = sp.m_Pivot.x, sp.m_Pivot.y
    boxes.append((x - px * w, y - py * h, x + (1 - px) * w, y + (1 - py) * h, w, h))
minx = min(b[0] for b in boxes) - 1; maxx = max(b[2] for b in boxes) + 1
miny = min(b[1] for b in boxes) - 1; maxy = max(b[3] for b in boxes) + 1
W, H = int((maxx - minx) * SCALE), int((maxy - miny) * SCALE)
X = lambda x: round((x - minx) * SCALE, 1)
Y = lambda y: round((maxy - y) * SCALE, 1)

canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
rooms, area_pts = {}, {}
for (scene, x, y, sp, area, col), (x0, y0, x1, y1, w, h) in zip(placed, boxes):
    img = sp.image.convert("RGBA").resize((max(1, round((x1 - x0) * SCALE)), max(1, round((y1 - y0) * SCALE))), Image.LANCZOS)
    r, g, b, a = img.split()
    img = Image.merge("RGBA", (r.point(lambda v: v * col[0]), g.point(lambda v: v * col[1]), b.point(lambda v: v * col[2]), a))
    canvas.alpha_composite(img, (round((x0 - minx) * SCALE), round((maxy - y1) * SCALE)))
    rooms[scene] = [X(x), Y(y), AREA_KEY.get(area, ""), round(w, 3), round(h, 3)]
    area_pts.setdefault(area, []).append(((x0 + x1) / 2, (y0 + y1) / 2, w * h))

labels = []
for area, pts in area_pts.items():
    key = AREA_KEY.get(area)
    if not key:
        continue
    tot = sum(p[2] for p in pts)
    cx, cy = sum(p[0] * p[2] for p in pts) / tot, sum(p[1] * p[2] for p in pts) / tot
    labels.append({"k": "area", "x": X(cx), "y": Y(cy), "en": ZONES["en"][key], "it": ZONES["it"][key]})
for key, x, y in subs:
    labels.append({"k": "sub", "x": X(x), "y": Y(y), "en": ZONES["en"].get(key, key), "it": ZONES["it"].get(key, key)})

canvas.save("hk_map.webp", quality=90, method=6)
json.dump({"scale": SCALE, "size": [W, H], "rooms": rooms}, open("hk_rooms.json", "w"))
json.dump({"labels": labels, "zones": {k: [ZONES["en"][k], ZONES["it"][k]] for k in AREA_KEY.values()}}, open("hk_labels.json", "w", encoding="utf8"), ensure_ascii=False)
print(len(rooms), "rooms,", len(labels), "labels, canvas", W, H)
