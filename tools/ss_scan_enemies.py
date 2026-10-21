# Find every enemy placed in Silksong scenes: components with a journalRecord pointing at an EnemyJournalRecord asset.
# Output ss_enemies.json {scene: {"size": [w, h] | null, "hits": [[journalId, x, y], ...]}}.
import json, os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from ss_env import *

rec = UnityPy.load(AA + r"\dataassets_assets_assets\dataassets\enemyjournal\journalrecords.bundle")
RCAB = next(iter(next(iter(rec.files.values())).files)).lower()
R = {o.path_id: o.read().m_Name for o in rec.objects if o.type.name == "MonoBehaviour"}
SCN = AA + r"\scenes_scenes_scenes"

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
files = sorted(f for f in os.listdir(SCN) if f.endswith(".bundle"))
for n, f in enumerate(files):
    try:
        env = UnityPy.load(os.path.join(SCN, f))
    except Exception as e:
        print("skip", f, e, flush=True); continue
    scene, size, hits = None, None, []
    for o in env.objects:
        if o.type.name == "GameObject" and size is None and o.peek_name() == "TileMap":
            for mb in comps(o.read()).get("MonoBehaviour", []):
                try:
                    d = mb.parse_as_dict()
                except Exception:
                    continue
                if "width" in d and "height" in d:
                    size = [d["width"], d["height"]]; break
        if o.type.name != "MonoBehaviour":
            continue
        ri = {i + 1 for i, e in enumerate(o.assets_file.externals) if RCAB in e.path.lower()}
        if not ri:
            continue
        try:
            d = o.parse_as_dict()
        except Exception:
            continue
        jr = d.get("journalRecord")
        if not (isinstance(jr, dict) and jr.get("m_FileID") in ri and jr.get("m_PathID") in R):
            continue
        try:
            go = o.read().m_GameObject.read()
            c = comps(go)
            hits.append([R[jr["m_PathID"]], *world((c.get("Transform") or c.get("RectTransform"))[0].read())])
        except Exception:
            pass
    name = f[:-7]
    out[name] = {"size": size, "hits": hits}
    if n % 50 == 0:
        print(n, name, size, len(hits), flush=True)
json.dump(out, open("ss_enemies.json", "w"))
print("done", len(out), "scenes", sum(len(v["hits"]) for v in out.values()), "enemies", flush=True)
