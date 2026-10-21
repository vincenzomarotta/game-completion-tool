# Build silksong/data.js: every tracked item (silksong-completionist dictionary, MIT) with a map position when the
# game files tell us where it is, the Hunter's Journal (names in EN/IT from the game) and enemy pins from the scenes.
import json, os, re, shutil, sys, base64, html, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from ss_env import *
from Crypto.Cipher import AES

OUT = sys.argv[1]
d = json.load(open("ss/dict.json"))
rooms = json.load(open("ss_rooms.json"))
labels = json.load(open("ss_labels.json", encoding="utf8"))
scenes = json.load(open("ss_scenes.json"))
enemies = json.load(open("ss_enemies.json"))
best = json.load(open("ss_bestiary_index.json"))
S = rooms["scale"]
room_ci = {k.lower(): v for k, v in rooms["rooms"].items()}
size_ci = {k.lower(): v["size"] for k, v in enemies.items() if v["size"]}

# Journal names from the game: record displayName key -> EN/IT Journal sheet.
res = UnityPy.load(DATA + r"\resources.assets")
def sheet(lang, name):
    o = next(o for o in res.objects if o.type.name == "TextAsset" and o.peek_name() == f"{lang}_{name}")
    s = o.read().m_Script
    s = s if isinstance(s, (bytes, bytearray)) else s.encode("utf-8", "surrogateescape")
    raw = AES.new(b"UKu52ePUBwetZ9wNX88o54dnfKRu0T1l", AES.MODE_ECB).decrypt(base64.b64decode(s))
    raw = raw[:-raw[-1]].decode("utf8")
    return {k: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(v))).strip() for k, v in re.findall(r'<entry name="([^"]+)">(.*?)</entry>', raw, re.S)}
J_IT = sheet("IT", "Journal")
rec_env = UnityPy.load(AA + r"\dataassets_assets_assets\dataassets\enemyjournal\journalrecords.bundle")
REC_KEY = {}
for o in rec_env.objects:
    if o.type.name == "MonoBehaviour":
        dd = o.parse_as_dict()
        REC_KEY[dd["m_Name"]] = dd["displayName"]["Key"]

CATS = {
    "Mask Shards": "mask", "Spool Fragments": "spool", "Memory Lockets": "locket", "Craftmetals": "metal", "Mossberries": "berry",
    "Pale Oil": "core", "Silkeaters": "silkeater", "Caches & Secrets": "rosary", "Unique Spawns": "beast", "Keys": "key",
    "Upgrades": "core", "Lost Fleas": "flea", "Tools": "tool", "Abilities": "ability", "Crests": "crest", "Relics": "relic",
    "Tasks": "wish", "Bellways": "bellway", "Ventrica Stations": "tube", "Mapping Supplies": "quill", "Bellhome": "bellhome",
    "Materium": "materium", "Mementos": "memento", "Bosses": "boss",
}
SECTION_PIN = {"Shell Shard Caches": "shard", "Breakable Walls": "wall", "Void Masses": "void"}

def infos(p): return p if isinstance(p, list) else [p]

# ss_scan_refs.py: scenes whose components point at an item's asset or name its save flag. Only clear cases become pins:
# a pickup/shop/station object, or every remaining reference in one room. Shared prefabs (weaver shrines, wish boards,
# benches, the mapper) reference many items at once and are ignored.
refs = json.load(open("ss_refs.json")) if os.path.exists("ss_refs.json") else {}
JUNK = re.compile(r"bench|mapper|loader|area title|caravan|return scene|control|states|menu|credits|board|shrine weaver|template", re.I)
GOOD = re.compile(r"pickup|collectable item|toll machine|travel tube|inspect region|shop|merchant|crest upgrade shrine|plinney|memento", re.I)
REF_KIND = {"mementoDeposit": "collectable"}
def ref_pin(ps):
    p = ps[0]
    ids = p["internalId"] if isinstance(p["internalId"], list) else [p["internalId"]]
    if p["type"] == "flagMin":
        ids = ids[:1]
    flag = p["type"].startswith("flag") or p["type"] == "quill"
    hits = [h for i in ids for h in refs.get(("flag:" if flag else REF_KIND.get(p["type"], p["type"]) + ":") + str(i), [])]
    hits = [h for h in hits if not JUNK.search(h[3] or "") and (h[1] or h[2]) and to_map(re.sub(r"(_boss.*|_memory)$", "", h[0].lower()), None, None)]
    good = [h for h in hits if GOOD.search(h[3] or "")]
    if len({h[0] for h in good}) == 1:
        hits = good
    elif len({re.sub(r"(_boss.*)$", "", h[0].lower()) for h in hits}) != 1:
        return None
    scene, x, y = hits[0][:3]
    base = scene if to_map(scene, None, None) else re.sub(r"(_boss.*|_memory)$", "", scene.lower())
    return to_map(base, (x, y), size_ci.get(scene.lower()) or size_ci.get(base))

