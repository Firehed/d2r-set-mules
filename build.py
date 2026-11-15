#!/usr/bin/env python3
"""Build the D2R set-item list and a mule layout plan.

Usage: python3 -I build.py [data dir]

Reads the game data from data/ (see fetch_data.py) unless another directory
is given. Writes set_items.csv, set_items.json, mule_plan.json and mules.html
next to this script.
"""
import csv
import json
import sys
from pathlib import Path

GRIDS = [("Stash", 10, 10), ("Inventory", 10, 4)]  # name, width, height
OUT = Path(__file__).resolve().parent

# Base item type code -> slot label used for display and ordering within a set.
SLOT_ORDER = ["Helm", "Armor", "Weapon", "Shield", "Gloves", "Belt", "Boots", "Amulet", "Ring"]
TYPE_SLOT = {
    "helm": "Helm", "circ": "Helm", "pelt": "Helm", "phlm": "Helm",
    "tors": "Armor", "glov": "Gloves", "belt": "Belt", "boot": "Boots",
    # head = Necromancer shrunken head, grim = Warlock grimoire
    "shie": "Shield", "ashd": "Shield", "head": "Shield", "grim": "Shield",
    "amul": "Amulet", "ring": "Ring",
}


def load(data_dir, name):
    return json.loads((data_dir / name).read_text(encoding="utf-8"))


def build_items(data_dir):
    strings = load(data_dir, "localestrings-eng.json")
    bases = {}
    for f in ("weapons.json", "armor.json", "misc.json"):
        for b in load(data_dir, f).values():
            bases[b["code"]] = (f, b)
    sets = load(data_dir, "sets.json")

    items = []
    for raw in load(data_dir, "setitems.json").values():
        src, base = bases[raw["item"]]
        slot = "Weapon" if src == "weapons.json" else TYPE_SLOT[base["type"]]
        set_key = raw["set"]
        items.append({
            "set": strings.get(set_key) or set_key,
            "name": strings.get(raw["index"]) or raw["index"],
            "base": strings.get(raw["item"]) or raw.get("*ItemName") or base["name"],
            "slot": slot,
            "width": base["invwidth"],
            "height": base["invheight"],
            "req_level": raw.get("lvl req"),
            "expansion": bool(sets[set_key].get("expansion")),
            "obtainable": raw.get("spawnable") == 1,
        })
    items.sort(key=lambda i: (i["set"].lower(), SLOT_ORDER.index(i["slot"]), i["name"]))
    return items


class Grid:
    def __init__(self, name, w, h):
        self.name, self.w, self.h = name, w, h
        self.cells = [[None] * w for _ in range(h)]

    def find(self, iw, ih):
        # Column-major first fit: fills left-to-right in vertical bands, which
        # keeps each set in a tidy cluster instead of a long horizontal smear.
        for x in range(self.w - iw + 1):
            for y in range(self.h - ih + 1):
                if all(self.cells[y + dy][x + dx] is None
                       for dy in range(ih) for dx in range(iw)):
                    return x, y
        return None

    def put(self, x, y, iw, ih, tag):
        for dy in range(ih):
            for dx in range(iw):
                self.cells[y + dy][x + dx] = tag

    def snapshot(self):
        return [row[:] for row in self.cells]

    def restore(self, snap):
        self.cells = snap


def try_place_set(grid, members):
    """Place every item of a set into one grid, or nothing at all."""
    snap = grid.snapshot()
    placed = []
    # Big items first packs much tighter.
    for item in sorted(members, key=lambda i: (-i["width"] * i["height"], -i["height"])):
        pos = grid.find(item["width"], item["height"])
        if pos is None:
            grid.restore(snap)
            return None
        grid.put(*pos, item["width"], item["height"], item["name"])
        placed.append((item, pos))
    return placed


def plan_mules(items):
    by_set = {}
    for it in items:
        if it["obtainable"]:
            by_set.setdefault(it["set"], []).append(it)

    mules = []

    def new_mule():
        m = {"grids": [Grid(*g) for g in GRIDS], "sets": [], "placements": []}
        mules.append(m)
        return m

    mule = new_mule()
    # Strict alphabetical order so each mule covers a contiguous A–Z range;
    # a set never splits across grids or mules.
    for set_name in sorted(by_set, key=str.lower):
        members = by_set[set_name]
        for attempt in range(2):
            placed = None
            for grid in mule["grids"]:
                placed = try_place_set(grid, members)
                if placed:
                    break
            if placed:
                break
            mule = new_mule()
        else:
            raise SystemExit(f"{set_name} does not fit on an empty mule")
        mule["sets"].append(set_name)
        for item, (x, y) in placed:
            mule["placements"].append({
                "set": set_name, "name": item["name"], "grid": grid.name,
                "x": x, "y": y, "width": item["width"], "height": item["height"],
            })

    out = []
    for n, m in enumerate(mules, 1):
        used = {g.name: sum(c is not None for row in g.cells for c in row) for g in m["grids"]}
        out.append({
            "mule": n,
            "range": f"{m['sets'][0]} – {m['sets'][-1]}",
            "sets": m["sets"],
            "cells_used": used,
            "placements": m["placements"],
        })
    return out


def main():
    if len(sys.argv) > 2:
        raise SystemExit(__doc__)
    data_dir = Path(sys.argv[1]) if len(sys.argv) == 2 else OUT / "data"
    items = build_items(data_dir)

    (OUT / "set_items.json").write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    with open(OUT / "set_items.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(items[0]))
        w.writeheader()
        w.writerows(items)

    plan = {
        "grids": [{"name": n, "width": w, "height": h} for n, w, h in GRIDS],
        "excluded": sorted({i["set"] for i in items if not i["obtainable"]}),
        "mules": plan_mules(items),
    }
    (OUT / "mule_plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    html = (OUT / "mules.template.html").read_text(encoding="utf-8")
    html = html.replace("/*ITEMS*/", json.dumps(items, ensure_ascii=False))
    html = html.replace("/*PLAN*/", json.dumps(plan, ensure_ascii=False))
    (OUT / "mules.html").write_text(html, encoding="utf-8")
    # Standalone copy for static hosting (GitHub Pages); mules.html is a
    # fragment that the Artifact viewer wraps in its own document.
    site = OUT / "site"
    site.mkdir(exist_ok=True)
    (site / "index.html").write_text(
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
        '</head>\n<body>\n' + html + '\n</body>\n</html>\n',
        encoding="utf-8",
    )
    plan = plan["mules"]

    sets = {i["set"] for i in items}
    print(f"{len(items)} set items in {len(sets)} sets -> {len(plan)} mules")
    for m in plan:
        print(f"  Mule {m['mule']}: {m['range']}  {m['cells_used']}")


if __name__ == "__main__":
    main()
