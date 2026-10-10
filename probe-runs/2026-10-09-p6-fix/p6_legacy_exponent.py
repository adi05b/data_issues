#!/usr/bin/env python3
"""Open item from P6_DIAGNOSIS 7.3: does a legacy "5e-05"^^xsd:decimal already in
the store (6 such literals in prod, from ETL) survive the fixed handle_site_update
as an orphan? Same offline Jena 5.2.0 TDB2 CLI setup as p6_repro.py; no network.

Usage: CFG_FILE=<blocked config> p6_legacy_exponent.py <jena_home>
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

JENA = Path(sys.argv[1])
DB = Path(tempfile.mkdtemp(prefix="p6-legacy-tdb2-"))


def _no_network(*a, **k):
    raise RuntimeError("network disabled")


httpx.post = _no_network

from minmodkg.models.kg.base import MINMOD_KG  # noqa: E402
from minmodkg.models.kgrel.mineral_site import MineralSiteAndInventory  # noqa: E402
from minmodkg.services.sync.kgsync_listener import KGSyncListener  # noqa: E402


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
    f = DB.parent / (DB.name + ".rq")
    f.write_text(MINMOD_KG.prefix_part + q)
    return _Resp(jena("tdb2.tdbquery", "--results=" + ("ttl" if "CONSTRUCT" in q.upper() else "json"), f"--query={f}"))


def _update(q):
    f = DB.parent / (DB.name + ".ru")
    f.write_text(MINMOD_KG.prefix_part + q)
    jena("tdb2.tdbupdate", f"--update={f}")


MINMOD_KG._sparql_query = _query
MINMOD_KG._sparql_update = _update


class _Route:
    def site_paper(self, s):
        return None


L = KGSyncListener()
L.routing = _Route()

ORPHANS = """SELECT ?n ?p ?o WHERE { ?n ?p ?o FILTER NOT EXISTS { ?x ?q ?n } FILTER NOT EXISTS { ?n a ?t } }"""
VALUES = """SELECT ?m (STR(?v) AS ?lex) (DATATYPE(?v) AS ?dt) WHERE { ?m mo:value ?v }"""
out = {}

# 1. Is "5e-05"^^xsd:decimal the same RDF term as "0.00005"^^xsd:decimal in Jena?
_update('INSERT DATA { <urn:t> <urn:p> "5e-05"^^xsd:decimal }')
_update('DELETE DATA { <urn:t> <urn:p> "0.00005"^^xsd:decimal }')
out["1_left_after_deleting_0.00005"] = MINMOD_KG.query("SELECT (STR(?o) AS ?lex) WHERE { <urn:t> <urn:p> ?o }")
_update("CLEAR DEFAULT")

# 2. Legacy store: a site whose grade was written by the old writer as "5e-05".
SITE_ID = "site__mrdata-usgs-gov-mrds__10014570__curator1"
site = {"ms": {
    "site_id": SITE_ID, "dedup_site_id": "dedup_" + SITE_ID,
    "source_id": "https://mrdata.usgs.gov/mrds", "record_id": "10014570", "name": "Eagle Mine",
    "inventories": [{
        "commodity": {"source": "curator", "confidence": 1.0, "observed_name": "Nickel",
                      "normalized_uri": "https://minmod.isi.edu/resource/Q578"},
        "reference": {"document": {"uri": "https://mrdata.usgs.gov/mrds"}},
        "grade": {"value": 5e-05}}],
    "created_by": "https://minmod.isi.edu/users/u/curator1", "modified_at": 1}}
L.handle_site_add(None, MineralSiteAndInventory.from_dict(site), [])
_update('DELETE { ?m mo:value ?v } INSERT { ?m mo:value "5e-05"^^xsd:decimal } WHERE { ?m mo:value ?v }')
out["2a_values_before_update"] = MINMOD_KG.query(VALUES)
site["ms"]["name"] = "Eagle Mine (renamed)"
L.handle_site_update(None, MineralSiteAndInventory.from_dict(site))
out["2b_values_after_update"] = MINMOD_KG.query(VALUES)
out["2c_orphans_after_update"] = MINMOD_KG.query(ORPHANS)

shutil.rmtree(DB)
print(json.dumps(out, indent=1))
