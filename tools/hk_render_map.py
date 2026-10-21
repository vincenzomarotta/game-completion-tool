# Compose the full Hollow Knight map from the Game_Map prefab room sprites.
# Output: hk_map.png (tinted per area) + hk_rooms.json {scene: [x, y]} in image pixels (room transform position).
import UnityPy, json, re
from PIL import Image

ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Hollow Knight\hollow_knight_Data\resources.assets"
SCALE = 100  # output pixels per map unit
env = UnityPy.load(ROOT)

sprites = {}
for o in env.objects:
    if o.type.name == "Sprite":
        try:
            sprites.setdefault(o.peek_name(), o)
        except Exception:
            pass

gm = next(o for o in env.objects if o.type.name == "GameObject" and o.peek_name() == "Game_Map").read()

def parts(go):
    t = sr = None
    for c in go.m_Components:
        r = (c.component if hasattr(c, "component") else c).deref()
        if r.type.name in ("Transform", "RectTransform"): t = r.read()
        elif r.type.name == "SpriteRenderer": sr = r.read()
    return t, sr

def kids(t):
    return [ch.read() for ch in t.m_Children]

def lj(p):
    t = open(p, encoding="utf-8-sig").read()
    t = re.sub(r"^\s*//.*$", "", t, flags=re.M)
    return json.loads(re.sub(r",(\s*[}\]])", r"", t))
room_sprites = lj("hk/MapChanger/MapChanger/Resources/roomSprites.json")
wanted = {p for v in room_sprites.values() for p in v["RoomSprites"]}  # "Area/Room"

placed = []   # (scene, x, y, sprite_obj, area)
gmt, _ = parts(gm)
for at in kids(gmt):
    ago = at.m_GameObject.read()
    for rt in kids(at):
        rgo = rt.m_GameObject.read()
        key = f"{ago.m_Name}/{rgo.m_Name}"
        if key not in wanted:
            continue
        _, sr = parts(rgo)
        if not sr or not sr.m_Sprite.path_id:
            continue
        name = sr.m_Sprite.read().m_Name
        full = re.sub(r"_Cornifer$", "", name)
        sp = sprites.get(full) or sprites.get(name)
        x = at.m_LocalPosition.x + rt.m_LocalPosition.x
        y = at.m_LocalPosition.y + rt.m_LocalPosition.y
        placed.append((rgo.m_Name, x, y, sp.read(), ago.m_Name))

print("rooms placed", len(placed), "of", len(wanted))

# world bounds
boxes = []
for scene, x, y, sp, area in placed:
    w, h = sp.m_Rect.width / sp.m_PixelsToUnits, sp.m_Rect.height / sp.m_PixelsToUnits
    px, py = sp.m_Pivot.x, sp.m_Pivot.y
    boxes.append((x - px * w, y - py * h, x + (1 - px) * w, y + (1 - py) * h))
minx = min(b[0] for b in boxes) - 1; maxx = max(b[2] for b in boxes) + 1
miny = min(b[1] for b in boxes) - 1; maxy = max(b[3] for b in boxes) + 1
W, H = int((maxx - minx) * SCALE), int((maxy - miny) * SCALE)
print("canvas", W, H)

TINT = {  # muted per-area colors, our own palette
    "Crossroads": (150, 170, 200), "Town_Tutorial": (200, 200, 205), "Green_Path": (130, 200, 130),
    "Fungal Wastes": (180, 190, 120), "Fog_Canyon": (200, 160, 220), "Queens_Gardens": (110, 190, 150),
    "City of Tears": (110, 150, 230), "Waterways": (90, 190, 190), "Deepnest": (150, 135, 175),
    "Kingdoms_Edge": (230, 215, 195), "Crystal Peak": (230, 140, 200), "Resting_Grounds": (230, 200, 140),
    "Ancient Basin": (135, 150, 170), "Cliffs": (190, 190, 190),
}

canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
rooms = {}
for (scene, x, y, sp, area), (x0, y0, x1, y1) in zip(placed, boxes):
    img = sp.image.convert("RGBA")
    tw, th = max(1, round((x1 - x0) * SCALE)), max(1, round((y1 - y0) * SCALE))
    img = img.resize((tw, th), Image.LANCZOS)
    r, g, b = TINT.get(area, (200, 200, 200))
    a = img.getchannel("A")
    lum = img.convert("L")
    tinted = Image.merge("RGBA", (lum.point(lambda v: v * r // 255), lum.point(lambda v: v * g // 255), lum.point(lambda v: v * b // 255), a))
    canvas.alpha_composite(tinted, (round((x0 - minx) * SCALE), round((maxy - y1) * SCALE)))
    rooms[scene] = [round((x - minx) * SCALE, 1), round((maxy - y) * SCALE, 1), area]

canvas.save("hk_map.webp", quality=88, method=6)
json.dump({"scale": SCALE, "size": [W, H], "rooms": rooms}, open("hk_rooms.json", "w"))
print("saved")
