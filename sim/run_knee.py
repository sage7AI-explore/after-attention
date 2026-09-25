"""Fine alpha grid through the knee (Appendix C).

Section 7.1 measures the margin fall on the 0.1 alpha grid, which cannot
distinguish a discontinuity from a steepening. This resweeps the window at
Delta-alpha = 0.02 on the headline configuration (M = 3000, 16 markup points,
8 spend points, tau = 0.15), 20 seeds, both persuadability regimes.

    python3 sim/run_knee.py

Writes results/results_knee_fine.jsonl. Resumes by cell, so an interrupted run
can be restarted and only the missing cells are computed.
"""
import sim2, json, os
from multiprocessing import Pool

ALPHAS = [0.15, 0.17, 0.19, 0.21, 0.23, 0.25, 0.27, 0.29,
          0.31, 0.33, 0.35, 0.37, 0.39, 0.41]
SPECS = [dict(alpha=a, gamma=g, seed=s)
         for s in range(20) for g in (0.0, 1.5) for a in ALPHAS]
OUT = "results/results_knee_fine.jsonl"


def job(sp):
    return sim2.run(**sp)


def main():
    os.makedirs("results", exist_ok=True)
    have = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            have.add((r["alpha"], r["gamma"], r["seed"]))
    todo = [sp for sp in SPECS
            if (sp["alpha"], sp["gamma"], sp["seed"]) not in have]
    print(f"{len(have)} present, {len(todo)} to go", flush=True)
    if not todo:
        return
    with Pool(int(os.environ.get("PROCS", 3))) as p, open(OUT, "a") as fh:
        for r in p.imap_unordered(job, todo):
            fh.write(json.dumps(r) + "\n")
            fh.flush()
    print("done", OUT, flush=True)


if __name__ == "__main__":
    main()
