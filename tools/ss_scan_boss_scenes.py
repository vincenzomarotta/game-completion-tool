# Bosses and scripted enemies point at their EnemyJournalRecord from FSM/other components rather than a journalRecord
# field. For journal entries without a placed enemy, find the scenes whose components reference the record anywhere.
# Output ss_boss_scenes.json {journalId: [[scene, x, y], ...]} (x/y = position of the referencing object).
import json, os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from ss_env import *

rec = UnityPy.load(AA + r"\dataassets_assets_assets\dataassets\enemyjournal\journalrecords.bundle")
RCAB = next(iter(next(iter(rec.files.values())).files)).lower()
R = {o.path_id: o.read().m_Name for o in rec.objects if o.type.name == "MonoBehaviour"}
_d = open(sys.argv[1], encoding="utf8").read()  # silksong/data.js: entries that already have a map pin
_d = json.loads(_d[_d.index("{"):_d.rstrip().rindex(";")])
placed = {_d["journal"][p[0]]["id"] for p in _d["enemies"]}
want = {pid: n for pid, n in R.items() if n not in placed}
print(len(want), "entries to look for", flush=True)
SCN = AA + r"\scenes_scenes_scenes"

def refs(v, ri):
    if isinstance(v, dict):
        if v.get("m_FileID") in ri and v.get("m_PathID") in want:
            yield want[v["m_PathID"]]
        for x in v.values():
            yield from refs(x, ri)
    elif isinstance(v, list):
        for x in v:
            yield from refs(x, ri)

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
for n, f in enumerate(sorted(os.listdir(SCN))):
    if not f.endswith(".bundle"):
        continue
    try:
        env = UnityPy.load(os.path.join(SCN, f))
    except Exception:
        continue
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        ri = {i + 1 for i, e in enumerate(o.assets_file.externals) if RCAB in e.path.lower()}
        if not ri:
            continue
        try:
            d = o.parse_as_dict()
        except Exception:
            continue
        names = set(refs(d, ri))
        if not names:
            continue
        try:
            c = comps(o.read().m_GameObject.read())
            pos = world((c.get("Transform") or c.get("RectTransform"))[0].read())
        except Exception:
            pos = (None, None)
        for nm in names:
            out.setdefault(nm, []).append([f[:-7], *pos])
    if n % 100 == 0:
        print(n, f, len(out), flush=True)
json.dump(out, open("ss_boss_scenes.json", "w"), indent=0)
print("found", len(out), "of", len(want), "; missing:", sorted(set(want.values()) - set(out)), flush=True)
