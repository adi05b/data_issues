#!/usr/bin/env python3
"""Problem 3: check the Null Island fix and the precision tie-break against a kgrel database.

What it checks. For every merged site (dedup_mineral_site) with 2 or more member
records, the coordinate is elected again in memory with the checked-out code and
compared with the one stored in the database:

  before   the coordinate stored on the merged site today;
  control  re-elected with both Problem 3 steps bypassed. It must equal `before`
           for every site; otherwise the database was built from other code or
           data, and the script says so and stops (exit code 2);
  after    re-elected with both steps on: each member's location view recomputed
           with LocationView.from_location (Null Island rule), then
           DedupMineralSite.from_sites(..., crs_names=...) (tie-break).

It prints the funnel, the changes by reason, the tie-break moves, six safety
checks (PASS/FAIL, exit code 1 on any FAIL) and examples, and writes
<out>/changes.csv and <out>/summary.json.

Read-only. The connection is opened with default_transaction_read_only=on and
SQLAlchemy's postgresql_readonly, and the script only runs SELECTs. It never
calls the API and never touches Fuseki.

Usage: put this file in a ta2-minmod-kg checkout of fix/p3-null-island and run
it from there, in that checkout's Python environment (the code in the current
directory is used; CFG_FILE is optional):

    python verify_p3.py --db "$KGREL_URL" --out p3_check/

A plain postgresql:// URL is run with the psycopg driver, as kgrel uses.

Expected on the 28 Jul data (ta2-minmod-data 3a086a5): 197 merged sites change,
29 from Null Island (25 to no point, 4 to another member's point) and 168 from
the tie-break (median 4 m, max 2.8 km); every check PASS; exit code 0. About
1-2 minutes on that data (198,129 merged sites, 458,809 member records).
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import csv
import json
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.getcwd())  # the checked-out code, not an installed copy
if "CFG_FILE" not in os.environ and not Path("config.yml").exists():
    # minmodkg needs a config for its namespaces; the database is --db
    os.environ["CFG_FILE"] = str(Path("tests/resources/config.yml").resolve())

from sqlalchemy import create_engine, func, select, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

try:
    import minmodkg.models.kgrel.custom_types.location as location_module
    import minmodkg.models.kgrel.dedup_mineral_site as dedup_module
    from minmodkg.misc.coord_precision import SourceCoordinate
    from minmodkg.models.kgrel.custom_types import LocationView
    from minmodkg.models.kgrel.custom_types.site_and_score import SiteScore
    from minmodkg.models.kgrel.dedup_mineral_site import DedupMineralSite
    from minmodkg.models.kgrel.mineral_site import MineralSite, MineralSiteAndInventory
    from minmodkg.services.kgrel_entity import EntityService

    assert hasattr(location_module, "drop_null_island")
    assert hasattr(dedup_module, "prefer_refined_coordinate")
except (ImportError, AssertionError) as e:
    sys.exit(f"Run this from a ta2-minmod-kg checkout of fix/p3-null-island ({e!r}).")

T0 = time.time()


def log(msg: str):
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


@contextlib.contextmanager
def p3_steps(on: bool):
    """With on=False, the Null Island rule and the tie-break are bypassed: the
    election is the one main ran before this branch."""
    if on:
        yield
        return
    saved = location_module.drop_null_island, dedup_module.prefer_refined_coordinate
    location_module.drop_null_island = lambda geometry: geometry
    dedup_module.prefer_refined_coordinate = lambda picked, *args, **kwargs: picked
    try:
        yield
    finally:
        location_module.drop_null_island, dedup_module.prefer_refined_coordinate = saved


def elect(members: list[MineralSite], crs_names, on: bool):
    """Recompute each member's location view, then elect: (dms, views by site_id)."""
    with p3_steps(on):
        views = {}
        for ms in members:
            ms.location_view = (
                LocationView.from_location(ms.location, crs_names)
                if ms.location is not None
                else LocationView()
            )
            views[ms.site_id] = ms.location_view
        dms = DedupMineralSite.from_sites(
            [MineralSiteAndInventory(ms, []) for ms in members], crs_names=crs_names
        ).dms
    return dms, views


def has_coord(view) -> bool:
    return view.lat is not None and view.lon is not None


def haversine_km(a, b) -> float:
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    h = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b.lon - a.lon) / 2) ** 2
    )
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(h)))


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, math.ceil(q * len(xs)) - 1)] if xs else None


def short(source_id: str) -> str:
    return source_id.split("://", 1)[-1]