def to_map(scene, pos, size):
    """Map pixel position of a scene-space point, or the room centre when it can't be placed exactly."""
    room = rooms["rooms"].get(scene) or room_ci.get(scene.lower())
    if not room:
        return None
    x, y, zone, w, h, pvx, pvy = room
    if pos and size:
        W, H = size
        left, bottom = x - pvx * w * S, y + pvy * h * S
        return [round(left + pos[0] / W * w * S), round(bottom - pos[1] / H * h * S)], zone
    return [round(x + (0.5 - pvx) * w * S), round(y - (0.5 - pvy) * h * S)], zone

def place(scene, obj):
    info = scenes.get(scene) or {}
    return to_map(scene, info.get("objs", {}).get(obj), info.get("size") or size_ci.get(scene.lower()))

items, journal = [], []
os.makedirs(os.path.join(OUT, "journal"), exist_ok=True)
for cat in d:
    for sec in cat["sections"]:
        for it in sec["items"]:
            ps = infos(it["parsingInfo"])
            if cat["name"] == "Hunter's Journal":
                jid = ps[0]["internalId"]
                rec = {"n": it["name"], "it": J_IT.get(REC_KEY.get(jid, ""), it["name"]), "id": jid,
                       "k": (it.get("additionalMeta") or {}).get("killsRequired", 1)}
                if jid in best["index"]:
                    rec["i"] = best["index"][jid]
                else:  # no icon in the game atlas: fall back to the dictionary's image
                    src = os.path.join("ss/silksong-completionist/src/assets", it["additionalMeta"]["imageAsset"])
                    shutil.copy(src, os.path.join(OUT, "journal", os.path.basename(src)))
                    rec["img"] = "journal/" + os.path.basename(src)
                journal.append(rec)
                continue
            rec = {"c": cat["name"], "s": sec.get("name") or "", "n": it["name"], "d": it.get("completionDetails", ""),
                   "a": it.get("whichAct", 0), "t": it["parsingInfo"]}
            if it.get("onlyFoundInSteelSoulMode"): rec["ss"] = 1
            if it.get("onlyFoundInClassicMode"): rec["cl"] = 1
            pin = None
            for p in ps:
                if p["type"].startswith("sceneData"):
                    pin = place(p["internalId"][0], p["internalId"][1]); break
                if p["type"] == "flag" and p["internalId"].startswith("SavedFlea_"):
                    pin = place(p["internalId"][len("SavedFlea_"):], "*flea*"); break
            if not pin and not ps[0]["type"].startswith("sceneData"):
                pin = ref_pin(ps)
            if pin and cat["name"] in CATS:
                rec["p"], rec["r"] = pin
                rec["i"] = SECTION_PIN.get(sec.get("name"), CATS[cat["name"]])
            items.append(rec)

# Enemy pins: one per enemy type per room, at the first placement found in that scene.
jidx = {e["id"]: i for i, e in enumerate(journal)}
epins = []
for scene, info in enemies.items():
    per = {}
    for jid, wx, wy in info["hits"]:
        per.setdefault(jid, []).append((wx, wy))
    for jid, pts in per.items():
        if jid not in jidx:
            continue
        pin = to_map(scene, pts[0], info["size"])
        if pin:
            epins.append([jidx[jid], pin[0][0], pin[0][1], pin[1], len(pts)])

