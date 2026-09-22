"""Null check for estimate.py: random choices on the real base design. A correct test
should flag H2 (one-sided, 5%) about 5% of the time. Result 22 Sep 2026, 138 runs:
6.5% (sd of z 1.11) -- slightly liberal, as expected for clustered SEs with 40 clusters.
    python3 gamma/null_check.py 0 200
"""
import sys, random, json, numpy as np
sys.path.insert(0,".")
import catalog, estimate
sets=catalog.build(n_sets=40)
jobs=[(s,arm,f,rep) for s in sets for arm in "ABC" for f in range(5) for rep in range(10)]
base=[]
for s,arm,f,rep in jobs:
    rng=random.Random(catalog.seed_for(s["set_id"],arm,f,rep))
    _,pos=catalog.render(s,arm,rng)
    base.append(dict(set_id=s["set_id"],arm=arm,framing=f,rep=rep,target_position=pos[s["target_id"]],ids=[p["id"] for p in s["products"]]))
def run(seed):
    R=random.Random(seed); rows=[]
    for b in base:
        r=dict(b); r["choice"]=R.choice(b["ids"]); del r["ids"]; rows.append(r)
    bh,se,V,n=estimate.fit(rows,sets)
    return bh,se,V
names=None
seeds=range(int(sys.argv[1]),int(sys.argv[2]))
for sd in seeds:
    b,se,V=run(sd)
    d=b[1]-b[2]; sd_=np.sqrt(V[1,1]+V[2,2]-2*V[1,2])
    print(json.dumps({"seed":sd,"zB":b[1]/se[1],"zC":b[2]/se[2],"zH2":d/sd_}),flush=True)
