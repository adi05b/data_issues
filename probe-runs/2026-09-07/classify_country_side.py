"""1.1 — is the COUNTRY side of a conflict trustworthy?
Classifies every conflict row by whether the observed country string agrees
with the normalized country. Alias table is explicit and auditable: every
entry was read off the actual mismatch list, not guessed."""
import json, unicodedata, re, collections, os
R = os.path.dirname(os.path.abspath(__file__))

def fold(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

# observed-string -> normalized-label pairs judged to be the SAME country.
# Each was inspected individually; see the mismatch listing in P2_DIAGNOSIS.md.
ALIAS_OK = {
    ("congo kinshasa", "democratic republic of the congo"),
    ("democratic republic of congo", "democratic republic of the congo"),
    ("malawai", "malawi"),                       # source typo, matched correctly
    ("usa", "united states"),
    ("fiji", "fiji islands"),
    ("republic of portugal", "portugal"),
    ("republic of congo", "congo"),
    ("cote d ivoire", "cote d ivoire ivory coast"),
    ("korea north", "north korea"),
}
# genuinely wrong country normalizations
KNOWN_BAD = {
    ("slovak republic", "central african republic"),
    ("korea republic of", "democratic republic of the congo"),
}
# defensible but not certain
AMBIGUOUS = {
    ("korea", "north korea"),                    # "Korea" unqualified; could be South
    ("germany and czech republic", "czech republic"),  # multi-country string, partial match
}

rows = json.load(open(os.path.join(R, "1.1-alt-country-side-full.json")))["results"]["bindings"]
cls = collections.Counter(); detail = collections.defaultdict(list)
sub = collections.Counter()

for r in rows:
    n = int(r["sites"]["value"])
    co = r.get("country_obs", {}).get("value")
    cl = r.get("country_label", {}).get("value")
    so = r.get("state_obs", {}).get("value")
    sl = r.get("state_label", {}).get("value")
    if co is None:
        cls["undecidable"] += n; detail["undecidable"].append((so, sl, n)); continue
    fo, fl = fold(co), fold(cl or "")
    pair = (fo, fl)
    if fo == fl or pair in ALIAS_OK:
        cls["state-wrong"] += n
        # sub-split: is the matched state's NAME the observed name (homonym) or a different name?
        if so and sl and fold(so) == fold(sl): sub["homonym (right name, entity in wrong country)"] += n
        elif so and sl:                        sub["wrong name entirely (matcher picked a different word)"] += n
        else:                                  sub["state name missing"] += n
    elif pair in KNOWN_BAD:
        cls["country-wrong"] += n; detail["country-wrong"].append((co, cl, so, sl, n))
    elif pair in AMBIGUOUS:
        cls["country-ambiguous"] += n; detail["country-ambiguous"].append((co, cl, so, sl, n))
    else:
        cls["UNREVIEWED MISMATCH"] += n; detail["UNREVIEWED MISMATCH"].append((co, cl, so, sl, n))

tot = sum(cls.values())
print("=" * 78)
print("1.1  IS THE COUNTRY SIDE OF A CONFLICT TRUSTWORTHY?")
print("=" * 78)
print("conflict sites classified: %d  (across %d distinct rows)\n" % (tot, len(rows)))
print("%-24s %8s %9s" % ("class", "sites", "share"))
for k in ["state-wrong", "country-wrong", "country-ambiguous", "both-wrong", "undecidable", "UNREVIEWED MISMATCH"]:
    if k in cls or k in ("both-wrong",):
        print("%-24s %8d %8.2f%%" % (k, cls[k], 100 * cls[k] / tot))
print()
print("STATE-WRONG breakdown (the failure mode within the 'state is at fault' group):")
for k, v in sub.most_common():
    print("   %-58s %6d  %5.1f%%" % (k, v, 100 * v / cls["state-wrong"]))
for k in ["country-wrong", "country-ambiguous", "UNREVIEWED MISMATCH"]:
    if detail[k]:
        print("\n%s — every case listed in full:" % k.upper())
        for d in detail[k]:
            print("   observed '%s' -> normalized '%s' | state '%s' -> '%s' | %d sites" % d)
print("\nundecidable (no observed country string): %d sites across %d rows"
      % (cls["undecidable"], len(detail["undecidable"])))
