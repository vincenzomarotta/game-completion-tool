# Game Completion Tool

Carica il salvataggio di un gioco e scopri cosa ti manca per il 100% e dove trovarlo. Tutto gira nel browser: il file non viene caricato da nessuna parte. Interfaccia in italiano e inglese.

Sito: https://vincenzomarotta.github.io/game-completion-tool/

## Giochi

- **Death's Door** (`deaths-door/`): legge `Save_slotN.sav` da `%USERPROFILE%\AppData\LocalLow\Acid Nerve\DeathsDoor\SAVEDATA`. Posizioni e chiavi del salvataggio da [DeathsDoor.ItemChanger](https://github.com/dpinela/DeathsDoor.ItemChanger) (pubblico dominio).
- **Hollow Knight** (`hollow-knight/`): legge `userN.dat` da `%USERPROFILE%\AppData\LocalLow\Team Cherry\Hollow Knight`, con mappa interattiva. Posizioni e regole del salvataggio da [MapChanger](https://github.com/syyePhenomenol/MapChanger) e [RandomizerMod](https://github.com/homothetyhk/RandomizerMod) (GPL/LGPL). La mappa è composta dalle stanze della mappa di gioco di Team Cherry.
- **Tunic** (`tunic/`): legge il file `.tunic` più recente da `%USERPROFILE%\AppData\LocalLow\Andrew Shouldice\Secret Legend\SAVES`, con una mini-mappa vista dall'alto per regione. Posizioni e nomi da [TUNIC Randomizer](https://github.com/silent-destroyer/tunic-randomizer) (MIT). La chiave dell'Atoll non ha un flag leggibile nel salvataggio e va controllata a mano.

## Rigenerare i dati di Hollow Knight

Gli script in `tools/` vanno lanciati da una cartella che contiene i cloni di MapChanger, RandomizerMod e HollowKnight.ItemChanger sotto `hk/`, con il gioco installato (serve `UnityPy` e `Pillow`):

1. `python hk_render_map.py`: compone `hk_map.webp` e `hk_rooms.json` dai file del gioco.
2. `python hk_build_data.py hollow-knight/data.js`: genera i dati delle posizioni.

## Rigenerare i dati di Tunic

`python tools/tunic_build_data.py tunic/data.js [salvataggio.tunic]` da una cartella con il clone di tunic-randomizer sotto `tunic/`. Con un salvataggio come secondo argomento stampa anche i conteggi, utile per controllare.

## Aggiungere un gioco

Crea una cartella con il suo `index.html`, usa `i18n.js` per le due lingue e aggiungi una card nella home (`index.html`).

## Licenza

GPL-3.0 (vedi `LICENSE`). Progetto amatoriale, non affiliato con gli sviluppatori dei giochi.
