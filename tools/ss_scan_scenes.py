# For each scene the tracker needs: tilemap size + world position of the named objects (persistent item ids, flea cages).
# Output ss_scenes.json {scene: {"size": [w, h], "objs": {name: [x, y]}}}. Resumable: skips scenes already in the output.
import json, os, re, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from ss_env import *

SCN = AA + r"\scenes_scenes_scenes"
d = json.load(open("ss/dict.json"))
want = {}
def infos(p): return p if isinstance(p, list) else [p]
for cat in d:
    for s in cat["sections"]:
        for it in s["items"]:
            for p in infos(it["parsingInfo"]):
                if p["type"].startswith("sceneData"):
                    want.setdefault(p["internalId"][0], set()).add(p["internalId"][1])
                elif p["type"] == "flag" and p["internalId"].startswith("SavedFlea_"):
                    want.setdefault(p["internalId"][len("SavedFlea_"):], set()).add("*flea*")

out = json.load(open("ss_scenes.json")) if os.path.exists("ss_scenes.json") else {}
todo = [s for s in want if s not in out]
print(len(want), "scenes,", len(todo), "to scan", flush=True)

def world(tr_obj):
    x = y = 0.0
    sx = sy = 1.0
    chain = []
    t = tr_obj
    while t is not None:
        chain.append(t)
        t = t.m_Father.read() if t.m_Father.path_id else None
    for t in reversed(chain):          # root first; ignore rotation, good enough for map pins
        x += t.m_LocalPosition.x * sx
        y += t.m_LocalPosition.y * sy
        sx *= t.m_LocalScale.x
        sy *= t.m_LocalScale.y
    return [round(x, 2), round(y, 2)]

for n, scene in enumerate(todo):
    path = os.path.join(SCN, scene.lower() + ".bundle")
    rec = {"size": None, "objs": {}}
    if not os.path.exists(path):
        out[scene] = rec; print("missing bundle", scene, flush=True); continue
    try:
        env = UnityPy.load(path)
        names = want[scene]
        for o in env.objects:
            if o.type.name != "GameObject":
                continue
            name = o.peek_name()
            flea = "*flea*" in names and re.match(r"Flea Rescue|Flea_Cage|Caravan Flea|Flea", name or "")
            if name != "TileMap" and name not in names and not flea:
                continue
            go = o.read()
            c = comps(go)
            if name == "TileMap" and rec["size"] is None:
                for mb in c.get("MonoBehaviour", []):
                    try:
                        dd = mb.parse_as_dict()
                    except Exception:
                        continue
                    if "width" in dd and "height" in dd:
                        rec["size"] = [dd["width"], dd["height"]]
                        break
                continue
            t = (c.get("Transform") or c.get("RectTransform"))[0].read()
            key = "*flea*" if flea and name not in names else name
            rec["objs"].setdefault(key, world(t))
    except Exception as e:
        print("error", scene, e, flush=True)
    out[scene] = rec
    if n % 10 == 0:
        json.dump(out, open("ss_scenes.json", "w"))
        print(n, scene, rec["size"], len(rec["objs"]), "/", len(want[scene]), flush=True)
json.dump(out, open("ss_scenes.json", "w"))
print("done", flush=True)
