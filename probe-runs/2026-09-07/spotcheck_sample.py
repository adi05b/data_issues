"""1.3 — apply the proposed rule per site, then draw a reproducible sample for
hand adjudication. SEED = 20260907, random.Random, sorted site order."""
import json, os, re, random, unicodedata, collections
R = os.path.dirname(os.path.abspath(__file__))
SEED = 20260907
SUF = ("department","province","parish","state","region","prefecture","governorate",
       "district","oblast","county","territory","municipality")
def fold(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("-", " ").replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9 ]", " ", s); return re.sub(r"\s+", " ", s).strip()
def strip_suf(s):
    w = s.split()
    while w and w[-1] in SUF: w = w[:-1]
    return " ".join(w) if w else s
def key(s): return strip_suf(fold(s))

vocab = collections.defaultdict(lambda: collections.defaultdict(list))
for b in json.load(open(os.path.join(R,"..","2026-09-02-addendum","A2.4c-vocab-states.json")))["results"]["bindings"]:
    vocab[key(b["label"]["value"])][b.get("country",{}).get("value")].append(
        (b["ent"]["value"].rsplit("/",1)[1], b["label"]["value"]))

rows = json.load(open(os.path.join(R,"1.3-conflicts-sitelevel.json")))["results"]["bindings"]
recs = {}
for r in rows:
    g = lambda k: r.get(k,{}).get("value")
    recs[g("site")] = dict(site=g("site"), label=g("label"), state_obs=g("state_obs"),
        country_obs=g("country_obs"), country_id=g("country_id"), country_label=g("country_label"),
        state_ent=(g("state_ent") or "").rsplit("/",1)[-1], state_label=g("state_label"),
        wkt=g("wkt"), src=g("state_src"))

resolved, unresolved = [], []
for s, d in recs.items():
    so, cid = d["state_obs"], d["country_id"]
    hits = vocab.get(key(so), {}).get(cid, []) if so and cid else []
    if len(hits) == 1:
        d["rule_answer"] = hits[0]; resolved.append(d)
    else:
        d["rule_answer"] = None
        d["why"] = ("no observed state" if not so else
                    "no normalized country" if not cid else
                    "ambiguous: %d in-country hits" % len(hits) if len(hits) > 1 else
                    "key '%s' absent for country %s" % (key(so), cid))
        unresolved.append(d)

print("resolved by rule: %d   unresolved: %d   total: %d" % (len(resolved), len(unresolved), len(recs)))
rng = random.Random(SEED)
smp_r = rng.sample(sorted(resolved, key=lambda x: x["site"]), 30)
smp_u = rng.sample(sorted(unresolved, key=lambda x: x["site"]), 10)
json.dump({"seed": SEED, "n_resolved": len(resolved), "n_unresolved": len(unresolved),
           "sample_resolved": smp_r, "sample_unresolved": smp_u},
          open(os.path.join(R,"1.3-sample.json"),"w"), indent=2)

def coord(w):
    if not w: return "—"
    m = re.findall(r"[-+0-9.]+", w)
    return "(%.4f, %.4f)" % (float(m[1]), float(m[0])) if len(m) >= 2 else w  # lat, lon
print("\n" + "="*118); print("SAMPLE A — 30 CONFLICTS THE RULE RESOLVED  (seed %d)" % SEED); print("="*118)
print("%-3s %-24s %-17s %-24s %-22s %s" % ("#","observed state","obs country","rule answer","norm country","coord (lat,lon)"))
for i, d in enumerate(smp_r, 1):
    print("%-3d %-24s %-17s %-24s %-22s %s" % (i, (d["state_obs"] or "")[:24],
          (d["country_obs"] or "—")[:17], "%s %s" % (d["rule_answer"][0], d["rule_answer"][1][:16]),
          (d["country_label"] or "")[:22], coord(d["wkt"])))
print("\n" + "="*118); print("SAMPLE B — 10 THE RULE DID NOT RESOLVE"); print("="*118)
for i, d in enumerate(smp_u, 1):
    print("%-3d %-26s obs_country=%-16s wrongly->%-20s | %s" % (i, (d["state_obs"] or "«none»")[:26],
          (d["country_obs"] or "—")[:16], (d["state_label"] or "")[:20], d["why"]))
