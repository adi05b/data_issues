"""Problem 2 review (#110): elect every merged site from an offline merge run,
as p5/p5_load_kgrel.py does, and write {merged site id: [countries, states]}
to JSON. Run it once per build with that build's code, then compare two:

    CFG_FILE=<kg>/tests/resources/config.yml PYTHONPATH=<kg> \\
      <venv>/bin/python p2_review_diff.py elect <run dir> <out.json>
    python3 p2_review_diff.py diff <run dir>/data/entities <a.json> <b.json>
    <venv>/bin/python p2_review_diff.py records <run a> <run b>

`diff` counts, per build, merged sites with a country, with a state, and with
a state in none of their countries; then the sites whose country or state
differs between the two. `records` counts the records whose location view
differs between two runs. Nothing touches a database.
"""

import json
import sys


def elect(run, out):
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
        dms = DedupMineralSite.from_dedup_sites(dms_lst, sites, **args).dms
        result[e] = [dms.country.value, dms.state_or_province.value]
    Path(out).write_text(json.dumps(result, sort_keys=True))
    print(f"{len(result)} merged sites -> {out}")


def diff(entity_dir, a_json, b_json):
    import collections
    from pathlib import Path

    states = json.loads((Path(entity_dir) / "state_or_province.json").read_text())
    owner = {s["id"]: s.get("country") for s in states["StateOrProvince"]}
    a, b = json.load(open(a_json)), json.load(open(b_json))
    assert a.keys() == b.keys(), "the builds have different merged sites"

    def conflicted(countries, sts):
        return len(countries) > 0 and any(
            owner.get(s) is not None and owner[s] not in countries for s in sts
        )

    for name, r in (("a", a), ("b", b)):
        print(
            f"{name}: merged {len(r):,}, with a country "
            f"{sum(len(c) > 0 for c, _ in r.values()):,}, with a state "
            f"{sum(len(s) > 0 for _, s in r.values()):,}, state in another "
            f"country {sum(conflicted(c, s) for c, s in r.values()):,}"
        )
    what = collections.Counter()
    examples = collections.defaultdict(list)
    for e in a:
        (ca, sa), (cb, sb) = a[e], b[e]
        if ca == cb and sa == sb:
            continue
        if ca != cb:
            kind = "country changed"
        elif not sb:
            kind = "state emptied"
        elif not sa:
            kind = "state filled"
        else:
            kind = "state changed"
        what[kind] += 1
        if len(examples[kind]) < 3:
            examples[kind].append((e, a[e], b[e]))
    print(f"changed: {sum(what.values()):,} {dict(sorted(what.items()))}")
    for kind, lst in sorted(examples.items()):
        for e, va, vb in lst:
            print(f"  {kind}: {e} {va} -> {vb}")


def records(run_a, run_b):
    """Records (not merged sites) whose location view differs between two runs,
    and how many of them only lost a duplicate state."""
    from pathlib import Path

    import serde.json

    def views(run):
        out = {}
        for p in sorted((Path(run) / "data/mineral-sites/merged").glob("*/*")):
            for m in serde.json.deser(p)["MineralSiteAndInventory"]:
                v = m["ms"].get("location_view", {})
                out[m["ms"]["site_id"]] = (
                    v.get("country", []),
                    v.get("state_or_province", []),
                )
        return out

    a, b = views(run_a), views(run_b)
    assert a.keys() == b.keys(), "the runs have different records"
    changed = [k for k in a if a[k] != b[k]]
    dup = sum(
        a[k][0] == b[k][0] and list(dict.fromkeys(a[k][1])) == b[k][1] for k in changed
    )
    print(f"records: {len(a):,}, location view changed: {len(changed):,}")
    print(f"  of which only a duplicate state removed: {dup:,}")
    for k in changed[:5]:
        print(f"  {k}: {a[k]} -> {b[k]}")


if __name__ == "__main__":
    {"elect": elect, "diff": diff, "records": records}[sys.argv[1]](*sys.argv[2:])
