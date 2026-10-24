"""Fill a throwaway local Postgres from an offline merge run, the way the kgrel
loader would, so acceptance/problem5_commodity_corrections.sql can be checked
on the full data. Adapted from p3/p3_verify_load.py. Never points at a shared
database.

  - schema from MinMod's own SQLAlchemy models (all kgrel tables);
  - dedup_mineral_site + dedup_mineral_inventory_view: every merged site,
    built with DedupMineralSite.from_dedup_sites over its partials and its
    members' inventory views, as prep_kgrel_input does. On the Problem 3
    branch the election also takes the run's CRS names and reads each member's
    location, so those are passed too;
  - mineral_site: every record, all columns; mineral_inventory_view: its views.

    CFG_FILE=<kg>/tests/resources/config.yml PYTHONPATH=<kg> \\
      .venv-p2/bin/python p5_load_kgrel.py <run dir> \\
      'postgresql+psycopg://postgres@<loopback host>:<port>/<db>'
"""

import collections
import inspect
import ipaddress
import socket
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import serde.json
from sqlalchemy import create_engine, insert, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from minmodkg.models.kgrel.base import Base
from minmodkg.models.kgrel.dedup_mineral_site import DedupMineralSite
from minmodkg.models.kgrel.mineral_site import MineralSite
from minmodkg.models.kgrel.views.mineral_inventory_view import (
    DedupMineralInventoryView,
    MineralInventoryView,
)
from minmodkg.services.kgrel_entity import FileEntityService

run, url = Path(sys.argv[1]), sys.argv[2]
assert ipaddress.ip_address(
    socket.gethostbyname(make_url(url).host or "")
).is_loopback, "local throwaway databases only"
files = sorted((run / "data/mineral-sites/merged").glob("*/*"))
# every row names every column: executemany takes its keys from the first row
VIEW_COLS = ["commodity", "contained_metal", "tonnage", "grade", "date"]
DINV_COLS = VIEW_COLS + ["site_id", "dedup_site_id"]
elect = {"is_site_ranked": True}
if "crs_names" in inspect.signature(DedupMineralSite.from_dedup_sites).parameters:
    elect["crs_names"] = FileEntityService(run / "data/entities").get_crs_name()
t0 = time.time()
engine = create_engine(url)
Base.metadata.create_all(engine)

# pass 1: merged-site partials and every record's inventory views
partials = collections.defaultdict(list)
views, members = {}, {}
for p in files:
    d = serde.json.deser(p)
    for x in d["DedupMineralSite"]:
        partials[x["id"]].append(x)
    for m in d["MineralSiteAndInventory"]:
        views[m["ms"]["site_id"]] = m.get("invs", [])
        ms = MineralSite.from_dict(m["ms"])
        members[ms.site_id] = SimpleNamespace(
            site_id=ms.site_id, location=ms.location, location_view=ms.location_view
        )
print(f"read {len(files)} files ({time.time() - t0:.0f}s)", flush=True)

n_dms = n_dinv = 0
with Session(engine) as s:
    batch, inv_rows = [], []
    for e, lst in partials.items():
        dms_lst = [DedupMineralSite.from_dict(x) for x in lst]
        sites = [
            SimpleNamespace(
                ms=members[r.site_id],
                invs=[MineralInventoryView.from_dict(v) for v in views[r.site_id]],
            )
            for dms in dms_lst
            for r in dms.ranked_sites
        ]
        merged = DedupMineralSite.from_dedup_sites(dms_lst, sites, **elect)
        batch.append(merged.dms)
        inv_rows.extend(
            {c: getattr(inv, c) for c in DINV_COLS} for inv in merged.invs
        )
        if len(batch) == 20000:
            s.bulk_save_objects(batch)
            s.execute(insert(DedupMineralInventoryView.__table__), inv_rows)
            n_dms += len(batch)
            n_dinv += len(inv_rows)
            batch, inv_rows = [], []
    s.bulk_save_objects(batch)
    if inv_rows:
        s.execute(insert(DedupMineralInventoryView.__table__), inv_rows)
    n_dms += len(batch)
    n_dinv += len(inv_rows)
    s.commit()
print(f"dedup_mineral_site: {n_dms}, dedup_mineral_inventory_view: {n_dinv} ({time.time() - t0:.0f}s)", flush=True)

# pass 2: records, with explicit ids so their views can point at them
cols = [c.name for c in MineralSite.__table__.columns if c.name != "id"]
n = n_inv = 0
with engine.begin() as conn:
    for p in files:
        rows, inv_rows = [], []
        for m in serde.json.deser(p)["MineralSiteAndInventory"]:
            ms = MineralSite.from_dict(m["ms"])
            n += 1
            rows.append({"id": n, **{c: getattr(ms, c) for c in cols}})
            for v in m.get("invs", []):
                inv_rows.append({**{c: v.get(c) for c in VIEW_COLS}, "site_id": n})
        conn.execute(insert(MineralSite.__table__), rows)
        if inv_rows:
            conn.execute(insert(MineralInventoryView.__table__), inv_rows)
        n_inv += len(inv_rows)
    conn.execute(text("SELECT setval(pg_get_serial_sequence('mineral_site', 'id'), :n)"), {"n": n})
print(f"mineral_site: {n}, mineral_inventory_view: {n_inv} ({time.time() - t0:.0f}s)", flush=True)
