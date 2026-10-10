#!/usr/bin/env python3
"""P6 offline reproduction: run the REAL KGSyncListener handlers from
ta2-minmod-kg@83f9b7b, but route every SPARQL query/update to a throwaway
local Jena 5.2.0 TDB2 directory via the tdb2.tdbquery / tdb2.tdbupdate CLIs.

No server is started, no network write is possible: httpx.post is replaced
with a function that raises, and the config's endpoints point at 127.0.0.1:1.

Usage: CFG_FILE=<blocked config> p6_repro.py <jena_home> <out_dir>
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

JENA, OUT = Path(sys.argv[1]), Path(sys.argv[2])
DB = Path(tempfile.mkdtemp(prefix="p6-tdb2-"))
LOG = OUT / "p6-repro-sparql.log"
LOG.write_text("")


def _no_network(*a, **k):
    raise RuntimeError("network disabled in p6_repro")


httpx.post = _no_network  # belt and braces: nothing reaches a real store

from minmodkg.libraries.rdf import fuseki  # noqa: E402

fuseki.httpx.post = _no_network

from minmodkg.misc.utils import norm_literal  # noqa: E402
from minmodkg.models.kg.base import MINMOD_KG  # noqa: E402
from minmodkg.models.kgrel.mineral_site import MineralSiteAndInventory  # noqa: E402
from minmodkg.models.kgrel.sample import Sample  # noqa: E402
from minmodkg.services.sync.kgsync_listener import KGSyncListener  # noqa: E402
from rdflib import XSD, Literal, URIRef  # noqa: E402


def jena(tool, *args):
    r = subprocess.run([str(JENA / "bin" / tool), "--loc", str(DB), *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return r.stdout


class _Resp:
    def __init__(self, text):
        self.text = text

    def json(self):
        return json.loads(self.text)


def _query(q):
    f = DB.parent / "q.rq"
    f.write_text(MINMOD_KG.prefix_part + q)
    kind = "ttl" if "CONSTRUCT" in q.upper() else "json"
    return _Resp(jena("tdb2.tdbquery", f"--results={kind}", f"--query={f}"))


def _update(q, label=[None]):
    full = MINMOD_KG.prefix_part + q
    with LOG.open("a") as h:
        h.write(f"\n##### {STEP} #####\n{q}\n")
    f = DB.parent / "u.ru"
    f.write_text(full)
    jena("tdb2.tdbupdate", f"--update={f}")


MINMOD_KG._sparql_query = _query
MINMOD_KG._sparql_update = _update


class _Route:  # minmod lane, no GeoChem paper -> listener owns every event
    def site_paper(self, s):
        return None

    def sample_paper(self, s):
        return None


L = KGSyncListener()
L.routing = _Route()

CENSUS = """
SELECT ?p ?dt (COUNT(*) AS ?n) WHERE {
  ?s ?p ?o FILTER(isLiteral(?o))
  BIND(DATATYPE(?o) AS ?dt)
  FILTER(?dt IN (xsd:decimal, xsd:double, xsd:float, xsd:integer))
} GROUP BY ?p ?dt ORDER BY ?p ?dt"""

ORPHANS = """
SELECT ?n ?p ?o (DATATYPE(?o) AS ?dt) WHERE {
  ?n ?p ?o .
  FILTER(STRSTARTS(STR(?n), "https://minmod.isi.edu/resource/") || STRSTARTS(STR(?n), "https://geochemistry.isi.edu/resource/"))
  FILTER NOT EXISTS { ?x ?q ?n }
  FILTER NOT EXISTS { ?n a ?t }
} ORDER BY ?n ?p"""

DOUBLES = """
SELECT ?s ?p ?o WHERE { ?s ?p ?o FILTER(isLiteral(?o) && DATATYPE(?o) = xsd:double) } ORDER BY ?s ?p"""

ATTACHED_DUPES = """
SELECT ?s ?p (COUNT(?o) AS ?vals) (GROUP_CONCAT(CONCAT(STR(?o), "^^", STR(DATATYPE(?o))); separator=" | ") AS ?all)
WHERE { ?s ?p ?o . ?s a ?t . FILTER(isNumeric(?o)) } GROUP BY ?s ?p HAVING (COUNT(?o) > 1)"""

results = {}


def snap(step):
    rows = {}
    for name, q in [("census", CENSUS), ("orphans", ORPHANS), ("doubles", DOUBLES), ("attached_dupes", ATTACHED_DUPES)]:
        out = MINMOD_KG._sparql_query(q).json()["results"]["bindings"]
        rows[name] = [{k: v["value"] for k, v in b.items()} for b in out]
    results[step] = rows


# ---------------------------------------------------------------- inputs
CE = lambda name, conf, uri=None: {  # noqa: E731
    "source": "curator", "confidence": conf, "observed_name": name,
    **({"normalized_uri": uri} if uri else {})}
USER = "https://minmod.isi.edu/users/u/curator1"
SITE_ID = "site__mrdata-usgs-gov-mrds__10014570__curator1"
site_v1 = {"ms": {
    "site_id": SITE_ID, "dedup_site_id": "dedup_" + SITE_ID,
    "source_id": "https://mrdata.usgs.gov/mrds", "record_id": "10014570",
    "name": "Eagle Mine", "discovered_year": 1950,
    "location": {"country": [CE("United States", 0.9, "https://minmod.isi.edu/resource/Q1235")],
                 "crs": CE("EPSG:4326", 1.0, "https://minmod.isi.edu/resource/Q701"),
                 "coordinates": "POINT (-87.0999 46.9)"},
    "inventories": [{
        "commodity": CE("Nickel", 0.9999, "https://minmod.isi.edu/resource/Q578"),
        "reference": {"document": {"uri": "https://mrdata.usgs.gov/mrds"},
                      "page_info": [{"page": 3, "bounding_box": {"x_max": 10.5, "x_min": 1.25, "y_max": 20.75, "y_min": 2.5}}]},
        "grade": {"value": 1.25, "unit": CE("percent", 1.0, "https://minmod.isi.edu/resource/Q201")},
        "ore": {"value": 8.54, "unit": CE("tonnes", 1.0, "https://minmod.isi.edu/resource/Q202")},
    }],
    "created_by": USER, "modified_at": 1_700_000_000_000_000_000}}

site_v2 = json.loads(json.dumps(site_v1))
site_v2["ms"]["name"] = "Eagle Mine (renamed)"          # text-only edit
site_v3 = json.loads(json.dumps(site_v2))
site_v3["ms"]["inventories"][0]["grade"]["value"] = 1.3  # numeric edit

SAMPLE_ID = "smp__" + SITE_ID + "__S1"
sample_v1 = {
    "public_id": SAMPLE_ID, "mineral_site_id": SITE_ID, "sample_id": "S1",
    "sample_name": "kawazulite", "top_depth_m": 12.5, "bottom_depth_m": 13.0,
    "is_deleted": False, "modified_at": 1,
    "analyses": [{"analysis_id": "A1", "elements": [
        {"label": "Bi", "grade": 61.5, "grade_unit": CE("wt%", 0.95)},
        {"label": "Te", "grade": 29.33, "detection_limit": 0.04},
    ]}],
    "reference": [], "edit_history": []}
sample_v2 = json.loads(json.dumps(sample_v1))
sample_v2["sample_name"] = "kawazulite (edited)"         # text-only edit
sample_v3 = json.loads(json.dumps(sample_v2))
sample_v3["top_depth_m"] = 12.75                        # numeric edit on the KEYED Sample node

# ---------------------------------------------------------------- run
STEP = "S0-norm_literal-table"
table = []
for lit in [Literal("1.25", datatype=XSD.decimal), Literal("1.25", datatype=XSD.double),
            Literal("1.25", datatype=XSD.float), Literal("3", datatype=XSD.integer),
            Literal("true", datatype=XSD.boolean), Literal("2026-10-01", datatype=XSD.date),
            Literal("2026-10-01T00:00:00Z", datatype=XSD.dateTime), Literal("abc"),
            Literal("abc", datatype=XSD.string), Literal("abc", lang="en"),
            URIRef("https://minmod.isi.edu/resource/Q578")]:
    n = norm_literal(lit)
    table.append({"in": lit.n3(), "out": n.n3(), "out_type": type(n).__name__})
results[STEP] = table

for STEP, fn, arg in [
    ("S1-site-add", L.handle_site_add, None),
    ("S2-site-update-text-only", L.handle_site_update, site_v2),
    ("S3-site-update-grade-1.25-to-1.3", L.handle_site_update, site_v3),
    ("S4-sample-add", L.handle_sample_add, None),
    ("S5-sample-update-text-only", L.handle_sample_update, sample_v2),
    ("S6-sample-update-top_depth-12.5-to-12.75", L.handle_sample_update, sample_v3),
]:
    if STEP == "S1-site-add":
        fn(None, MineralSiteAndInventory.from_dict(site_v1), [])
    elif STEP == "S4-sample-add":
        fn(None, Sample.from_dict(sample_v1))
    elif "site" in STEP:
        fn(None, MineralSiteAndInventory.from_dict(arg))
    else:
        fn(None, Sample.from_dict(arg))
    snap(STEP)

# Detection check: the exact .rq files sent to production, run against this
# repro store (which is known to contain doubles and orphans). Non-zero here
# means a zero in production is "absent", not "the query cannot see it".
detect = {}
for rq in ["p6-pf1-double-any", "p6-o1-untyped-numeric", "p6-o2-issue-element-query"]:
    text = (OUT / f"{rq}.rq").read_text()
    out = _query(text).json()["results"]["bindings"]
    detect[rq] = [{k: v["value"] for k, v in b.items()} for b in out]
results["detection-check-prod-queries-on-repro-store"] = detect

(OUT / "p6-repro-results.json").write_text(json.dumps(results, indent=2))
shutil.rmtree(DB)
print(json.dumps({k: (v if k.startswith("S0") else {kk: len(vv) for kk, vv in v.items()}) for k, v in results.items()}, indent=1))
