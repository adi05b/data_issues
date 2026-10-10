import json,sys
j=json.load(open(sys.argv[1]))
if "boolean" in j: print("ASK =",j["boolean"]); sys.exit()
v=j["head"]["vars"]; b=j["results"]["bindings"]
print(" | ".join(v)); print("-"*70)
for r in b[:int(sys.argv[2]) if len(sys.argv)>2 else 60]:
    print(" | ".join((r[k]["value"] if k in r else "«UNBOUND»") for k in v))
print("rows:",len(b))
