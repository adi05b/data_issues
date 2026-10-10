#!/bin/bash
# Sends probe-runs/<date>/<id>.rq to the endpoint, saves raw bytes + meta.
# ponytail: no retry/backoff logic, re-run by hand if a probe times out.
ENDPOINT="https://minmod.isi.edu/sparql"
id="$1"; maxtime="${2:-300}"
d="$(cd "$(dirname "$0")" && pwd)"
start=$(python3 -c 'import time;print(int(time.time()*1000))')
sent_at=$(python3 -c 'import datetime;print(datetime.datetime.now(datetime.timezone.utc).isoformat())')
code=$(curl -sS -X POST "$ENDPOINT" \
  -H "Content-Type: application/sparql-query" \
  -H "Accept: application/sparql-results+json" \
  --data-binary @"$d/$id.rq" \
  --max-time "$maxtime" \
  -D "$d/$id.headers" \
  -o "$d/$id.json" \
  -w "%{http_code}" 2>"$d/$id.curlerr")
rc=$?
end=$(python3 -c 'import time;print(int(time.time()*1000))')
python3 - "$d" "$id" "$sent_at" "$code" "$((end-start))" "$rc" <<'PY'
import json,os,sys,re
d,id_,sent_at,code,elapsed,rc = sys.argv[1:7]
p=os.path.join(d,id_+".json")
raw=open(p,'rb').read() if os.path.exists(p) else b""
meta={"id":id_,"sent_at":sent_at,"http_status":int(code or 0),"elapsed_ms":int(elapsed),
      "bytes":len(raw),"curl_exit":int(rc),"row_count":None,"truncated_by_limit":None,"error":None}
err=open(os.path.join(d,id_+".curlerr")).read().strip()
if int(rc)!=0 or code!="200":
    meta["error"]=(err or raw.decode('utf8','replace')[:2000])
else:
    try:
        j=json.loads(raw)
        if "boolean" in j: meta["row_count"]="ASK="+str(j["boolean"])
        else:
            n=len(j["results"]["bindings"]); meta["row_count"]=n
            m=re.search(r'LIMIT\s+(\d+)',open(os.path.join(d,id_+".rq")).read(),re.I)
            meta["truncated_by_limit"]= bool(m and n==int(m.group(1)))
    except Exception as e: meta["error"]="unparseable JSON: %s"%e
json.dump(meta,open(os.path.join(d,id_+".meta.json"),"w"),indent=2)
print(json.dumps(meta))
PY
