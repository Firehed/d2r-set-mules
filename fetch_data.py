#!/usr/bin/env python3
"""Download the D2R game data files that build.py needs into data/.

Usage: python3 -I fetch_data.py [version]

Pulls from the @blizzhackers/d2data npm package (datamined D2R .txt files
converted to JSON). With no version, uses the latest published release.
Records the version and checksum in data/SOURCE.json.
"""
import hashlib
import io
import json
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

PACKAGE = "@blizzhackers/d2data"
# Paths inside the package tarball.
FILES = [
    "json/setitems.json", "json/sets.json",
    "json/armor.json", "json/weapons.json", "json/misc.json",
    "json/localestrings-eng.json",
    "LICENSE",
]
DATA = Path(__file__).resolve().parent / "data"


def get_json(url):
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "latest"
    meta = get_json(f"https://registry.npmjs.org/{PACKAGE}/{version}")
    dist = meta["dist"]
    print(f"Fetching {PACKAGE}@{meta['version']}")
    with urllib.request.urlopen(dist["tarball"]) as r:
        blob = r.read()
    if hashlib.sha1(blob).hexdigest() != dist["shasum"]:
        raise SystemExit("Checksum mismatch; refusing to use the download")

    DATA.mkdir(exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
        for name in FILES:
            member = tar.getmember(f"package/{name}")
            dest = DATA / Path(name).name
            with tar.extractfile(member) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            print(f"  data/{dest.name}")

    (DATA / "SOURCE.json").write_text(json.dumps({
        "package": PACKAGE,
        "version": meta["version"],
        "tarball": dist["tarball"],
        "shasum": dist["shasum"],
    }, indent=1) + "\n")


if __name__ == "__main__":
    main()