def git_describe() -> str:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%h %s"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return f"{branch} @ {out}"
    except Exception:
        return "(not a git checkout)"


def multi_record_sites():
    return (
        select(MineralSite.dedup_site_id)
        .group_by(MineralSite.dedup_site_id)
        .having(func.count() >= 2)
    )


def load(session: Session) -> dict[str, list[MineralSite]]:
    """Members of every merged site with >= 2 records, with only the columns the
    election reads; inventories, references and geology are left out, so those
    fields come out empty, the same way in the control and in `after`."""
    stmt = select(
        MineralSite.site_id,
        MineralSite.dedup_site_id,
        MineralSite.source_id,
        MineralSite.source_score,
        MineralSite.record_id,
        MineralSite.name,
        MineralSite.type,
        MineralSite.rank,
        MineralSite.location,
        MineralSite.location_view,
        MineralSite.mineral_form,
        MineralSite.discovered_year,
        MineralSite.is_deleted,
        MineralSite.created_by,
        MineralSite.modified_at,
    ).where(MineralSite.dedup_site_id.in_(multi_record_sites()))
    groups = collections.defaultdict(list)
    for i, row in enumerate(session.execute(stmt.execution_options(yield_per=20000))):
        (site_id, dedup_id, source_id, source_score, record_id, name, type_, rank,
         location, location_view, mineral_form, discovered_year, is_deleted,
         created_by, modified_at) = row  # fmt: skip
        groups[dedup_id].append(
            MineralSite(
                site_id=site_id, dedup_site_id=dedup_id, source_id=source_id,
                source_score=source_score, record_id=record_id, name=name, aliases=[],
                rank=rank, type=type_, location=location, location_view=location_view,
                deposit_type_candidates=[], inventories=[], reference=[],
                mineral_form=mineral_form or [], geology_info=None,
                discovered_year=discovered_year, is_deleted=is_deleted, deleted_by=None,
                deleted_at=None, created_by=created_by, modified_at=modified_at,
            )  # fmt: skip
        )
        if (i + 1) % 100000 == 0:
            log(f"  loaded {i + 1:,} member records")
    return groups


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", required=True, help="kgrel Postgres URL (read-only use)")
    ap.add_argument(
        "--out",
        required=True,
        type=Path,
        help="directory for changes.csv and summary.json",
    )
    args = ap.parse_args()

    url = make_url(args.db)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    engine = create_engine(
        url,
        connect_args={"options": "-c default_transaction_read_only=on"},
        execution_options={"postgresql_readonly": True},
    )
    log(f"code: {git_describe()}")

    with Session(engine) as session:
        read_only = session.execute(text("SHOW transaction_read_only")).scalar()
        if read_only != "on":
            sys.exit("The connection is not read-only; stopping.")
        log(f"database: {url.database}; read-only transaction: {read_only}")
        entities = EntityService(engine)
        crs_names = entities.get_crs_name()
        country_name = {c.id: c.name for c in entities.get_countries()}
        log(f"CRS names: {len(crs_names)}; countries: {len(country_name)}")
        groups = load(session)
        n_records = sum(map(len, groups.values()))
        log(f"merged sites with >= 2 records: {len(groups):,} ({n_records:,} records)")
        before = dict(
            session.execute(
                select(DedupMineralSite.id, DedupMineralSite.coordinates).where(
                    DedupMineralSite.id.in_(multi_record_sites())
                )
            ).all()
        )
        log(f"stored merged coordinates read: {len(before):,}")

    funnel = collections.Counter()
    mismatch, changes, other_fields, zero_after = [], [], collections.Counter(), 0
    country_signs = collections.defaultdict(collections.Counter)
    for i, (e, members) in enumerate(groups.items()):
        score = {ms.site_id: SiteScore.get_score(ms) for ms in members}
        by_id = {ms.site_id: ms for ms in members}
        ctrl, ctrl_views = elect(members, crs_names, on=False)
        after, after_views = elect(members, crs_names, on=True)

        coord = sorted(
            (s for s, v in ctrl_views.items() if has_coord(v)),
            key=score.get,
            reverse=True,
        )
        funnel["1 merged sites with >= 2 records"] += 1
        if len(coord) >= 2:
            funnel["2 ... >= 2 with a coordinate"] += 1
            top = score[coord[0]]
            if (
                not top.is_from_user()
                and sum(score[s].score == top.score for s in coord) >= 2
            ):
                funnel["3 ... top trust score tied"] += 1
        for s in coord:
            v = ctrl_views[s]
            if v.lat == 0 and v.lon == 0:
                continue
            for c in v.country:
                country_signs[c]["lat+" if v.lat > 0 else "lat-"] += 1
                country_signs[c]["lon+" if v.lon > 0 else "lon-"] += 1

        if e not in before or ctrl.coordinates != before[e]:
            mismatch.append(
                (e, before.get(e, "(no stored merged site)"), ctrl.coordinates)
            )
        a, c = after.to_dict(), ctrl.to_dict()
        a.pop("coordinates", None), c.pop("coordinates", None)
        for k in set(a) | set(c):
            if a.get(k) != c.get(k):
                other_fields[k] += 1
        new = after.coordinates
        if new is not None and new.value.lat == 0 and new.value.lon == 0:
            zero_after += 1
        old = before.get(e)
        if old != new:
            changes.append(
                (
                    e,
                    members,
                    by_id,
                    score,
                    coord,
                    ctrl_views,
                    after_views,
                    after,
                    old,
                    new,
                )
            )
        if (i + 1) % 25000 == 0:
            log(f"  re-elected {i + 1:,} / {len(groups):,} merged sites")
    log(f"re-elected {len(groups):,} merged sites")

    print("\nControl (both steps bypassed) against the stored coordinates")
    if mismatch:
        print(f"  MISMATCH on {len(mismatch):,} of {len(groups):,} merged sites, e.g.:")
        for e, b, c in mismatch[:10]:
            print(f"    {e}\n      stored:  {b}\n      control: {c}")
        print(
            "\n  The database was not built by this code with the Problem 3 steps off,"
            "\n  or not from the same data (e.g. built before #108, or edited since)."
            "\n  The before/after comparison would mix other changes in. Stopping."
        )
        sys.exit(2)
    print(
        f"  equal on all {len(groups):,} merged sites: the baseline is this code's own"
    )

    rows = []
    for (
        e,
        members,
        by_id,
        score,
        coord,
        ctrl_views,
        after_views,
        after,
        old,
        new,
    ) in changes:
        name = after.name.value if after.name else None
        null_island = old is not None and old.value.lat == 0 and old.value.lon == 0
        reason = (
            "tie-break refinement" if not null_island
            else "null island -> no point" if new is None
            else "null island -> another member"
        )  # fmt: skip

        def side(ref, views):
            if ref is None:
                return None, None, None, None, None
            ms = by_id[ref.refid]
            crs = ms.location.crs_name(crs_names)
            src = SourceCoordinate(
                ms.site_id,
                ms.location.coordinates,
                crs,
                views[ms.site_id].lat,
                views[ms.site_id].lon,
            )
            return ms, crs, src, score[ms.site_id], short(ms.source_id)

        oms, ocrs, osrc, oscore, osrc_name = side(old, ctrl_views)
        nms, ncrs, nsrc, nscore, nsrc_name = side(new, after_views)
        row = {
            "dedup_site_id": e, "name": name, "reason": reason,
            "old_site_id": old and old.refid, "old_source": osrc_name,
            "old_score": oscore and oscore.score, "old_wkt": oms and oms.location.coordinates, "old_crs": ocrs,
            "new_site_id": new and new.refid, "new_source": nsrc_name,
            "new_score": nscore and nscore.score, "new_wkt": nms and nms.location.coordinates, "new_crs": ncrs,
            "km": round(haversine_km(old.value, new.value), 4) if old and new else None,
            "sign_flag": "",
            "_checks": {},
        }  # fmt: skip
        if reason == "tie-break refinement":
            row["_checks"] = {
                "top record is expert/curator": score[coord[0]].is_from_user(),
                "moves to a lower score": nscore.score < oscore.score,
                "outside the old point's rounding box": not osrc.contains(nsrc),
                "not strictly finer": not (nsrc.resolution_km() < osrc.resolution_km()),
            }
        elif new is not None:
            for c in after.country.value:
                st = country_signs.get(c, {})
                for axis, v in (("lat", new.value.lat), ("lon", new.value.lon)):
                    n = st.get(f"{axis}+", 0) + st.get(f"{axis}-", 0)
                    share = st.get(f"{axis}{'+' if v > 0 else '-'}", 0) / n if n else 1
                    if n >= 20 and share <= 0.05:
                        row["sign_flag"] = (
                            f"looks sign-flipped: {axis} {v:+g}, but {1 - share:.1%} of "
                            f"{n} records in {country_name.get(c, c)} have the other sign"
                        )
        rows.append(row)

    by_reason = collections.Counter(r["reason"] for r in rows)
    tb = [r for r in rows if r["reason"] == "tie-break refinement"]
    kms = [r["km"] for r in tb]
    checks = {
        name: sum(r["_checks"].get(name, False) for r in tb)
        for name in (
            "top record is expert/curator",
            "moves to a lower score",
            "outside the old point's rounding box",
            "not strictly finer",
        )
    }
    checks = {f"tie-break change: {k}": v for k, v in checks.items()}
    checks["a field other than the coordinate changed (country, state, ...)"] = sum(
        other_fields.values()
    )
    checks["a new coordinate at (0, 0)"] = zero_after

    print("\nFunnel")
    for k in sorted(funnel):
        print(f"  {k[2:]:40} {funnel[k]:>9,}")
    print(f"\nChanges: {len(rows):,} merged sites")
    for k in (
        "null island -> no point",
        "null island -> another member",
        "tie-break refinement",
    ):
        print(f"  {k:40} {by_reason[k]:>9,}")
    if kms:
        print(
            f"\nTie-break moves: median {statistics.median(kms) * 1000:.1f} m, p95 {pct(kms, 0.95) * 1000:.0f} m, "
            f"max {max(kms):.2f} km; {sum(k > 0.1 for k in kms)} over 100 m, {sum(k > 1 for k in kms)} over 1 km"
        )
        print("  top source pairs:")
        for pair, n in collections.Counter(
            f"{r['old_source']} -> {r['new_source']}" for r in tb
        ).most_common(10):
            print(f"    {n:>5}  {pair}")

    print("\nSafety checks (each must be 0)")
    failed = False
    for k, v in checks.items():
        print(f"  {'PASS' if v == 0 else 'FAIL'}  {v:>6}  {k}")
        failed |= v != 0
    if other_fields:
        print(f"        fields: {dict(other_fields)}")

    def show(r):
        km = (
            ""
            if r["km"] is None
            else (f"{r['km'] * 1000:.0f} m" if r["km"] < 1 else f"{r['km']:.1f} km")
        )
        print(f"  {km:>8}  {r['name']}  [{r['dedup_site_id']}]")
        print(
            f"            old: {r['old_wkt']} ({r['old_crs']}, {r['old_source']}, score {r['old_score']})"
        )
        print(
            f"            new: {r['new_wkt']} ({r['new_crs']}, {r['new_source']}, score {r['new_score']})"
        )
        if r["sign_flag"]:
            print(f"            ! {r['sign_flag']}")

    print("\nExamples: tie-break changes across the distance range")
    tb_sorted = sorted(tb, key=lambda r: r["km"])
    for j in (
        sorted({round(i * (len(tb_sorted) - 1) / 9) for i in range(10)})
        if tb_sorted
        else []
    ):
        show(tb_sorted[j])
    print("\nEvery Null Island fallback to another member")
    for r in rows:
        if r["reason"] == "null island -> another member":
            show(r)

    args.out.mkdir(parents=True, exist_ok=True)
    fields = [k for k in rows[0] if k != "_checks"] if rows else ["dedup_site_id"]
    with open(args.out / "changes.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    summary = {
        "code": git_describe(),
        "database": url.database,
        "merged_sites_with_2plus_records": len(groups),
        "member_records": n_records,
        "control_equals_stored": True,
        "funnel": {k[2:]: v for k, v in sorted(funnel.items())},
        "changes": len(rows),
        "changes_by_reason": dict(by_reason),
        "tie_break_moves_km": {
            "median": statistics.median(kms) if kms else None,
            "p95": pct(kms, 0.95),
            "max": max(kms, default=None),
            "over_100m": sum(k > 0.1 for k in kms),
            "over_1km": sum(k > 1 for k in kms),
        },
        "tie_break_source_pairs": dict(
            collections.Counter(
                f"{r['old_source']} -> {r['new_source']}" for r in tb
            ).most_common()
        ),
        "checks": {
            k: {"count": v, "result": "PASS" if v == 0 else "FAIL"}
            for k, v in checks.items()
        },
        "sign_flagged_fallbacks": [r["name"] for r in rows if r["sign_flag"]],
        "runtime_s": round(time.time() - T0, 1),
    }
    (args.out / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )
    print(f"\nWrote {args.out / 'changes.csv'} and {args.out / 'summary.json'}")
    print("RESULT: " + ("FAIL" if failed else "PASS") + f" ({time.time() - T0:.0f}s)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
