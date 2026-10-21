# Where in the world is each item the map can't place from scene data? Scan every scene for components that point at
# the item's asset (pickups, shops, NPCs, quest givers) or name its save flag (FSM actions), and keep their positions.
# Output ss_refs.json {"kind:name": [[scene, x, y, objectName], ...]}; ss_build_data.py turns them into pins.
import json, os, re, struct, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from ss_env import *

D = AA + r"\dataassets_assets_assets\dataassets"
BUNDLES = {"tool": r"\tools\toolitems", "crest": r"\tools\crestitems", "collectable": r"\collectables\collectableitems",
           "relic": r"\collectables\relics", "materium": r"\collectables\materium", "quest": r"\questsystem\quests",
           "mainquest": r"\questsystem\mainquests"}
assets = {}  # (cab, path_id) -> "kind:name"
for kind, b in BUNDLES.items():
    env = UnityPy.load(D + b + ".bundle")
    cab = next(iter(next(iter(env.files.values())).files)).lower()
    for o in env.objects:
        if o.type.name == "MonoBehaviour":
            n = o.parse_as_dict().get("m_Name")
            if n:
                assets[(cab, o.path_id)] = ("quest" if kind == "mainquest" else kind) + ":" + n

def pptrs(v, ext):
    """(cab, path_id) of every PPtr in a parsed object that points into another file."""
    if isinstance(v, dict):
        if v.get("m_FileID") and "m_PathID" in v and 0 < v["m_FileID"] <= len(ext):
            yield ext[v["m_FileID"] - 1], v["m_PathID"]
        for x in v.values():
            yield from pptrs(x, ext)
    elif isinstance(v, list):
        for x in v:
            yield from pptrs(x, ext)

def externals(f):
    return [e.path.split("/")[-1].lower() for e in f.externals]

# Shop entries point at the item they sell: a scene that references the shop entry sells that item.
shop = UnityPy.load(D + r"\shopitems.bundle")
scab = next(iter(next(iter(shop.files.values())).files)).lower()
for o in shop.objects:
    if o.type.name == "MonoBehaviour":
        for ref in pptrs(o.parse_as_dict(), externals(o.assets_file)):
            if ref in assets:
                assets[(scab, o.path_id)] = assets[ref]
                break

d = json.load(open("ss/dict.json"))
flags = set()
for c in d:
    for s in c["sections"]:
        for it in s["items"]:
            for p in (it["parsingInfo"] if isinstance(it["parsingInfo"], list) else [it["parsingInfo"]]):
                if p["type"] in ("flag", "flagReturn", "quill"):
                    flags.add(p["internalId"])
                elif p["type"] in ("flagAnyOf",):
                    flags.update(p["internalId"])
                elif p["type"] == "flagMin":
                    flags.add(p["internalId"][0])
# Unity strings are a 32-bit length then the bytes; path ids are 64-bit little endian
pat = re.compile(b"|".join([re.escape(struct.pack("<i", len(f)) + f.encode()) for f in sorted(flags)] +
                           [re.escape(struct.pack("<q", pid)) for pid in {k[1] for k in assets}]))
flag_bytes = {struct.pack("<i", len(f)) + f.encode(): f for f in flags}
print(len(assets), "assets,", len(flags), "flags", flush=True)

def world(t):
    chain = []
    while t is not None:
        chain.append(t)
        t = t.m_Father.read() if t.m_Father.path_id else None
    x = y = 0.0; sx = sy = 1.0
    for t in reversed(chain):
        x += t.m_LocalPosition.x * sx; y += t.m_LocalPosition.y * sy
        sx *= t.m_LocalScale.x; sy *= t.m_LocalScale.y
    return round(x, 2), round(y, 2)

out = {}
SCN = AA + r"\scenes_scenes_scenes"
for n, f in enumerate(sorted(os.listdir(SCN))[:int(sys.argv[1]) if len(sys.argv) > 1 else None]):
    if not f.endswith(".bundle"):
        continue
    try:
        env = UnityPy.load(os.path.join(SCN, f))
    except Exception:
        continue
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            raw = o.get_raw_data()
        except Exception:
            continue
        hits = set(m.group(0) for m in pat.finditer(raw))
        if not hits:
            continue
        keys = {"flag:" + flag_bytes[h] for h in hits if h in flag_bytes}
        if len(keys) < len(hits):  # some path id matched: confirm it is a real reference to a target asset
            try:
                keys |= {assets[r] for r in pptrs(o.parse_as_dict(), externals(o.assets_file)) if r in assets}
            except Exception:
                pass
        if not keys:
            continue
        try:
            go = o.read().m_GameObject.read()
            c = comps(go)
            pos, name = world((c.get("Transform") or c.get("RectTransform"))[0].read()), go.m_Name
        except Exception:
            pos, name = (None, None), ""
        for k in keys:
            out.setdefault(k, []).append([f[:-7], *pos, name])
    if n % 100 == 0:
        print(n, f, len(out), flush=True)
json.dump(out, open("ss_refs.json", "w"), indent=0)
print("found", len(out), flush=True)
