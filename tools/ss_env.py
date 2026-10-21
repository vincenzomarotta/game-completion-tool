# Shared setup for reading Silksong assets with UnityPy.
import UnityPy
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Hollow Knight Silksong"
DATA = GAME + r"\Hollow Knight Silksong_Data"
AA = DATA + r"\StreamingAssets\aa\StandaloneWindows64"
_v = UnityPy.load(DATA + r"\globalgamemanagers").objects[0].assets_file.unity_version
UnityPy.config.FALLBACK_UNITY_VERSION = _v

def comps(go):
    out = {}
    for c in go.m_Components:
        r = (c.component if hasattr(c, "component") else c).deref()
        out.setdefault(r.type.name, []).append(r)
    return out
