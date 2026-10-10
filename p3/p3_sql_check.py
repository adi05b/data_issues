"""Load run-main into a throwaway local Postgres so p3_amandeep.sql can be checked
against the real kgrel DDL. Creates mineral_site and dedup_mineral_site from
MinMod's own SQLAlchemy models, relaxes NOT NULL on the columns not loaded, and
fills the columns the query reads. Never points at a shared database.

    CFG_FILE=<main>/tests/resources/config.yml PYTHONPATH=<main> \\
      .venv-p2/bin/python p3_sql_check.py run-main 'postgresql+psycopg://postgres@/kgrel?host=<socket dir>&port=55432'
"""

import collections
import sys
from pathlib import Path

import orjson
import serde.json
from sqlalchemy import create_engine, text

from minmodkg.models.kgrel.dedup_mineral_site import DedupMineralSite
from minmodkg.models.kgrel.mineral_site import MineralSite

run, url = Path(sys.argv[1]), sys.argv[2]
assert "localhost" in url or "host=/" in url, "local throwaway databases only"
engine = create_engine(url)
tables = [DedupMineralSite.__table__, MineralSite.__table__]
DedupMineralSite.metadata.create_all(engine, tables=tables)
with engine.begin() as conn:
    for t in tables:
        for c in t.columns:
            if not c.primary_key:
                conn.execute(text(f'ALTER TABLE {t.name} ALTER COLUMN "{c.name}" DROP NOT NULL'))

ranked, sites = collections.defaultdict(list), []
for f in sorted((run / "data/mineral-sites/merged").glob("*/*")):
    d = serde.json.deser(f)
    for x in d["DedupMineralSite"]:
        ranked[x["id"]].extend(x["ranked_sites"])  # the merged list is the union of the partials'
    for m in d["MineralSiteAndInventory"]:
        ms = m["ms"]
        sites.append((ms["site_id"], ms["dedup_site_id"], ms["source_id"], orjson.dumps(ms.get("location_view") or {})))

raw = engine.raw_connection()
cur = raw.cursor()
with cur.copy("COPY dedup_mineral_site (id, ranked_sites) FROM STDIN") as cp:
    for k, v in ranked.items():
        cp.write_row((k, orjson.dumps(v)))
with cur.copy("COPY mineral_site (site_id, dedup_site_id, source_id, location_view) FROM STDIN") as cp:
    for row in sites:
        cp.write_row(row)
raw.commit()
raw.close()
print(f"loaded {len(ranked)} dedup_mineral_site rows, {len(sites)} mineral_site rows")
