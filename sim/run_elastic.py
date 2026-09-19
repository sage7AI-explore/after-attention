import sim2, json, time
from multiprocessing import Pool
specs=[dict(alpha=a, gamma=g, seed=s, variant="elastic", elastic_scale=0.15,
            M=1500, n_mark=12, n_spend=7)
       for s in range(5) for g in (0.0,1.5) for a in [0,.1,.2,.3,.4,.5,.6,.7,.8,.9,1.0]]
def job(sp):
    r=sim2.run(**sp); r["elastic_scale"]=0.15; return r
with Pool(2) as p, open("results_elastic.jsonl","w") as fh:
    for i,r in enumerate(p.imap_unordered(job, specs),1):
        fh.write(json.dumps(r)+"\n"); fh.flush()
print("done", len(specs))
