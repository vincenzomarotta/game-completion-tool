# Build hollow-knight/data.js from MapChanger (positions, save tracking) + RandomizerMod (groups) + extracted room positions.
import json, re, collections, sys

def lj(p):
    t = open(p, encoding="utf-8-sig").read()
    t = re.sub(r"^\s*//.*$", "", t, flags=re.M)
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", t))

R = "hk/MapChanger/MapChanger/Resources/"
locs = lj(R + "locations.json")
track = lj(R + "trackingItems.json")
pools = lj("hk/RandomizerMod/RandomizerMod/Resources/Data/pools.json")
items = lj("hk/HollowKnight.ItemChanger/ItemChanger/Resources/items.json")
rooms = json.load(open("hk_rooms.json"))

SHOPS = {"Sly", "Sly_(Key)", "Iselda", "Salubra", "Salubra_(Requires_Charms)", "Leg_Eater", "Grubfather", "Seer", "Egg_Shop"}
group_of = {}
for p in pools:
    for v in p["Vanilla"]:
        group_of.setdefault(v["location"], p["Group"])

field_name = {v["fieldName"]: k for k, v in items.items() if isinstance(v, dict) and v.get("fieldName")}
charm_name = {v["charmNum"]: k for k, v in items.items() if isinstance(v, dict) and v.get("charmNum")}
charm_name.update({23: "Fragile_Heart", 24: "Fragile_Greed", 25: "Fragile_Strength", 36: "Kingsoul", 40: "Grimmchild"})
SEER = ["Hallownest_Seal", "Glade_Door", "Pale_Ore", "Dream_Wielder", "Vessel_Fragment", "Dream_Gate", "Arcane_Egg", "Mask_Shard", "Awoken_Dream_Nail", "Ascension"]
MISC = {"slySimpleKey": "Simple_Key", "slyRancidEgg": "Rancid_Egg", "Heart Piece": "Mask_Shard", "Shiny Item Rancid Egg": "Rancid_Egg",
        "Shiny Item Relic2": "Hallownest_Seal", "Shiny Item Ore": "Pale_Ore", "Shiny Item Relic3": "King's_Idol", "dreamReward5b": "Dream_Gate"}

def label(t):
    key = t[1]
    if key in MISC: return MISC[key]
    if key in field_name: return field_name[key]
    m = re.match(r"gotCharm_(\d+)$", key)
    if m: return charm_name[int(m.group(1))]
    m = re.match(r"dreamReward(\d+)$", key)
    if m: return SEER[int(m.group(1)) - 1]
    if re.match(r"slyShellFrag", key): return "Mask_Shard"
    if re.match(r"slyVesselFrag", key): return "Vessel_Fragment"
    if re.match(r"salubraNotch", key): return "Charm_Notch"
    return key

def enc(t):
    k = t["$type"].split(",")[0].split(".")[-1]
    if k == "PdBoolTrackingItem": return ["b", t["PdBoolName"]]
    if k == "PdIntTrackingItem": return ["i", t["PdIntName"], t["PdIntValue"]]
    if k == "PdListTrackingItem": return ["l", t["PdListName"], t["SceneName"]]
    if k == "SdTrackingItem": return ["s", t["Id"], t["SceneName"]]
    if k == "UnionTrackingItem": return ["u", [enc(x) for x in t["TrackingItems"]]]
    if k == "ConjunctionTrackingItem": return ["c", [enc(x) for x in t["TrackingItems"]]]
    raise ValueError(k)

labels = json.load(open("hk_labels.json", encoding="utf8"))

out = []
for name, l in locs.items():
    g = "Shops" if name in SHOPS else group_of.get(name)
    if name not in track or not g:
        continue
    ml = next((m for m in l["MapLocations"] if m["MappedScene"] in rooms["rooms"]), None)
    if not ml:
        print("unplaced", name); continue
    bx, by, area = rooms["rooms"][ml["MappedScene"]][:3]
    rec = {"n": name, "g": g, "a": area,
           "x": round(bx + ml["X"] * rooms["scale"]), "y": round(by - ml["Y"] * rooms["scale"])}
    t = enc(track[name])
    if g == "Shops":
        rec["sub"] = [[label(x), x] for x in t[1]]
    else:
        rec["t"] = t
    out.append(rec)

print(len(out), collections.Counter(r["g"] for r in out))
with open(sys.argv[1], "w", encoding="utf8") as f:
    f.write("// Generated from MapChanger + RandomizerMod data (GPL-3.0) and the game's map layout. Do not edit by hand.\n")
    f.write("window.HK = " + json.dumps({"size": rooms["size"], "zones": labels["zones"], "labels": labels["labels"], "locs": out}, separators=(",", ":"), ensure_ascii=False) + ";\n")