ZONE_OF_SCENE = [("organ_", "ORGAN"), ("room_crowcourt", "CRAW_LAKE"), ("peak_", "PEAK"), ("coral_29", "VOLTNEST"),
                 ("clover_", "CLOVER"), ("memory_coral_tower", "RED_CORAL_TOWER"), ("memory_ant_queen", "HUNTERS_NEST"),
                 ("abyss_", "ABYSS"), ("dust_maze", "DUSTPENS"), ("cradle_", "CRADLE"), ("slab_", "THE_SLAB"),
                 ("ant_", "HUNTERS_NEST"), ("abandoned_town", "BONETOWN"), ("bellway_centipede", "CITADEL_STATION")]
# Bosses / scripted enemies: scenes whose components reference the journal record (ss_scan_boss_scenes.py).
# One pin per entry, count 0 = "fought here"; object position when usable, else the room centre.
pinned = {p[0] for p in epins}
for jid, refs in (json.load(open("ss_boss_scenes.json")) if os.path.exists("ss_boss_scenes.json") else {}).items():
    if jid not in jidx or jidx[jid] in pinned:
        continue
    pin = None
    for scene, wx, wy in refs:
        size = size_ci.get(scene.lower())
        pin = to_map(scene, (wx, wy) if wx or wy else None, size)
        if not pin:  # arena / memory variants share the base room ("bone_05_boss" -> "bone_05")
            base = re.sub(r"(_boss.*|_memory)$", "", scene.lower())
            pin = to_map(base, (wx, wy) if wx or wy else None, size_ci.get(base))
        if pin:
            break
    if not pin:  # fights in scenes with no room of their own: pin the zone title they belong to
        key = next((k for pre, k in ZONE_OF_SCENE if refs[0][0].lower().startswith(pre)), None)
        lab = next((l for l in labels["labels"] if l["key"] == key), None)
        if lab:
            pin = ([round(lab["x"]), round(lab["y"])], key)
    if pin:
        epins.append([jidx[jid], pin[0][0], pin[0][1], pin[1], 0])

# A few bosses no scene search finds: pin their zone title by hand.
MANUAL_ZONE = {"Last Judge": "JUDGE_STEPS", "Tormented Trobbio": "CITADEL_STAGE", "Flower Queen": "SHELLWOOD_THICKET"}
pinned = {p[0] for p in epins}
for jid, key in MANUAL_ZONE.items():
    lab = next((l for l in labels["labels"] if l["key"] == key), None)
    if jid in jidx and jidx[jid] not in pinned and lab:
        epins.append([jidx[jid], round(lab["x"]), round(lab["y"]), key, 0])

# Bosses without a pin of their own sit where their Hunter's Journal entry is pinned (same name or journal id).
first_pin = {}
for e in epins:
    first_pin.setdefault(e[0], e)
by_name = {j["n"].lower(): i for i, j in enumerate(journal)}
for rec in items:
    if rec["c"] == "Bosses" and "p" not in rec:
        t = infos(rec["t"])[0]
        ji = jidx.get(t["internalId"]) if t["type"] == "journal" else by_name.get(rec["n"].lower())
        if ji in first_pin:
            e = first_pin[ji]
            rec["p"], rec["r"], rec["i"] = [e[1], e[2]], e[3], CATS["Bosses"]

meta = {"size": rooms["size"], "cell": best["cell"], "cols": best["cols"], "zones": labels["zones"], "labels": labels["labels"]}
with open(os.path.join(OUT, "data.js"), "w", encoding="utf8") as f:
    f.write("// Item list and save rules from Br3zzly/silksong-completionist (MIT); map, positions, enemies and names from the game files.\n")
    f.write("// Generated by tools/ss_build_data.py. Do not edit by hand.\n")
    f.write("window.SS = " + json.dumps({**meta, "items": items, "journal": journal, "enemies": epins}, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(len(items), "items,", sum(1 for i in items if "p" in i), "on the map,", len(journal), "journal entries,",
      len(epins), "enemy pins for", len({p[0] for p in epins}), "entries")
