# Bosses and arena enemies are recorded by FSMs (SetPlayerDataBool "killed<Name>"), not by EnemyDeathEffects.
# Find which scenes mention killed<Name>/kills<Name> for journal entries that have no placed enemy, so they can get a pin.
# Output hk_boss_scenes.json {journalId: [scene, ...]}.
import UnityPy, json, os, re

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Hollow Knight"
D = GAME + r"\hollow_knight_Data"
ggm = UnityPy.load(D + r"\globalgamemanagers")
bs = next(o for o in ggm.objects if o.type.name == "BuildSettings").read()
scenes = [s.split("/")[-1][:-6] for s in bs.scenes]

src = open("out_hk/bestiary.js", encoding="utf8").read()
entries = json.loads(src[src.index("{"):src.rstrip().rindex(";")])["entries"]
placed = set(json.load(open("hk_enemies.json")).keys())
have = {jid for hits in json.load(open("hk_enemies.json")).values() for jid, *_ in hits}
want = [e["id"] for e in entries if e["id"] not in have]
pats = {jid: re.compile(rb"\b(killed|kills)" + re.escape(jid.encode()) + rb"\b") for jid in want}

out = {}
for i, scene in enumerate(scenes):
    p = D + rf"\level{i}"
    if not os.path.exists(p):
        continue
    data = open(p, "rb").read()
    for jid, pat in pats.items():
        if pat.search(data):
            out.setdefault(jid, []).append(scene)
json.dump(out, open("hk_boss_scenes.json", "w"), indent=0)
print(len(want), "entries without pins;", len(out), "found in scenes")
print({k: v[:4] for k, v in out.items()})
print("still missing:", [j for j in want if j not in out])
