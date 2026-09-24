"""Sweep the conflicted agent's weight on the commission rate (paper section 7.6).

Reproduces results/results_psi_sensitivity.jsonl. Same reduced configuration as
the variants sweep (M=1500, 12 markup points, 7 spend points, 5 seeds), at full
agent adoption, with psi taking each of the four values reported in the paper.
Run from the repository root:

    python3 sim/run_psi.py

Writes results_psi_sensitivity.jsonl in the working directory.
"""
import sim2, json
from multiprocessing import Pool

PSI = (0.25, 0.5, 1.0, 2.0)

specs = [dict(alpha=1.0, gamma=g, seed=s, variant="conflict", psi=psi,
              M=1500, n_mark=12, n_spend=7)
         for psi in PSI for g in (0.0, 1.5) for s in range(5)]


def job(sp):
    r = sim2.run(**sp)
    r["psi"] = sp["psi"]
    return r


if __name__ == "__main__":
    with Pool(2) as p, open("results_psi_sensitivity.jsonl", "w") as fh:
        for r in p.imap_unordered(job, specs):
            fh.write(json.dumps(r) + "\n")
            fh.flush()
    print("done", len(specs))
