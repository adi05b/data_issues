"""Test helper for verify_p3.py: fill a throwaway local Postgres from a merge run,
the way the kgrel loader would, so verify_p3.py can be checked end to end.

Run it with the code that "built" the database (main: the stored merged
coordinates are then main's picks):
  - schema from MinMod's own SQLAlchemy models (all kgrel tables);
  - crs and country from the run's entities;
  - mineral_site: every record, all columns, from the merged files;
  - dedup_mineral_site: every merged site, built with from_dedup_sites over its
    partials, as prep_kgrel_input does (inventories are not loaded).
Never points at a shared database.

    CFG_FILE=<main>/tests/resources/config.yml PYTHONPATH=<main>:. \\
      .venv-p2/bin/python p3_verify_load.py run-main "$LOCAL_TEST_DB"

where $LOCAL_TEST_DB is a throwaway Postgres on this machine (UTF8 database).
"""

import collections
import ipaddress
import socket
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import serde.json
from sqlalchemy import create_engine, insert
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from minmodkg.models.kgrel.base import Base
from minmodkg.models.kgrel.dedup_mineral_site import DedupMineralSite
from minmodkg.models.kgrel.mineral_site import MineralSite
from minmodkg.services.kgrel_entity import FileEntityService
from p3_null_island_measure import files

run, url = Path(sys.argv[1]), sys.argv[2]
host = make_url(url).host or ""
assert ipaddress.ip_address(
    socket.gethostbyname(host)
).is_loopback, "local throwaway databases only"
t0 = time.time()
engine = create_engine(url)
Base.metadata.create_all(engine)

with Session(engine) as s:
    entities = FileEntityService(run / "data/entities")
    s.add_all(entities.get_crs() + entities.get_countries())
    s.commit()

# merged sites first: mineral_site.dedup_site_id references them
partials = collections.defaultdict(list)
for p in files(run).values():
    for x in serde.json.deser(p)["DedupMineralSite"]:
        partials[x["id"]].append(x)
batch = []
with Session(engine) as s:
    for e, lst in partials.items():
        dms_lst = [DedupMineralSite.from_dict(x) for x in lst]
        # from_dedup_sites only needs the members' ids and inventories
        sites = [
            SimpleNamespace(ms=SimpleNamespace(site_id=r.site_id), invs=[])
            for d in dms_lst
            for r in d.ranked_sites
        ]
        batch.append(
            DedupMineralSite.from_dedup_sites(dms_lst, sites, is_site_ranked=True).dms
        )
        if len(batch) == 20000:
            s.bulk_save_objects(batch)
            batch = []
    s.bulk_save_objects(batch)
    s.commit()
print(f"dedup_mineral_site: {len(partials)} rows ({time.time() - t0:.0f}s)", flush=True)

cols = [c.name for c in MineralSite.__table__.columns if c.name != "id"]
n = 0
with engine.begin() as conn:
    for p in files(run).values():
        rows = []
        for m in serde.json.deser(p)["MineralSiteAndInventory"]:
            ms = MineralSite.from_dict(m["ms"])
            rows.append({c: getattr(ms, c) for c in cols})
        conn.execute(insert(MineralSite.__table__), rows)
        n += len(rows)
print(f"mineral_site: {n} rows ({time.time() - t0:.0f}s)", flush=True)
