import re,sys
src,ids = sys.argv[1], sys.argv[2].split(',')
txt=open(src, encoding='utf-8').read()
blocks=re.findall(r'```sparql\n(.*?)```', txt, re.S)
assert len(blocks)==len(ids), "found %d blocks, expected %d"%(len(blocks),len(ids))
for i,b in zip(ids,blocks):
    open(i+'.rq','w',encoding='utf-8').write(b)
    print(i, len(b), "bytes")
