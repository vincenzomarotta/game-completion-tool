# Extract Silksong pin icons (inventory atlas) and Hunter's Journal portraits (journal_enemy_icons atlas).
# Output into argv[1]: pins/<key>.png, bestiary.webp (sheet) and bestiary_index.json {journalId: cellIndex}.
import json, os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from ss_env import *
from PIL import Image

OUT = sys.argv[1]
A = AA + r"\atlases_assets_assets\sprites\_atlases"
PINS = {
    "mask": "Hornet_T_fractured_mask", "spool": "Hornet_Spool_Upgrade_Shop_Icon", "locket": "Hornet_icon_0005_R_saint_locket",
    "metal": "Hornet_Tool_Metal", "berry": "I_moss_berry", "core": "Icon_Pristine_Core", "silkeater": "Silk_Grub_Suck_no_cocoon0000",
    "rosary": "I_rosary_necklace_0002_1", "shard": "I_shell_shard_icon_large", "wall": "I_map", "void": "Hornet_icon_0004_R_ancient_egg",
    "beast": "Icon_Beast_Shard", "key": "I_slab_key", "flea": "QI_Flea", "token": "Hornet_bellway_token",
    "tool": "T_straight_pin", "ability": "Inv_0029_spell_core_outer_icons_0000_1_harpoon_dash", "crest": "Hornet_Inv_pane_icons_0001_crest",
    "relic": "Hornet_icon_0002_R_weaver_record", "wish": "Hornet_Inv_pane_icons_0002_wish", "bellway": "pin_stag_station_shop_icon",
    "tube": "pin_tube_station_shop_icon", "quill": "I_quill_and_map", "bellhome": "pin_bench_shop_icon", "materium": "icon_silk_materium",
    "memento": "surface_memento", "boss": "Kill_quest_icon",
}
env = UnityPy.load(A + r"\inventory.spriteatlas.bundle")
sp = {o.peek_name(): o for o in env.objects if o.type.name == "Sprite"}
os.makedirs(os.path.join(OUT, "pins"), exist_ok=True)
for key, name in PINS.items():
    im = sp[name].read().image.convert("RGBA")
    im = im.crop(im.getbbox())
    im.thumbnail((56, 56), Image.LANCZOS)
    im.save(os.path.join(OUT, "pins", key + ".png"), optimize=True)

CELL, COLS = 96, 16
env = UnityPy.load(A + r"\journal_enemy_icons.spriteatlas.bundle")
icons = sorted((o.peek_name(), o) for o in env.objects if o.type.name == "Sprite")
rows = (len(icons) + COLS - 1) // COLS
sheet = Image.new("RGBA", (COLS * CELL, rows * CELL), (0, 0, 0, 0))
index = {}
for n, (name, o) in enumerate(icons):
    im = o.read().image.convert("RGBA")
    im = im.crop(im.getbbox() or (0, 0, im.width, im.height))
    im.thumbnail((CELL - 4, CELL - 4), Image.LANCZOS)
    sheet.alpha_composite(im, ((n % COLS) * CELL + (CELL - im.width) // 2, (n // COLS) * CELL + (CELL - im.height) // 2))
    index[name.removesuffix(".png")] = n
sheet.save(os.path.join(OUT, "bestiary.webp"), quality=85, method=6)
json.dump({"cell": CELL, "cols": COLS, "index": index}, open("ss_bestiary_index.json", "w"))
print(len(PINS), "pins,", len(icons), "portraits")
