# D2R Set Item Mules

Every Diablo II: Resurrected set and unique item with its inventory size,
plus a plan for storing one of each across mule characters (10×10 stash +
10×4 inventory). Set items and uniques use separate mule series.

## Outputs

- `set_items.csv` / `set_items.json` — every set item: set, name, base, slot,
  size (cells), level requirement, Classic vs. expansion, whether it drops,
  and where it goes (mule, grid, 1-indexed col/row).
- `unique_items.csv` / `unique_items.json` — every unique that can drop: name,
  type, storage group, base, tier, size, level requirement, and location.
- `mule_plan.json` / `unique_mule_plan.json` — each mule's contents with
  0-indexed x/y from the top-left of each grid.
- `mules.html` / `uniques.html` — viewers for each plan with search.

## Layout rules

Sets:
- Each set is placed whole in a single grid (stash or inventory), never split.
- Sets are placed in alphabetical order, so each mule holds a contiguous
  A–Z range of sets.
- Sets that can't drop (currently Warlord's Glory) are listed but not placed.

Uniques:
- Items are grouped by class (`UNIQUE_GROUPS` in `build.py`); small related
  classes share a group, e.g. Gloves, Boots & Belts.
- Each group goes whole onto the first mule with room for it, so small groups
  fill gaps left by bigger ones.
- Groups too big for one mule (body armor, swords, axes, polearms) split by
  tier, lowest first, and are labeled "1 of 2", "2 of 2".
- A new item type in a future patch stops the build with a message saying
  where to add it.

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
`mules.template.html`; `build.py` fills in the data to produce both pages.

## Hosting

`build.py` also writes `site/index.html` and `site/uniques.html`, standalone
copies of the viewers with links between them.
On every push to `main`, `.github/workflows/pages.yml` runs the build and
deploys `site/` to GitHub Pages (enable Pages with source "GitHub Actions").

## Data source

Game data is from [`@blizzhackers/d2data`](https://www.npmjs.com/package/@blizzhackers/d2data),
which converts the D2R data files to JSON (MIT licensed, see `data/LICENSE`).
Item sizes come from the base item's `invwidth`/`invheight`.
