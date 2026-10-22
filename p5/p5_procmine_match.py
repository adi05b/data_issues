"""Problem 5 root cause: which commodity key each defect string hits in
ProcMine's matcher. Read-only; ProcMine is not changed.

    <venv with strsimpy 0.2.1>/bin/python -I p5_procmine_match.py \\
        <procmine checkout> <ta2-minmod-data>

Re-implements, line for line, procmine/converting/_entity.py:43-94
(identify_entity_id, ProcMine @ ce1ed70) and the dictionary
procmine/_utils.py:49-88 builds from _entities/commodity.csv, using the columns
in _entities/_selected_cols.pkl: name, aliases, geokb_name, mrds_code, all
lower-cased, aliases split on "|". strsimpy is the version ProcMine's
poetry.lock pins (0.2.1). ProcMine uses the `regex` module; the one pattern it
applies, r"[0-9]\\s", behaves the same in `re`.

Also prints, for the Oregon codes, every key in today's commodity.csv that the
code equals: the older "UMN Matching System v1" is not public, but it scored
1.0 on these and 0.001 on misses, as an exact lookup would.
"""

from __future__ import annotations

import csv
import re
import statistics
import sys
from pathlib import Path

from strsimpy import cosine, jaro_winkler, metric_lcs, normalized_levenshtein, overlap_coefficient, sorensen_dice

STRINGS = ["Construction", "Construc", "Metal", "General", "Dimension", "Refiner", "Smelter",
           "Pigment", "Industrial", "Volcanic Materials", "Water", "Flanthanum", "Halite", "Salt", "Emery",
           "SC", "SD", "CS", "S", "S&G", "Sand And Gravel"]
COLUMNS = ["name", "aliases", "geokb_name", "mrds_code"]


def build_dict(commodity_csv: Path) -> tuple[dict[str, str], dict[str, str]]:
    """key -> minmod_id, and key -> the column it came from"""
    rows = list(csv.DictReader(open(commodity_csv, encoding="utf-8-sig")))
    out, col_of = {}, {}
    for col in COLUMNS:
        tmp = {}
        for r in rows:
            v = r.get(col) or ""
            if v == "":
                continue
            for k in v.lower().split("|"):
                k = k.strip()
                tmp.setdefault(k, r["minmod_id"])  # rows_by_key keeps the first row
        for k, q in tmp.items():
            out[k] = q  # dict.update: a later column overwrites
            col_of[k] = col
    return out, col_of


def identify_entity_id(observed: str, entities: dict[str, str]):
    entity_uri, confidence = None, 0.0001
    string1 = re.sub(r"[0-9]\s", "", observed.lower())
    if not string1:
        return entity_uri, confidence, []
    if string1 in entities:
        return entities[string1], 0.9999, [(string1, 0.9999)]
    scored = []
    for entity, entity_id in entities.items():
        string2 = re.sub(r"[0-9]\s", "", entity.lower())
        if not string2:
            continue
        try:
            oc = overlap_coefficient.OverlapCoefficient(2).similarity(string1, string2)
        except Exception:
            oc = 0
        sims = [
            1 - normalized_levenshtein.NormalizedLevenshtein().distance(string1, string2),
            jaro_winkler.JaroWinkler().similarity(string1, string2),
            1 - metric_lcs.MetricLCS().distance(string1, string2),
            cosine.Cosine(1).similarity(string1, string2),
            oc,
            sorensen_dice.SorensenDice(2).similarity(string1, string2),
        ]
        try:
            tmp = statistics.mean(sims)
        except Exception:
            tmp = 0
        scored.append((entity, tmp))
        if tmp > confidence:
            confidence, entity_uri = tmp, entity_id
        if confidence > 0.9999:
            break
    scored.sort(key=lambda x: -x[1])
    return entity_uri, confidence, scored[:3]


def main(procmine: Path, repo: Path):
    ents, col_of = build_dict(procmine / "procmine/_entities/commodity.csv")
    names = {r["minmod_id"]: r["name"] for r in csv.DictReader(open(repo / "data/entities/commodity.csv", encoding="utf-8-sig"))}
    print(f"ProcMine's table: {len(ents)} keys")
    for s in STRINGS:
        q, conf, top = identify_entity_id(s, ents)
        how = f"exact key '{s.lower()}' ({col_of[s.lower()]})" if conf == 0.9999 else "fuzzy, best of all keys"
        print(f"{s!r:24} -> {q} {names.get(q, '')!s:28} {conf:.4f}  {how}; top 3: "
              + ", ".join(f"{k!r} {v:.4f}" for k, v in top))

    today, today_col = build_dict(repo / "data/entities/commodity.csv")
    print("\ntoday's commodity.csv, exact keys for the Oregon codes:")
    for code in ["SC", "SD", "CS", "S", "G", "S&G"]:
        k = code.lower()
        print(f"  {code:4} -> {today.get(k)} {names.get(today.get(k), '')} ({today_col.get(k, 'no key')})")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
