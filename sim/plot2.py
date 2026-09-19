"""Figure 1 for After Attention — regenerated from the v0.2 harness output."""
import json, sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

src = sys.argv[1] if len(sys.argv) > 1 else "results_headline.jsonl"
out = sys.argv[2] if len(sys.argv) > 2 else "fig_outcomes_v2.png"
R = [json.loads(l) for l in open(src)]

def agg(g, k):
    al = sorted({r["alpha"] for r in R})
    vals = [[r[k] for r in R if r["gamma"] == g and abs(r["alpha"] - a) < 1e-9] for a in al]
    return (np.array(al),
            np.array([np.mean(v) for v in vals]),
            np.array([np.std(v) for v in vals]))

panels = [("markup", "Gross margin (share of revenue)"),
          ("ad_spend", "Advertising spend (targets humans)"),
          ("agent_opt_spend", "Agent-directed spend (targets twins)"),
          ("persuasion_total", "Total persuasion spend"),
          ("surplus_per_unit", "Consumer net value per unit"),
          ("top3_value_share", "Sales share of top-3 true-value sellers"),
          ("hhi", "Concentration (HHI)"),
          ("price_cv", "Price dispersion (CV)")]

fig, ax = plt.subplots(2, 4, figsize=(16, 7.5))
for (k, title), a in zip(panels, ax.flat):
    for g, col, lab in [(0.0, "#2b6cb0", "Robust twins (γ = 0)"),
                        (1.5, "#c05621", "Manipulable twins (γ = 1.5)")]:
        x, m, s = agg(g, k)
        a.plot(x, m, color=col, lw=2, label=lab)
        a.fill_between(x, m - s, m + s, color=col, alpha=0.15)
    a.set_title(title, fontsize=10)
    a.set_xlabel("Twin-buyer share α", fontsize=9)
    a.grid(alpha=0.3)
    a.tick_params(labelsize=8)
ax[0, 0].legend(fontsize=8)
fig.suptitle("After Attention — simulated market outcomes vs. twin-buyer adoption "
             "(20 seeds, smoothed best response, mean ± sd)", fontsize=12)
fig.tight_layout()
fig.savefig(out, dpi=150)
print("wrote", out)

# summary table to stdout for the paper
for g in (0.0, 1.5):
    for k, _ in panels:
        x, m, _ = agg(g, k)
        pts = {a: round(float(v), 3) for a, v in zip(x, m) if a in (0, .2, .3, .5, 1.0)}
        print(f"g={g} {k:18s} {pts}")
