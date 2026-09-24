"""Figure 2: gamma x alpha phase diagram for After Attention."""
import json, sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

src = sys.argv[1] if len(sys.argv) > 1 else "results/results_phase.jsonl"
out = sys.argv[2] if len(sys.argv) > 2 else "figures/fig_phase.png"
R = [json.loads(l) for l in open(src)]
al = sorted({r["alpha"] for r in R})
gs = sorted({r["gamma"] for r in R})

def grid(k):
    Z = np.zeros((len(gs), len(al)))
    for i, g in enumerate(gs):
        for j, a in enumerate(al):
            v = [r[k] for r in R if r["gamma"] == g and abs(r["alpha"] - a) < 1e-9]
            Z[i, j] = np.mean(v) if v else np.nan
    return Z

panels = [("markup", "Gross margin (share of revenue)", "viridis"),
          ("persuasion_total", "Total persuasion spend", "magma"),
          ("hhi", "Concentration (HHI)", "inferno"),
          ("surplus_per_unit", "Consumer net value per unit", "cividis")]

fig, ax = plt.subplots(2, 2, figsize=(11, 8.2))
for (k, title, cmap), a in zip(panels, ax.flat):
    Z = grid(k)
    im = a.imshow(Z, origin="lower", aspect="auto", cmap=cmap,
                  extent=[min(al), max(al), min(gs), max(gs)])
    cs = a.contour(np.array(al), np.array(gs), Z, colors="white", linewidths=0.6, alpha=0.7)
    a.clabel(cs, inline=True, fontsize=8, fmt="%.0f" if k in ("hhi", "persuasion_total") else "%.2f")
    a.set_title(title, fontsize=11)
    a.set_xlabel("Twin-buyer share α", fontsize=10)
    a.set_ylabel("Twin persuadability γ", fontsize=10)
    fig.colorbar(im, ax=a, fraction=0.046)

# mark the pre-agent advertising benchmark on the persuasion panel
base = np.mean([r["persuasion_total"] for r in R if r["alpha"] == 0 and r["gamma"] == 0])
ax.flat[1].set_title(f"Total persuasion spend (α=γ=0 baseline ≈ {base:,.0f})", fontsize=10)

fig.suptitle("After Attention — outcomes across the persuadability × adoption plane "
             "(4 seeds per cell, smoothed best response)", fontsize=12.5)
fig.tight_layout()
fig.savefig(out, dpi=150)
print("wrote", out, "; baseline", round(base, 1))

# text summary for the paper
print("\ngamma ->", gs)
for k in ("markup", "persuasion_total", "hhi", "surplus_per_unit", "top3_value_share"):
    Z = grid(k)
    print(f"\n{k}")
    for i, g in enumerate(gs):
        print(f"  g={g:<5} " + " ".join(f"{Z[i,j]:8.2f}" for j in range(len(al))))
