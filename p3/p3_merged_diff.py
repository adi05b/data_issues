"""Problem 3: elect every merged site from an offline merge run, as
p5/p5_load_kgrel.py does, and write {merged site id: [coordinates, a hash of
every other field]} to JSON.
Run it once per build with that build's code, then compare the two files:

    CFG_FILE=<kg>/tests/resources/config.yml PYTHONPATH=<kg> \\
      .venv-p2/bin/python p3_merged_diff.py elect <run dir> <out.json>
    python3 p3_merged_diff.py diff <main.json> <branch.json> <listed.csv>

`diff` counts the merged sites whose coordinate changes, checks each against
the listed change (out/verify_p3_local_changes.csv), and counts changes to any
other field. Nothing touches a database.
"""

import json
import sys


def elect(run, out):
    import hashlib
    import inspect
    from pathlib import Path
    from types import SimpleNamespace

    import serde.json
    from minmodkg.models.kgrel.dedup_mineral_site import DedupMineralSite
    from minmodkg.models.kgrel.mineral_site import MineralSite
    from minmodkg.services.kgrel_entity import FileEntityService

    run = Path(run)
    args = {"is_site_ranked": True}
    if "crs_names" in inspect.signature(DedupMineralSite.from_dedup_sites).parameters:
        args["crs_names"] = FileEntityService(run / "data/entities").get_crs_name()
    partials, members = {}, {}
    for p in sorted((run / "data/mineral-sites/merged").glob("*/*")):
        d = serde.json.deser(p)
        for x in d["DedupMineralSite"]:
            partials.setdefault(x["id"], []).append(x)
        for m in d["MineralSiteAndInventory"]:
            ms = MineralSite.from_dict(m["ms"])
            members[ms.site_id] = SimpleNamespace(
                site_id=ms.site_id, location=ms.location, location_view=ms.location_view
            )
    result = {}
    for e, lst in partials.items():
        dms_lst = [DedupMineralSite.from_dict(x) for x in lst]
        sites = [
            SimpleNamespace(ms=members[r.site_id], invs=[])
            for dms in dms_lst
            for r in dms.ranked_sites
        ]
        merged = DedupMineralSite.from_dedup_sites(dms_lst, sites, **args).dms.to_dict()
        merged.pop("modified_at", None)
        coord = merged.pop("coordinates", None)
        rest = json.dumps(merged, sort_keys=True, default=str).encode()
        result[e] = [coord, hashlib.sha1(rest).hexdigest()]
    Path(out).write_text(json.dumps(result, sort_keys=True))
    print(f"{len(result)} merged sites -> {out}")


def diff(main_json, branch_json, listed_csv):
    import collections
    import csv

    a, b = json.load(open(main_json)), json.load(open(branch_json))
    assert a.keys() == b.keys(), "the builds have different merged sites"
    listed = {r["dedup_site_id"]: r for r in csv.DictReader(open(listed_csv))}
    changed = {e: (a[e][0], b[e][0]) for e in a if a[e][0] != b[e][0]}
    other = sum(a[e][1] != b[e][1] for e in a)
    reasons = collections.Counter(listed[e]["reason"] for e in changed if e in listed)
    as_listed = sum(
        e in listed
        and (cb and cb["refid"]) == (listed[e]["new_site_id"] or None)
        and (ca and ca["refid"]) == listed[e]["old_site_id"]
        for e, (ca, cb) in changed.items()
    )
    print(f"merged sites: {len(a):,}")
    print(f"coordinate changed: {len(changed):,} ({dict(reasons)})")
    print(f"changed but not listed: {sum(e not in listed for e in changed)}")
    print(f"listed but not changed: {sum(e not in changed for e in listed)}")
    print(f"changed from the listed old record to the listed new one: {as_listed}")
    print(f"another field changed: {other}")


if __name__ == "__main__":
    {"elect": elect, "diff": diff}[sys.argv[1]](*sys.argv[2:])
