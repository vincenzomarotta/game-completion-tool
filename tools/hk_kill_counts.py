# Read the default "kills<Enemy>" values (journal kill requirements) from PlayerData.SetupNewPlayerData() IL in Assembly-CSharp.dll.
import dnfile, struct, json, sys
dll = r"C:\Program Files (x86)\Steam\steamapps\common\Hollow Knight\hollow_knight_Data\Managed\Assembly-CSharp.dll"
pe = dnfile.dnPE(dll)
md = pe.net.mdtables
pd = next(t for t in md.TypeDef.rows if str(t.TypeName) == "PlayerData")
setup = next(m.row for m in pd.MethodList if str(m.row.Name) == "SetupNewPlayerData")
size = struct.unpack_from("<I", pe.get_data(setup.Rva, 12), 4)[0]  # fat method header
code = pe.get_data(setup.Rva + 12, size)
out = {}
i = 0
while i < len(code) - 6:
    op, val, n = code[i], None, 0
    if 0x16 <= op <= 0x1E: val, n = op - 0x16, 1
    elif op == 0x15: val, n = -1, 1
    elif op == 0x1F: val, n = struct.unpack_from("<b", code, i + 1)[0], 2
    elif op == 0x20: val, n = struct.unpack_from("<i", code, i + 1)[0], 5
    if n and code[i + n] == 0x7D:
        tok = struct.unpack_from("<I", code, i + n + 1)[0]
        if tok >> 24 == 0x04:
            name = str(md.Field.rows[(tok & 0xFFFFFF) - 1].Name)
            if name.startswith("kills"):
                out[name] = val
        i += n + 5
        continue
    i += 1
json.dump(out, open(sys.argv[1], "w"), indent=0)
print(len(out), {k: out[k] for k in list(out)[:8]})
