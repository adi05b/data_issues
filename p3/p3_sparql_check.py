"""Check p3_amandeep.rq before it goes to the live endpoint: build a small rdflib
graph from run-main in the live graph's shape (hub owl:sameAs member, literal
:source_id/:created_by, xsd:decimal :score on the DataSource, :location_info/
:location) for a sample of groups, run the query, and compare with the same rows
computed in Python from main's own SiteScores. Also runs <rq>_row1.rq.

    CFG_FILE=<main>/tests/resources/config.yml PYTHONPATH=<main> \\
      .venv-p2/bin/python p3_sparql_check.py run-main p3_amandeep.rq
"""

import collections
import json
import sys
from decimal import Decimal
from pathlib import Path

import serde.json
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, XSD

from minmodkg.models.kgrel.custom_types import SiteScore

run, rq = Path(sys.argv[1]), Path(sys.argv[2])
MO, MR = Namespace("https://minmod.isi.edu/ontology/"), Namespace("https://minmod.isi.edu/resource/")
SONORA = "site__api-cdr-land-v1-docs-documents__0205e384bede4889373d9e9788b27e984c76aec51a0ba876f098cd08541ac7ab54__inferlink"

groups = serde.json.deser(run / "data/same-as/final/groups.json")
site, score = {}, {}
for f in sorted((run / "data/mineral-sites/merged").glob("*/*")):
    d = serde.json.deser(f)
    for x in d["DedupMineralSite"]:
        for r in x["ranked_sites"]:
            score[r["site_id"]] = SiteScore.from_dict(r["score"])
    for m in d["MineralSiteAndInventory"]:
        ms = m["ms"]
        site[ms["site_id"]] = (ms["source_id"], ms["created_by"], (ms.get("location") or {}).get("coordinates"))
groups = [[s for s in g if s in site] for g in groups]
expert = [g for g in groups if any(not site[s][1].startswith("https://minmod.isi.edu/users/s/") for s in g)]
sample = list({g[0]: g for g in [g for i, g in enumerate(groups) if i % 40 == 0 or SONORA in g] + expert}.values())

G = Graph()
for g in sample:
    for s in g[1:]:
        G.add((MR[g[0]], OWL.sameAs, MR[s]))
    for s in g:
        src, by, wkt = site[s]
        G.add((MR[s], MO.source_id, Literal(src)))
        G.add((MR[s], MO.created_by, Literal(by)))
        if wkt is not None:
            li = BNode()
            G.add((MR[s], MO.location_info, li))
            G.add((li, MO.location, Literal(wkt)))
for ds in json.loads((run / "data/entities/data_source.json").read_text())["DataSource"]:
    if ds.get("score") is not None:
        G.add((URIRef(ds["id"]), MO.score, Literal(Decimal(str(ds["score"])), datatype=XSD.decimal)))
got = {}
for q in (rq, rq.with_name(rq.stem + "_row1.rq")):
    got.update({str(k): int(float(v)) for k, v in next(iter(G.query(q.read_text()))).asdict().items()})

exp = collections.Counter()
for g in sample:
    exp["row1_two_plus_members"] += len(g) >= 2
    ms = sorted((s for s in g if site[s][2] is not None), key=lambda s: score[s], reverse=True)
    if len(ms) < 2:
        continue
    exp["row2_two_plus_with_coordinate"] += 1
    if score[ms[0]].suborder.is_expert:
        exp["row2a_top_is_expert"] += 1
        continue
    tied = [s for s in ms if score[s].score == score[ms[0]].score]
    if len(tied) >= 2:
        exp["row3_top_score_tied"] += 1
        exp["row3_same_source" if len({site[s][0] for s in tied}) == 1 else "row3_different_sources"] += 1
print(f"{len(sample)} groups ({len(expert)} with an expert/curator record), {len(G)} triples")
for k in got:
    print(f"  {k:32} sparql {got[k]:>6}  python {exp[k]:>6}  {'ok' if got[k] == exp[k] else 'MISMATCH'}")
assert all(got[k] == exp[k] for k in got)
