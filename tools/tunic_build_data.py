# Build tunic/data.js from the TUNIC randomizer location list (MIT): name, category, region, scene, x/z position, save check.
import json, re, sys, collections

SRC = "tunic/tunic-randomizer/src/Data/"
raw = open(SRC + "ItemListJson.cs", encoding="utf-8-sig").read()
raw = raw[raw.index('@"') + 2:raw.rindex('"')].replace('""', '"')
items = json.loads(re.sub(r",(\s*[}\]])", r"\1", raw))
loc_cs = open(SRC + "Locations.cs", encoding="utf-8-sig").read()
names = json.loads(json.loads('"' + re.search(r'LocationNamesJson = "(.*?)";\n', loc_cs).group(1) + '"'))
items_cs = open(SRC + "Items.cs", encoding="utf-8-sig").read()
fairy_flag = dict(re.findall(r'\{"([^"]+)", new Fairy\("([^"]+)"', items_cs))
relic_flag = {m[0]: m[1] for m in re.findall(r'\{"(Relic - [^"]+)", new HeroRelic\("([^"]+)"', items_cs)}

# Unique pickups: the item stays in the inventory (or the flag below is set once it's used).
INVENTORY = {"Lantern": "Lantern", "Wand": "Wand", "Techbow": "Techbow", "Stundagger": "Stundagger", "Vault Key (Red)": "Vault Key (Red)"}
FLAGS = {"Sword": ["Got Sword", "inventory quantity Sword"], "Shield": ["Got Shield", "inventory quantity Shield"],
         "Key (House)": ["SV_Housekey from beach", "SV_Overworld_House Door Opened", "inventory quantity Key (House)"]}
HEX = {"Hexagon Red": "Placed Hexagon 1 Red", "Hexagon Green": "Placed Hexagon 2 Green", "Hexagon Blue": "Placed Hexagon 3 Blue"}

def check(lid, scene, reward):
    if lid.isdigit():
        if lid == "999":
            return ["k", "inventory quantity Hyperdash"]
        return ["k", f"chest open {lid}"]
    if reward["Type"] == "PAGE":
        return ["k", f"unlocked page {reward['Name']}"]
    if lid in fairy_flag:
        return ["k", fairy_flag[lid]]
    if reward["Type"] == "RELIC":
        return ["k", relic_flag[reward["Name"]]]
    m = re.match(r"Well Reward \((\d+) Coins\)", lid)
    if m:
        return ["n", "SV_Trinket Coins Tossed", int(m.group(1))]
    if lid in HEX:
        return ["o", [["k", f"inventory quantity {lid}"], ["k", HEX[lid]]]]
    if scene == "Shop":
        return ["k", f"SV_Shop_{lid}"]
    if lid in FLAGS:
        return ["o", [["k", k] for k in FLAGS[lid]]]
    if lid in INVENTORY:
        return ["k", f"inventory quantity {INVENTORY[lid]}"]
    if lid == "Key" and scene == "Overworld Redux":
        return ["o", [["k", "SV_got first key"], ["k", "inventory quantity Key"]]]
    return None  # Atoll key: no readable flag found

def category(lid, scene, reward, tr):
    if tr is None: return "Manual"
    if reward["Type"] == "PAGE": return "Pages"
    if reward["Type"] == "FAIRY": return "Fairies"
    if reward["Type"] == "RELIC": return "Relics"
    if lid.startswith("Well Reward"): return "Well"
    if scene == "Shop": return "Shop"
    if lid.isdigit() and lid != "999":
        return "Secrets" if int(lid) >= 1000 else "Chests"
    return "KeyItems"

out = []
for it in items:
    L = it["Location"]
    lid, scene = L["LocationId"], L["SceneName"]
    full = names[f"{lid} [{scene}]"]
    region, _, desc = full.partition(" - ")
    tr = check(lid, scene, it["Reward"])
    x, y, z = (float(v) for v in (L["Position"] or "(0, 0, 0)").strip("()").split(","))
    rec = {"n": desc, "r": region, "s": scene, "g": category(lid, scene, it["Reward"], tr), "p": [round(x, 1), round(z, 1)]}
    if tr: rec["t"] = tr
    out.append(rec)

print(len(out), collections.Counter(r["g"] for r in out))
if len(sys.argv) > 2:
    save = dict(l.split("|", 1) for l in open(sys.argv[2], encoding="utf8").read().splitlines() if "|" in l)
    num = lambda k: float(save.get(k) or 0) if re.fullmatch(r"-?\d+(\.\d+)?", save.get(k) or "0") else 1
    def has(t):
        if t[0] == "k": return num(t[1]) >= 1
        if t[0] == "n": return num(t[1]) >= t[2]
        if t[0] == "o": return any(has(x) for x in t[1])
    c = collections.Counter(r["g"] for r in out if "t" in r and has(r["t"]))
    print("got:", c, sum(c.values()))
with open(sys.argv[1], "w", encoding="utf8") as f:
    f.write("// Generated from the TUNIC randomizer location list (MIT, silent-destroyer/tunic-randomizer). Do not edit by hand.\n")
    f.write("window.TUNIC = " + json.dumps(out, separators=(",", ":"), ensure_ascii=False) + ";\n")
