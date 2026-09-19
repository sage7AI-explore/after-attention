import json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = json.load(open("results.json"))
def agg(g, k):
    al = sorted({r["alpha"] for r in R})
    v = [[r[k] for r in R if r["gamma"]==g and r["alpha"]==a] for a in al]
    return np.array(al), np.array([np.mean(x) for x in v]), np.array([np.std(x) for x in v])
panels = [("markup","Gross margin (share of revenue)"),("ad_spend","Advertising spend (targets humans)"),
          ("agent_opt_spend","Agent-optimization spend (targets twins)"),("surplus_per_unit","Consumer net value per unit"),
          ("top3_value_share","Sales share of top-3 true-value sellers"),("hhi","Concentration (HHI)")]
fig, ax = plt.subplots(2,3, figsize=(13,7.5))
for (k,t),a in zip(panels, ax.flat):
    for g,col,lab in [(0.0,"#2b6cb0","Robust twins (γ=0)"),(1.5,"#c05621","Manipulable twins (γ=1.5)")]:
        x,m,s = agg(g,k); a.plot(x,m,color=col,lw=2,label=lab); a.fill_between(x,m-s,m+s,color=col,alpha=.15)
    a.set_title(t, fontsize=10); a.set_xlabel("Twin-buyer share α"); a.grid(alpha=.3)
ax[0,0].legend(fontsize=8)
fig.suptitle("After Attention — simulated market outcomes vs. twin-buyer adoption (5 seeds, mean ± sd)", fontsize=12)
fig.tight_layout(); fig.savefig("fig_outcomes.png", dpi=160)
# summary table
rows=[]
for g in [0.0,1.5]:
    for k,_ in panels+[("profit",""),("price_cv","")]:
        x,m,s = agg(g,k); rows.append((g,k,m[0],m[5],m[-1]))
for r in rows: print(f"gamma={r[0]:<4} {r[1]:<18} a=0: {r[2]:>9.3f}  a=.5: {r[3]:>9.3f}  a=1: {r[4]:>9.3f}")
