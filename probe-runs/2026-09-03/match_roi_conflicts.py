"""Part 2.4: how many unmatched state names would a suffix-and-diacritic-aware
matcher recover, constrained to the site's already-normalized country?"""
import json, os, re, unicodedata, collections
R = os.path.dirname(os.path.abspath(__file__))

SUFFIXES = ("department","province","parish","state","region","prefecture",
            "governorate","district","oblast","county","territory","municipality")

def fold(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("-", " ").replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def strip_suffix(s):
    w = s.split()
    while w and w[-1] in SUFFIXES: w = w[:-1]
    return " ".join(w) if w else s

def key(s): return strip_suffix(fold(s))

# vocabulary: key -> {country_id -> [(ent,label)]}
vocab = collections.defaultdict(lambda: collections.defaultdict(list))
allv  = collections.defaultdict(list)
n_vocab = 0
for b in json.load(open(os.path.join(R,"A2.4c-vocab-states.json")))["results"]["bindings"]:
    lbl = b["label"]["value"]; ent = b["ent"]["value"]
    cid = b.get("country",{}).get("value")
    k = key(lbl); n_vocab += 1
    vocab[k][cid].append((ent,lbl)); allv[k].append((ent,lbl,cid))

rows = json.load(open(os.path.join(R,"A2.5-conflict-observed-names.json")))["results"]["bindings"]

tot=rec_country=rec_ambig=rec_nocountry=unrec=0
examples=[]; still=collections.Counter()
for b in rows:
    obs = b["state_obs"]["value"]; n = int(b["sites"]["value"])
    cid = b.get("country_id",{}).get("value")
    tot += n
    k = key(obs)
    if k not in allv:
        unrec += n; still[obs] += n; continue
    if cid and cid in vocab[k]:
        hits = vocab[k][cid]
        if len(hits) == 1:
            rec_country += n
            if len(examples) < 14: examples.append((obs, cid, hits[0][1], hits[0][0], n))
        else:
            rec_ambig += n
    elif not cid:
        # no normalized country to constrain with
        if len({e for e,_,_ in allv[k]}) == 1:
            rec_nocountry += n
            if len(examples) < 14: examples.append((obs, "(no country)", allv[k][0][1], allv[k][0][0], n))
        else:
            rec_ambig += n
    else:
        unrec += n; still[obs] += n

print("="*80)
print(f"vocabulary labels loaded: {n_vocab}   distinct folded keys: {len(allv)}")
print(f"unmatched (observed_name, country) rows: {len(rows)}   sites: {tot}")
print("="*80)
print("RECOVERY by a suffix-stripping + diacritic-folding matcher:")
print(f"  unique hit, constrained to the site's normalized country : {rec_country:5d} sites")
print(f"  unique hit, site had no normalized country to constrain  : {rec_nocountry:5d} sites")
print(f"  key matches but ambiguous (needs a tiebreak)             : {rec_ambig:5d} sites")
print(f"  still unmatched (genuine vocabulary gap)                 : {unrec:5d} sites")
print(f"  ---")
print(f"  confidently recoverable  : {rec_country+rec_nocountry:5d} / {tot} = {100*(rec_country+rec_nocountry)/tot:.1f}%")
print(f"  recoverable with tiebreak: {rec_country+rec_nocountry+rec_ambig:5d} / {tot} = {100*(rec_country+rec_nocountry+rec_ambig)/tot:.1f}%")
print("="*80)
print("EXAMPLES of what it recovers:")
for obs,cid,lbl,ent,n in examples:
    print(f"  {obs:<28} + country {str(cid):<8} -> {lbl:<32} ({ent.rsplit('/',1)[1]})  {n} sites")
print("="*80)
print("LARGEST REMAINING GAPS (no vocabulary entry under any country):")
for name,n in still.most_common(15): print(f"  {name:<34} {n:5d} sites")
