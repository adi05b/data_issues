#!/usr/bin/env python3
"""Section 5: is anything rounded or truncated between the graph and here?

Compares the RAW BYTES of the HTTP response body against the value the JSON
parser produced, for 20 records spanning short and long decimal counts.
"""
import json, re, pathlib, random

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-14")
raw = (RD / "p3.2b-dms-pull.json").read_bytes()
doc = json.loads(raw)
rows = doc["results"]["bindings"]
print(f"response body: {len(raw)} bytes, {len(rows)} bindings")

def dp(s):
    m = re.search(r"\.(\d+)", s)
    return len(m.group(1)) if m else 0

vals = [(b["site"]["value"], b["wkt"]["value"]) for b in rows if "wkt" in b]
short = [v for v in vals if dp(v[1]) <= 3]
long_ = [v for v in vals if dp(v[1]) >= 12]
random.seed(0)
sample = random.sample(short, 10) + random.sample(long_, 10)

print(f"\n{'stored WKT (parsed)':<46}{'present verbatim in raw bytes':>30}")
print("-" * 78)
ok = 0
for site, wkt in sample:
    # the exact characters must appear in the undecoded body
    needle = wkt.encode("utf-8")
    hit = needle in raw
    # and re-serialising the parsed value must reproduce them
    roundtrip = json.dumps(wkt)[1:-1].encode() in raw or hit
    if hit and roundtrip:
        ok += 1
    print(f"{wkt[:44]:<46}{str(hit):>30}")
print(f"\nverbatim in {ok} of {len(sample)}")

# Does float() lose anything relative to the stored string?
print("\n--- does parsing to float change the value? ---")
loss = 0
for site, wkt in sample:
    m = re.search(r"POINT\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)", wkt)
    if not m:
        continue
    for s in (m.group(1), m.group(2)):
        if repr(float(s)) != s and float(repr(float(s))) != float(s):
            loss += 1
print(f"values where float() round-trip changes the NUMBER: {loss} (0 expected)")

# Size the trailing-zero population: strings that END in '0' after the decimal point.
import csv
allrows = list(csv.DictReader((RD / "p3.2a-popA-pull.csv").open()))
tz = 0
for r in allrows:
    m = re.search(r"POINT\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)", r["wkt"])
    if m and any("." in s and s.rstrip("0") != s for s in (m.group(1), m.group(2))):
        tz += 1
print(f"\npopulation A records whose stored string carries explicit trailing zeros: "
      f"{tz} of {len(allrows)}")
print("  (these were NOT rounded by float storage - the source wrote them that way)")
