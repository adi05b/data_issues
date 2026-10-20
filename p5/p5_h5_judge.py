"""Problem 5, H5: verdicts for the graded (ProcMinev2) candidates below 0.62.

Method: one verdict per distinct (observed_name -> label) pair, judged against
the observed string only (mineralogy / commodity meaning), no other field of the
record. RIGHT = the label is what the string names; PARTIAL = the label is one
of several things the string names; WRONG = the label is a different
commodity. The 100-row sample (p5_scan.py, seed 20261020, uniform over
inventories) inherits the verdict of its pair.

    python3 p5_h5_judge.py out
"""

import collections
import csv
import sys
from pathlib import Path

VERDICT = {
    ("Construction", "Strontium"): ("WRONG", "MRDS subtype of 'Sand and Gravel, Construction'"),
    ("Construc", "Cobalt"): ("WRONG", "truncated 'Construction'"),
    ("Volcanic Materials", "Clay > Bloating Material"): ("WRONG", "pumice/cinder class; Q679 Volcanic Materials exists"),
    ("Water", "Slate"): ("WRONG", "Q680 Water exists"),
    ("Rock Asphalt", "Petroleum (Oil) > Rock Asphalt"): ("RIGHT", ""),
    ("Industrial/Frac Sand", "Sand"): ("RIGHT", ""),
    ("Industrial", "Indium"): ("WRONG", "subtype word"),
    ("Monazite", "Magnesite"): ("WRONG", "REE phosphate vs Mg carbonate"),
    ("Soda Ash", "Ash"): ("WRONG", "sodium carbonate"),
    ("Columbite-Tantalite", "Tantalum"): ("PARTIAL", "Nb and Ta ore; Nb missing"),
    ("Galena", "Gallium"): ("WRONG", "lead sulfide"),
    ("Chalcopyrite", "Clay > Chlorite"): ("WRONG", "copper sulfide"),
    ("Sillimanite", "Silica"): ("WRONG", "Al silicate (kyanite group)"),
    ("Gilsonite", "Wollastonite"): ("WRONG", "asphaltite"),
    ("Tripoli", "Lithium"): ("WRONG", "microcrystalline silica"),
    ("Halloysite", "Alunite"): ("WRONG", "clay mineral"),
    ("Apatite", "Graphite"): ("WRONG", "phosphate mineral; the earlier list called this correct"),
    ("Copper And Garnet", "Copper"): ("PARTIAL", "garnet missing"),
    ("Kaolin/ Feldspar", "Feldspar"): ("PARTIAL", "kaolin missing"),
    ("Muscovite Mica", "Mica"): ("RIGHT", ""),
    ("Tourmaline", "Staurolite"): ("WRONG", "different mineral"),
    ("Hematite", "Diatomite"): ("WRONG", "iron oxide"),
    ("Vesuvianite", "Kyanite"): ("WRONG", "different mineral"),
}


def fill(path: Path, weight: str | None):
    rows = list(csv.DictReader(open(path)))
    tally = collections.Counter()
    for r in rows:
        v, why = VERDICT[(r["observed_name"], r["label"])]
        r["verdict"] = v
        r["why"] = why
        tally[v] += int(r[weight]) if weight else 1
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return dict(tally), len(rows)


if __name__ == "__main__":
    out = Path(sys.argv[1])
    print("sample (rows):", fill(out / "h5_sample_below_062.csv", None))
    print("pairs (inventories):", fill(out / "h5_pairs_below_062.csv", "inventories"))
    pairs = list(csv.DictReader(open(out / "h5_pairs_below_062.csv")))
    print("pairs (distinct):", collections.Counter(r["verdict"] for r in pairs))
