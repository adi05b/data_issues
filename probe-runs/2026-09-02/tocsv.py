import json,csv,glob,os,sys
# Derives <id>.csv from <id>.json as a SEPARATE file; never rewrites the raw json.
for p in sorted(glob.glob("*.json")):
    b=os.path.basename(p)
    if b.startswith("_") or b.endswith(".meta.json") or b.endswith(".profile.json"): continue
    try: j=json.load(open(p))
    except Exception: continue
    if "results" not in j: continue
    idd=b[:-5]; v=j["head"]["vars"]; rows=j["results"]["bindings"]
    # _site key: prefer a var named site, else first uri-valued var
    cols=["_site"]+[c for var in v for c in (var,var+"_bound")]
    with open(idd+".csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(cols)
        for r in rows:
            site=r.get("site",{}).get("value","")
            if not site:
                for var in v:
                    if r.get(var,{}).get("type")=="uri": site=r[var]["value"]; break
            out=[site]
            for var in v:
                out += [r[var]["value"] if var in r else "", 1 if var in r else 0]
            w.writerow(out)
    print("%-28s %4d rows  %2d vars" % (idd+".csv", len(rows), len(v)))
