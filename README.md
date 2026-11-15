# D2R Set Item Mules

Every Diablo II: Resurrected set item with its inventory size, plus a plan for
storing one of each across mule characters (10×10 stash + 10×4 inventory).

## Outputs

- `set_items.csv` / `set_items.json` — every set item: set, name, base, slot,
  size (cells), level requirement, Classic vs. expansion, and whether it drops.
- `mule_plan.json` — where each item goes: mule, grid, x/y (0-indexed from the
  top-left).
- `mules.html` — a viewer for the plan with search.

## Layout rules

- Each set is placed whole in a single grid (stash or inventory), never split.
- Sets are placed in alphabetical order, so each mule holds a contiguous
  A–Z range of sets.
- Sets that can't drop (currently Warlord's Glory) are listed but not placed.

## Regenerating after a patch

```sh
python3 -I fetch_data.py   # pull the latest game data into data/
python3 -I build.py        # rebuild every output
```

`fetch_data.py` takes an optional version (e.g. `3.4.95032`) to pin a release.
The version in use is recorded in `data/SOURCE.json`; check `git diff` after
regenerating to see what the patch changed. Adding sets will usually move
the sets that come after them alphabetically to different mules.

To change the grid sizes, edit `GRIDS` in `build.py`. The page's look lives in
`mules.template.html`; `build.py` fills in the data to produce `mules.html`.

## Data source

Game data is from [`@blizzhackers/d2data`](https://www.npmjs.com/package/@blizzhackers/d2data),
which converts the D2R data files to JSON (MIT licensed, see `data/LICENSE`).
Item sizes come from the base item's `invwidth`/`invheight`.
