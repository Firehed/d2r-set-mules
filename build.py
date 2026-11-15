#!/usr/bin/env python3
"""Build the D2R set and unique item lists and their mule layout plans.

Usage: python3 -I build.py [data dir]

Reads the game data from data/ (see fetch_data.py) unless another directory
is given. Writes next to this script:
  set_items.{csv,json}     mule_plan.json          mules.html
  unique_items.{csv,json}  unique_mule_plan.json   uniques.html
  site/index.html, site/uniques.html (standalone copies for static hosting)
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

# Base item type code -> display label for uniques. The game's own type names
# for charms are off by one (cm2 "Large Charm" is typed mcha), so these are
# spelled out by hand. An unknown code fails the build: add it here and to
# UNIQUE_GROUPS.
UNIQUE_TYPES = {
    "helm": "Helm", "circ": "Circlet", "pelt": "Druid Pelt", "phlm": "Barbarian Helm",
    "tors": "Body Armor", "shie": "Shield",
    "ashd": "Paladin Shield", "head": "Necromancer Head", "grim": "Warlock Grimoire",
    "glov": "Gloves", "boot": "Boots", "belt": "Belt",
    "amul": "Amulet", "ring": "Ring", "jewl": "Jewel",
    "scha": "Small Charm", "mcha": "Large Charm", "lcha": "Grand Charm",
    "swor": "Sword", "axe": "Axe", "club": "Club", "mace": "Mace", "hamm": "Hammer",
    "scep": "Scepter", "pole": "Polearm", "spea": "Spear", "bow": "Bow", "xbow": "Crossbow",
    "staf": "Staff", "wand": "Wand", "knif": "Dagger",
    "jave": "Javelin", "taxe": "Throwing Axe", "tkni": "Throwing Knife",
    "abow": "Amazon Bow", "aspe": "Amazon Spear", "ajav": "Amazon Javelin",
    "h2h": "Assassin Katar", "h2h2": "Assassin Claw", "orb": "Sorceress Orb",
}

# Storage groups, in mule order. A group stays together on one mule when it
# fits; otherwise it splits by item tier across as many mules as it needs.
UNIQUE_GROUPS = [
    ("Helms & Circlets", ["helm", "circ", "pelt", "phlm"]),
    ("Body Armor", ["tors"]),
    ("Shields", ["shie"]),
    ("Class Shields", ["ashd", "head", "grim"]),
    ("Gloves, Boots & Belts", ["glov", "boot", "belt"]),
    ("Amulets, Rings & Jewels", ["amul", "ring", "jewl"]),
    ("Charms", ["scha", "mcha", "lcha"]),
    ("Swords", ["swor"]),
    ("Axes", ["axe"]),
    ("Clubs & Maces", ["club", "mace"]),
    ("Hammers", ["hamm"]),
    ("Scepters", ["scep"]),
    ("Polearms", ["pole"]),
    ("Spears", ["spea"]),
    ("Bows", ["bow"]),
    ("Crossbows", ["xbow"]),
    ("Staves", ["staf"]),
    ("Wands", ["wand"]),
    ("Daggers", ["knif"]),
    ("Throwing Weapons", ["jave", "taxe", "tkni"]),
    ("Class Weapons", ["abow", "aspe", "ajav", "h2h", "h2h2", "orb"]),
]
TIERS = ["Normal", "Exceptional", "Elite"]

FACET_ELEMENT = {"dmg-ltng": "Lightning", "dmg-cold": "Cold", "dmg-fire": "Fire", "dmg-pois": "Poison"}
FACET_TRIGGER = {"death-skill": "on death", "levelup-skill": "on level-up"}


def load(data_dir, name):
    return json.loads((data_dir / name).read_text(encoding="utf-8"))


class Data:
    def __init__(self, data_dir):
        self.dir = data_dir
        self.strings = load(data_dir, "localestrings-eng.json")
        # Newer items (Reign of the Warlock) only have names in allstrings.
        self.allstrings = load(data_dir, "allstrings-eng.json")
        self.bases = {}
        for f in ("weapons.json", "armor.json", "misc.json"):
            for b in load(data_dir, f).values():
                self.bases[b["code"]] = (f, b)

    def text(self, key, fallback=None):
        return self.strings.get(key) or self.allstrings.get(key) or fallback or key

    def base_name(self, code, base):
        return self.text(code, base["name"])


def tier_of(base):
    for tier, field in zip(TIERS, ("normcode", "ubercode", "ultracode")):
        if base.get(field) == base["code"]:
            return tier
    return None


def build_set_items(data):
    sets = load(data.dir, "sets.json")
    items = []
    for raw in load(data.dir, "setitems.json").values():
        src, base = data.bases[raw["item"]]
        slot = "Weapon" if src == "weapons.json" else TYPE_SLOT[base["type"]]
        set_key = raw["set"]
        items.append({
            "set": data.text(set_key),
            "name": data.text(raw["index"]),
            "base": data.base_name(raw["item"], base),
            "slot": slot,
            "width": base["invwidth"],
            "height": base["invheight"],
            "req_level": raw.get("lvl req"),
            "expansion": bool(sets[set_key].get("expansion")),
            "obtainable": raw.get("spawnable") == 1,
        })
    items.sort(key=lambda i: (i["set"].lower(), SLOT_ORDER.index(i["slot"]), i["name"]))
    return items


def facet_name(raw):
    props = [raw.get(f"prop{n}") for n in range(1, 13)]
    element = next(FACET_ELEMENT[p] for p in props if p in FACET_ELEMENT)
    trigger = next(FACET_TRIGGER[p] for p in props if p in FACET_TRIGGER)
    return f"{element}, {trigger}"


def build_unique_items(data):
    group_of = {code: g for g, codes in UNIQUE_GROUPS for code in codes}
    items = []
    for raw in load(data.dir, "uniqueitems.json").values():
        if raw.get("spawnable") != 1:
            continue
        _, base = data.bases[raw["code"]]
        code = base["type"]
        if code not in UNIQUE_TYPES or code not in group_of:
            raise SystemExit(f"Unknown item type {code!r} for {raw['index']}: add it to UNIQUE_TYPES and UNIQUE_GROUPS")
        items.append({
            "name": data.text(raw["index"]),
            "type": UNIQUE_TYPES[code],
            "group": group_of[code],
            "base": data.base_name(raw["code"], base),
            "tier": tier_of(base),
            "width": base["invwidth"],
            "height": base["invheight"],
            "req_level": raw.get("lvl req"),
            "_raw": raw,
        })

    # Rainbow Facets share one name across eight variants.
    seen = {}
    for it in items:
        seen.setdefault(it["name"], []).append(it)
    for name, dupes in seen.items():
        if len(dupes) > 1:
            for it in dupes:
                suffix = facet_name(it["_raw"]) if name == "Rainbow Facet" else it["base"]
                it["name"] = f"{name} ({suffix})"
    for it in items:
        del it["_raw"]

    order = {g: n for n, (g, _) in enumerate(UNIQUE_GROUPS)}
    types = list(UNIQUE_TYPES.values())
    items.sort(key=lambda i: (order[i["group"]], types.index(i["type"]),
                              TIERS.index(i["tier"]) if i["tier"] else 0, i["req_level"] or 0, i["name"]))
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

    def used(self):
        return sum(c is not None for row in self.cells for c in row)

    def snapshot(self):
        return [row[:] for row in self.cells]

    def restore(self, snap):
        self.cells = snap


BIG_FIRST = lambda i: (-i["width"] * i["height"], -i["height"])
TALL_FIRST = lambda i: (-i["height"], -i["width"])


def pack(grids, members, orders=(BIG_FIRST,), grid_orders=None):
    """Place every member somewhere in `grids`, or nothing at all.

    Tries each item order x grid order until one fits everything. Returns a
    list of (item, grid, (x, y)) or None.
    """
    for grid_order in grid_orders or [grids]:
        for order in orders:
            snaps = [g.snapshot() for g in grids]
            placed = []
            for item in sorted(members, key=order):
                for grid in grid_order:
                    pos = grid.find(item["width"], item["height"])
                    if pos is not None:
                        grid.put(*pos, item["width"], item["height"], item["name"])
                        placed.append((item, grid, pos))
                        break
                else:
                    break
            if len(placed) == len(members):
                return placed
            for g, s in zip(grids, snaps):
                g.restore(s)
    return None


def pack_hard(grids, members):
    """pack() with every heuristic; used where a tight fit matters."""
    return pack(grids, members, orders=(BIG_FIRST, TALL_FIRST), grid_orders=[grids, grids[::-1]])


def new_mule(mules):
    m = {"grids": [Grid(*g) for g in GRIDS], "groups": [], "placements": []}
    mules.append(m)
    return m


def record(mule, group, placed, key):
    if group not in mule["groups"]:
        mule["groups"].append(group)
    for item, grid, (x, y) in placed:
        mule["placements"].append({
            "group": group, "key": item[key], "name": item["name"], "grid": grid.name,
            "x": x, "y": y, "width": item["width"], "height": item["height"],
        })


def plan_set_mules(items):
    by_set = {}
    for it in items:
        if it["obtainable"]:
            by_set.setdefault(it["set"], []).append(it)

    mules = []
    mule = new_mule(mules)
    # Strict alphabetical order so each mule covers a contiguous A–Z range;
    # a set never splits across grids or mules.
    for set_name in sorted(by_set, key=str.lower):
        members = by_set[set_name]
        for attempt in range(2):
            placed = None
            for grid in mule["grids"]:
                placed = pack([grid], members)
                if placed:
                    break
            if placed:
                break
            mule = new_mule(mules)
        else:
            raise SystemExit(f"{set_name} does not fit on an empty mule")
        record(mule, set_name, placed, "set")
    return mules


def tier_label(chunk):
    tiers = [t for t in TIERS if any(i["tier"] == t for i in chunk)]
    if not tiers:
        return None
    return tiers[0] if len(tiers) == 1 else f"{tiers[0]}–{tiers[-1]}"


def plan_unique_mules(items):
    mules = []
    for group, _ in UNIQUE_GROUPS:
        remaining = [i for i in items if i["group"] == group]  # already tier-sorted
        chunks = []
        while remaining:
            # Whole (rest of the) group into the first mule with room for it.
            for m in mules:
                placed = pack_hard(m["grids"], remaining)
                if placed:
                    chunks.append((m, placed))
                    remaining = []
                    break
            if not remaining:
                break
            m = new_mule(mules)
            placed = pack_hard(m["grids"], remaining)
            if placed:
                chunks.append((m, placed))
                break
            # Too big for one mule: fill this one with the lowest tiers.
            for n in range(len(remaining) - 1, 0, -1):
                placed = pack_hard(m["grids"], remaining[:n])
                if placed:
                    chunks.append((m, placed))
                    remaining = remaining[n:]
                    break
        for n, (m, placed) in enumerate(chunks, 1):
            label = group
            if len(chunks) > 1:
                tiers = tier_label([p[0] for p in placed])
                label = f"{group} {n} of {len(chunks)}" + (f" ({tiers})" if tiers else "")
            record(m, label, placed, "type")
    return mules


def plan_json(mules, summary):
    return [{
        "mule": n,
        "summary": summary(m),
        "groups": m["groups"],
        "cells_used": {g.name: g.used() for g in m["grids"]},
        "placements": m["placements"],
    } for n, m in enumerate(mules, 1)]


def add_locations(items, plan):
    names = [i["name"] for i in items]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise SystemExit(f"Duplicate item names (locations would collide): {dupes}")
    spot = {p["name"]: (m["mule"], p) for m in plan for p in m["placements"]}
    for it in items:
        mule, p = spot.get(it["name"], (None, {}))
        it.update(mule=mule, grid=p.get("grid"),
                  col=p["x"] + 1 if p else None, row=p["y"] + 1 if p else None)


def write_lists(stem, items):
    (OUT / f"{stem}.json").write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    with open(OUT / f"{stem}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(items[0]))
        w.writeheader()
        w.writerows(items)


def page_items(items, group, note):
    return [{
        "name": i["name"], "group": i[group], "base": i["base"],
        "slot": i.get("slot") or i["type"], "width": i["width"], "height": i["height"],
        "req": i["req_level"], "note": note(i),
        "mule": i["mule"], "grid": i["grid"], "x": (i["col"] or 1) - 1, "y": (i["row"] or 1) - 1,
    } for i in items]


def render(template, page, items, plan, nav):
    grids = [{"name": n, "width": w, "height": h} for n, w, h in GRIDS]
    html = template.replace("<title>Item Mules</title>", f"<title>{page['title']}</title>")
    for key, value in (("PAGE", page), ("ITEMS", items), ("PLAN", {"grids": grids, "mules": plan}), ("NAV", nav)):
        html = html.replace(f"/*{key}*/", json.dumps(value, ensure_ascii=False))
    return html


def standalone(html):
    # mules.html and uniques.html are fragments that the Artifact viewer wraps
    # in its own document; static hosting needs the full thing.
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
            '</head>\n<body>\n' + html + '\n</body>\n</html>\n')


def main():
    if len(sys.argv) > 2:
        raise SystemExit(__doc__)
    data = Data(Path(sys.argv[1]) if len(sys.argv) == 2 else OUT / "data")
    grid_desc = " + ".join(f"{w}×{h} {n.lower()}" for n, w, h in GRIDS)
    template = (OUT / "mules.template.html").read_text(encoding="utf-8")

    # Sets
    set_items = build_set_items(data)
    set_plan = plan_json(plan_set_mules(set_items), lambda m: f"{m['groups'][0]} – {m['groups'][-1]}")
    add_locations(set_items, set_plan)
    write_lists("set_items", set_items)
    excluded = sorted({i["set"] for i in set_items if not i["obtainable"]})
    (OUT / "mule_plan.json").write_text(json.dumps({
        "grids": [{"name": n, "width": w, "height": h} for n, w, h in GRIDS],
        "excluded": excluded, "mules": set_plan,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    n_sets = len({i["set"] for i in set_items})
    set_page = {
        "title": "Set Item Mules", "mule": "Set Mule", "group": "Set", "note": "Version",
        "table": "Every set item", "stripOwner": True,
        "placeholder": "Find an item, set, or base (e.g. Tal Rasha, amulet, Shako)",
        "lede": f"{len(set_items)} set items across {n_sets} sets, packed onto {len(set_plan)} mules ({grid_desc}). "
                "Sets run in alphabetical order and each set stays whole in one grid."
                + (f" {', '.join(excluded)} is in the game files but has no drop source, so it is listed but not given space."
                   if excluded else ""),
    }

    # Uniques
    uniq_items = build_unique_items(data)
    uniq_plan = plan_json(plan_unique_mules(uniq_items), lambda m: " · ".join(m["groups"]))
    add_locations(uniq_items, uniq_plan)
    write_lists("unique_items", uniq_items)
    (OUT / "unique_mule_plan.json").write_text(json.dumps({
        "grids": [{"name": n, "width": w, "height": h} for n, w, h in GRIDS], "mules": uniq_plan,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    uniq_page = {
        "title": "Unique Item Mules", "mule": "Unique Mule", "group": "Group", "note": "Tier",
        "table": "Every unique item", "stripOwner": False,
        "placeholder": "Find an item, type, or base (e.g. Harlequin Crest, ring, Archon Plate)",
        "lede": f"{len(uniq_items)} unique items that can drop, packed onto {len(uniq_plan)} mules ({grid_desc}). "
                "Each item class stays on one mule when it fits; classes too big for one mule split by tier.",
    }

    pages = [
        ("mules", "index.html", set_page, page_items(set_items, "set", lambda i: "" if i["expansion"] else "Classic"), set_plan),
        ("uniques", "uniques.html", uniq_page, page_items(uniq_items, "group", lambda i: i["tier"] or ""), uniq_plan),
    ]
    site = OUT / "site"
    site.mkdir(exist_ok=True)
    for stem, site_name, page, items, plan in pages:
        (OUT / f"{stem}.html").write_text(render(template, page, items, plan, []), encoding="utf-8")
        nav = [{"href": s, "label": p["title"], "current": s == site_name} for _, s, p, _, _ in pages]
        (site / site_name).write_text(standalone(render(template, page, items, plan, nav)), encoding="utf-8")

    for label, items, plan in (("set", set_items, set_plan), ("unique", uniq_items, uniq_plan)):
        print(f"{len(items)} {label} items -> {len(plan)} mules")
        for m in plan:
            print(f"  {m['mule']:>2}: {m['summary']}  {m['cells_used']}")


if __name__ == "__main__":
    main()
