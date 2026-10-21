# Game Completion Tool

Load your save file and see what's left for 100% completion, and where to find it. Everything runs in the browser: your save never leaves your computer. The site is in English and Italian.

Site: https://vincenzomarotta.github.io/game-completion-tool/

## Games

| Game | Folder | Save file | What it shows |
|---|---|---|---|
| Death's Door | `deaths-door/` | `Save_slotN.sav` in `%USERPROFILE%\AppData\LocalLow\Acid Nerve\DeathsDoor\SAVEDATA` | Shiny things, seeds, pots, shrines, soul orbs, tablets, by category or area |
| Hollow Knight | `hollow-knight/` | `userN.dat` in `%USERPROFILE%\AppData\LocalLow\Team Cherry\Hollow Knight` | Interactive map with item pins, Hunter's Journal |
| Hollow Knight: Silksong | `silksong/` | `userN.dat` in `%USERPROFILE%\AppData\LocalLow\Team Cherry\Hollow Knight Silksong\<id>` | Interactive map with item pins, Hunter's Journal |
| TUNIC | `tunic/` | the newest `.tunic` file in `%USERPROFILE%\AppData\LocalLow\Andrew Shouldice\Secret Legend\SAVES` | Chests, pages, fairies, secrets by region, with top-down mini maps |

## Data sources

- **Death's Door**: locations and save keys from [DeathsDoor.ItemChanger](https://github.com/dpinela/DeathsDoor.ItemChanger) (public domain).
- **Hollow Knight**: locations, save rules and pin art from [MapChanger](https://github.com/syyePhenomenol/MapChanger) and [RandomizerMod](https://github.com/homothetyhk/RandomizerMod); journal areas from [hollow-knight-completion-check](https://github.com/ReznoRMichael/hollow-knight-completion-check). The map, journal portraits, names and kill counts are read from the game files.
- **Silksong**: item list and save rules from [silksong-completionist](https://github.com/Br3zzly/silksong-completionist) (MIT). The map and item positions are read from the game files.
- **TUNIC**: locations and names from [TUNIC Randomizer](https://github.com/silent-destroyer/tunic-randomizer) (MIT). The Ruined Atoll key has no readable save flag and is listed as "check by hand".

## Regenerating the data

The scripts in `tools/` rebuild the generated files. They read the game install, so you need the games installed, plus Python with `UnityPy`, `TypeTreeGeneratorAPI`, `pycryptodome`, `dnfile` and `Pillow`. Run them from a folder that holds clones of the source repositories listed above.

- Hollow Knight: `hk_render_map.py` (map), `hk_build_data.py hollow-knight/data.js` (locations), `hk_kill_counts.py hk_kills.json` then `hk_build_bestiary.py hollow-knight` (journal).
- Silksong: export the silksong-completionist dictionary to `ss/dict.json`, then `ss_render_map.py` (map), `ss_scan_scenes.py` (object positions), `ss_build_assets.py silksong` (pins and journal portraits), `ss_build_data.py silksong` (items and journal).
- TUNIC: `tunic_build_data.py tunic/data.js [save.tunic]` (prints counts when given a save).

## Adding a game

Create a folder with its own `index.html`, use `i18n.js` for the two languages, and add a card to the home page (`index.html`).

## License

GPL-3.0 (see `LICENSE`). Fan project, not affiliated with the developers of these games. Game maps, portraits and names belong to their owners.
