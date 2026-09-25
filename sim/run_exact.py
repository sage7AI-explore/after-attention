"""Exact best response, for the comparisons in Appendix C.

The smoothed dynamic used throughout section 7 has temperature tau and inertia
iota. Exact best response is the tau -> 0 limit with iota = 0: we take tau = 1e-9,
at which the logit weight is numerically a point mass on the argmax, and every
seller revises in every sweep. Only under iota = 0 does a sweep with zero changes
mean a pure-strategy fixed point rather than a coincidence of skips. Three sweeps:

  coarse       the earlier 12-point configuration, 11 alphas x 2 gammas x 5 seeds,
               to count how many runs reach a pure-strategy fixed point and where.
  fine_ladder  the same alpha ladder on the headline 16-point markup and 8-point
               spend grids, to test whether the interior fixed points found on the
               coarse grid survive refinement.
  fine         the headline 16-point configuration at full adoption, 20 seeds per
               regime, to check that the top-three true-value share on the finer
               grid is not an artifact of the smoothing.

    python3 sim/run_exact.py coarse
    python3 sim/run_exact.py fine_ladder
    python3 sim/run_exact.py fine

Writes results/results_exact_<sweep>.jsonl, relative to the working directory. Appends and
resumes: re-running the same command picks up where it stopped.
"""
import sim2, json, os, sys
from multiprocessing import Pool

TAU = 1e-9
ALPHAS = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0]

SWEEPS = {
    "coarse": [dict(alpha=a, gamma=g, seed=s, tau=TAU, inertia=0.0, M=1500, n_mark=12, n_spend=7)
               for s in range(5) for g in (0.0, 1.5) for a in ALPHAS],
    "fine":   [dict(alpha=1.0, gamma=g, seed=s, tau=TAU, inertia=0.0, M=3000, n_mark=16, n_spend=8)
               for s in range(20) for g in (0.0, 1.5)],
    # The same alpha ladder as `coarse` but on the headline 16-point markup and
    # 8-point spend grids, to test whether the interior fixed points found on the
    # coarse grid survive refinement. Proposition 3's grid-fineness condition says
    # they should not.
    "fine_ladder": [dict(alpha=a, gamma=g, seed=s, tau=TAU, inertia=0.0,
                         M=1500, n_mark=16, n_spend=8)
                    for s in range(5) for g in (0.0, 1.5) for a in ALPHAS],
}


def job(sp):
    r = sim2.run(**sp)
    r["tau"] = TAU
    return r


if __name__ == "__main__":
    sweep = sys.argv[1]
    specs = SWEEPS[sweep]
    os.makedirs("results", exist_ok=True)
    out = f"results/results_exact_{sweep}.jsonl"
    done = sum(1 for _ in open(out)) if os.path.exists(out) else 0
    specs = specs[done:]
    print(f"{sweep}: {done} already done, {len(specs)} to go", flush=True)
    with Pool(int(os.environ.get("PROCS", 3))) as p, open(out, "a") as fh:
        for i, r in enumerate(p.imap(job, specs), 1):
            fh.write(json.dumps(r) + "\n"); fh.flush()
            print(f"  {i}/{len(specs)}", flush=True)
    print("done", out, flush=True)
