"""Sonora Lithium Project in ta2-minmod-data history: did any field the merge
ranks or elects on change between commits? Read-only; needs a clone of
https://github.com/DARPA-CRITICALMAAS/ta2-minmod-data (a --filter=blob:none clone
is enough, git fetches the few blobs it shows).

    python3 p3_sonora_history.py <data repo clone> [commit ...]
"""

import csv
import io
import json
import subprocess
import sys

RIDS = ["0205e384bede", "0232b37b8235", "02497a3039a4", "026332f71cf7", "02c2ae8fc934", "02c7aaeba47f", "02ec633583ef"]
BUCKET = {"0205e384bede": "b063", "0232b37b8235": "b029", "02497a3039a4": "b061", "026332f71cf7": "b022",
          "02c2ae8fc934": "b014", "02c7aaeba47f": "b025", "02ec633583ef": "b034"}
FIELDS = ("source_id", "record_id", "created_by", "modified_at", "location_info")


def show(repo, commit, path):
    return subprocess.run(["git", "-C", repo, "show", f"{commit}:{path}"], capture_output=True, text=True, check=True).stdout


def snapshot(repo, commit):
    out = {}
    for rid, b in BUCKET.items():
        for team in ("inferlink", "sri"):
            for r in json.loads(show(repo, commit, f"data/mineral-sites/{team}/mining_report/{b}.json")):
                if r["record_id"].startswith(rid):
                    out[f"{rid} {team}"] = {k: r.get(k) for k in FIELDS}
    links = sum(any(rid in line for rid in RIDS) for line in show(repo, commit, "data/same-as/umn/part-0030.csv").splitlines())
    score = next(r for r in csv.DictReader(io.StringIO(show(repo, commit, "data/entities/data_source.csv")))
                 if r["uri"] == "https://api.cdr.land/v1/docs/documents")
    return out, links, score


def main(repo, commits):
    snaps = {c: snapshot(repo, c) for c in commits}
    base = snaps[commits[0]]
    for c in commits:
        recs, links, score = snaps[c]
        print(f"{c}: {len(recs)} records, {links} same-as lines naming them, mining-report score {score['score']}")
        for k in sorted(recs):
            diff = [f for f in FIELDS if recs[k][f] != base[0].get(k, {}).get(f)]
            if diff:
                print(f"   {k}: changed vs {commits[0]}: {diff}")
    print()
    for k, r in sorted(snaps[commits[-1]][0].items(), key=lambda kv: kv[1]["record_id"], reverse=True):
        loc = (r["location_info"] or {}).get("location")
        print(f"{k:24} {r['created_by'].rsplit('/', 1)[1]:9} {r['modified_at']:32} {loc}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or ["4305af5", "8c052d4", "3a086a5"])
