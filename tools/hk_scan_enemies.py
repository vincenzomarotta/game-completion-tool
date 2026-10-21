# Find every enemy placed in Hollow Knight scenes: EnemyDeathEffects.playerDataName (the journal entry) + world position.
# Output hk_enemies.json {scene: [[journalId, x, y], ...]}.
import UnityPy, json
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Hollow Knight"
D = GAME + r"\hollow_knight_Data"
ggm = UnityPy.load(D + r"\globalgamemanagers")
bs = next(o for o in ggm.objects if o.type.name == "BuildSettings").read()
scenes = [s.split("/")[-1][:-6] for s in bs.scenes]
gen = TypeTreeGenerator(ggm.objects[0].assets_file.unity_version)
gen.load_local_game(GAME)

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
for i, scene in enumerate(scenes):
    try:
        env = UnityPy.load(D + rf"\level{i}")
    except Exception as e:
        print("skip", scene, e); continue
    env.typetree_generator = gen
    hits = []
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            d = o.parse_as_dict()
        except Exception:
            continue
        if d.get("playerDataName") and "corpsePrefab" in d:
            try:
                go = o.read().m_GameObject.read()
                tr = next(c for c in (x.component if hasattr(x, "component") else x for x in go.m_Components) if c.deref().type.name in ("Transform", "RectTransform")).read()
                hits.append([d["playerDataName"], *world(tr)])
            except Exception:
                pass
    if hits:
        out[scene] = hits
    if i % 50 == 0:
        print(i, scene, len(hits), flush=True)
json.dump(out, open("hk_enemies.json", "w"))
print("done", len(out), "scenes", sum(len(v) for v in out.values()), "enemies")
