"""
After Attention — twin-buyer market simulation, v0.2 harness.

Changes from v0.1 (sim.py):
  * Smoothed (quantal / logit) best response with inertia, replacing pure argmax best
    response. Pure BR cycles on a discrete grid; smoothing gives a well-defined
    stationary distribution to average over and makes the reported numbers
    independent of the cycling artifact.
  * Configurable action grids (finer grids supported).
  * Variants:
      - elastic  : price-sensitive outside option (category demand can contract)
      - hetero   : twin population is a mixture of robust (gamma=0) and manipulable twins
      - conflict : third buyer type, a platform-owned agent that weights a per-sale
                   commission offered by the seller (kickback), not a resource-cost spend
  * Reports stationarity diagnostics instead of a binary converged flag.

Buyer types
  humans  : limited consideration bought by advertising, noisy quality perception,
            persuadable valuation (beta * log(1+A))
  twins   : full consideration, true quality, sharp choice (mu_t), persuadable by
            agent-directed optimization spend with weight gamma
  agents* : (conflict variant) full consideration, true quality, sharp choice, and
            additionally weight psi * commission_rate offered by the seller. The
            commission is a transfer paid out of the seller's margin on sales to this
            type, not a fixed cost, which is what distinguishes a conflicted agent from
            a merely persuadable one.
"""
import numpy as np, json, argparse, itertools, os, sys, time


# ---------------------------------------------------------------- parameters
DEFAULTS = dict(
    N=12, M=3000, iters=40, window=10,
    theta_q=12.0, lam=1.0, beta_h=1.2, noise_h=1.0, mu_t=3.0,
    a0=-1.5, a1=0.9, V0=5.0,
    tau=0.15,        # smoothing temperature, relative to the spread of candidate profits
    inertia=0.35,    # probability a seller keeps its current action in a given revision
    n_mark=16, n_spend=8, max_spend=1500.0, max_mark=1.7,
    psi=1.0,         # conflicted agent's weight on commission rate
    rho_robust=0.5,  # hetero variant: share of twins that are robust
    elastic_scale=1.0,   # elastic variant: multiplies the outside option's price sensitivity
)


def grids(p):
    marks = np.unique(np.round(np.concatenate([
        np.linspace(0.01, 0.3, p["n_mark"] // 2),
        np.linspace(0.35, p["max_mark"], p["n_mark"] - p["n_mark"] // 2)]), 4))
    spend = np.unique(np.round(np.concatenate([[0.0],
        np.geomspace(5.0, p["max_spend"], p["n_spend"] - 1)]), 2))
    return marks, spend


def run(alpha, gamma=0.0, seed=0, variant="base", **over):
    p = dict(DEFAULTS); p.update(over)
    N, M = p["N"], p["M"]
    rng = np.random.default_rng(seed)
    q = np.sort(rng.uniform(0, 1, N))
    c = 5 + 10 * q
    theta_q, lam, mu_t = p["theta_q"], p["lam"], p["mu_t"]
    beta_h, noise_h, V0 = p["beta_h"], p["noise_h"], p["V0"]
    a0, a1 = p["a0"], p["a1"]

    # ---- population split
    Mh = int(round(M * (1 - alpha)))
    Mt_total = M - Mh
    if variant == "conflict":
        Mc = Mt_total // 2          # half the agent population is platform-owned
        Mt = Mt_total - Mc
    else:
        Mc, Mt = 0, Mt_total
    if variant == "hetero":
        Mt_rob = int(round(Mt * p["rho_robust"]))
        Mt_man = Mt - Mt_rob
    else:
        Mt_rob, Mt_man = 0, Mt

    # ---- common random numbers
    rh = rng.uniform(size=(Mh, N))
    qn = rng.normal(0, noise_h, size=(Mh, N))
    gh = rng.gumbel(size=(Mh, N)); gh0 = rng.gumbel(size=(Mh, 1))
    gt_r = rng.gumbel(size=(Mt_rob, N)); gt_r0 = rng.gumbel(size=(Mt_rob, 1))
    gt_m = rng.gumbel(size=(Mt_man, N)); gt_m0 = rng.gumbel(size=(Mt_man, 1))
    gc = rng.gumbel(size=(Mc, N)); gc0 = rng.gumbel(size=(Mc, 1))

    marks, spend = grids(p)
    Agrid = spend
    Ggrid = spend if gamma > 0 else np.array([0.0])
    Rgrid = np.array([0.0, 0.02, 0.05, 0.10, 0.15, 0.25]) if variant == "conflict" else np.array([0.0])

    m = np.full(N, 0.5); A = np.full(N, 15.0); G = np.zeros(N); R = np.zeros(N)

    els = p["elastic_scale"] if variant == "elastic" else 0.0

    def out_opt(g0, price_level):
        """outside option value; under the elastic variant it rises with the price level"""
        return g0[:, 0] + els * price_level

    def util_h(j, pj, Aj):
        return V0 + theta_q * (q[j] + qn[:, j]) - lam * pj + beta_h * np.log1p(Aj) + gh[:, j]

    def util_t(j, pj, Gj, g, gam):
        return mu_t * (V0 + theta_q * q[j] - lam * pj + gam * np.log1p(Gj)) + g[:, j]

    def util_c(j, pj, Rj):
        return mu_t * (V0 + theta_q * q[j] - lam * pj + p["psi"] * Rj * 10.0) + gc[:, j]

    def consider(Aj):
        return 1 / (1 + np.exp(-(a0 + a1 * np.log1p(Aj))))

    def full_state(m, A, G, R):
        pr = c * (1 + m)
        lvl = pr.mean()
        out = {}
        if Mh:
            U = np.stack([util_h(j, pr[j], A[j]) for j in range(N)], 1)
            C = rh < consider(A)[None, :]
            out["h"] = (np.where(C, U, -np.inf), out_opt(gh0, lvl))
        if Mt_rob:
            out["tr"] = (np.stack([util_t(j, pr[j], G[j], gt_r, 0.0) for j in range(N)], 1),
                         out_opt(gt_r0, lvl))
        if Mt_man:
            out["tm"] = (np.stack([util_t(j, pr[j], G[j], gt_m, gamma) for j in range(N)], 1),
                         out_opt(gt_m0, lvl))
        if Mc:
            out["c"] = (np.stack([util_c(j, pr[j], R[j]) for j in range(N)], 1),
                        out_opt(gc0, lvl))
        return pr, out

    def outcomes(m, A, G, R):
        pr, segs = full_state(m, A, G, R)
        sales = np.zeros(N); commission = 0.0
        for key, (U, o) in segs.items():
            if len(U) == 0:
                continue
            k = np.argmax(U, 1)
            win = U[np.arange(len(U)), k] > o
            cnt = np.bincount(k[win], minlength=N)
            sales += cnt
            if key == "c":
                commission += float((pr * R * cnt).sum())
        S = sales.sum()
        rev = float((pr * sales).sum())
        gm = float(((pr - c) * sales).sum()) - commission
        value = V0 + theta_q * q
        surplus = float(((value - pr) * sales).sum())
        best3 = np.argsort(-(theta_q * q - pr))[:3]
        tp = np.repeat(pr, sales.astype(int))
        return dict(
            markup=gm / rev if rev else 0.0,
            ad_spend=float(A.sum()),
            agent_opt_spend=float(G.sum()),
            commission_paid=commission,
            persuasion_total=float(A.sum()) + float(G.sum()) + commission,
            profit=gm - float(A.sum()) - float(G.sum()),
            revenue=rev,
            price_cv=float(tp.std() / tp.mean()) if len(tp) else 0.0,
            units=float(S),
            surplus_per_unit=float(surplus / S) if S else 0.0,
            top3_value_share=float(sales[best3].sum() / S) if S else 0.0,
            hhi=float(((sales / S) ** 2).sum() * 1e4) if S else 0.0,
        )

    # ---------------- smoothed best response
    snaps, changes = [], []
    for it in range(p["iters"]):
        order = rng.permutation(N)
        changed = 0
        for j in order:
            if rng.random() < p["inertia"]:
                continue
            pr, segs = full_state(m, A, G, R)
            rivals = {}
            for key, (U, o) in segs.items():
                if len(U) == 0:
                    continue
                best_other = np.max(np.delete(U, j, 1), 1) if N > 1 else np.full(len(U), -np.inf)
                rivals[key] = np.maximum(best_other, o)

            cand, prof = [], []
            for mk in marks:
                pj = c[j] * (1 + mk)
                for Aj in Agrid:
                    dh = 0
                    if Mh:
                        uh = util_h(j, pj, Aj)
                        ch = rh[:, j] < consider(Aj)
                        dh = int(np.sum(ch & (uh > rivals["h"])))
                    for Gj in Ggrid:
                        dtr = int(np.sum(util_t(j, pj, Gj, gt_r, 0.0) > rivals["tr"])) if Mt_rob else 0
                        dtm = int(np.sum(util_t(j, pj, Gj, gt_m, gamma) > rivals["tm"])) if Mt_man else 0
                        for Rj in Rgrid:
                            dc = int(np.sum(util_c(j, pj, Rj) > rivals["c"])) if Mc else 0
                            margin = pj - c[j]
                            pi = margin * (dh + dtr + dtm) + (margin - pj * Rj) * dc - Aj - Gj
                            cand.append((mk, Aj, Gj, Rj)); prof.append(pi)
            prof = np.asarray(prof, dtype=float)
            scale = prof.std() + 1e-9
            w = np.exp((prof - prof.max()) / (p["tau"] * scale))
            w /= w.sum()
            pick = cand[rng.choice(len(cand), p=w)]
            if pick != (m[j], A[j], G[j], R[j]):
                changed += 1
            m[j], A[j], G[j], R[j] = pick
        changes.append(changed)
        if it >= p["iters"] - p["window"]:
            snaps.append((m.copy(), A.copy(), G.copy(), R.copy()))

    res = [outcomes(*s) for s in snaps]
    keys = [k for k in res[0]]
    avg = {k: float(np.mean([r[k] for r in res])) for k in keys}
    sd = {k + "_sd": float(np.std([r[k] for r in res])) for k in ("markup", "persuasion_total",
                                                                  "top3_value_share", "hhi")}
    avg.update(sd)
    avg.update(alpha=float(alpha), gamma=float(gamma), seed=int(seed), variant=variant,
               revisions_last10=float(np.mean(changes[-p["window"]:])),
               settled=bool(np.mean(changes[-p["window"]:]) < 0.5))
    for k in ("tau", "inertia", "n_mark", "n_spend", "M", "theta_q", "lam", "beta_h", "mu_t",
              "rho_robust", "elastic_scale"):
        avg[k] = p[k]
    return avg


# ---------------------------------------------------------------- job runner
def job(spec):
    t0 = time.time()
    r = run(**spec)
    r["secs"] = round(time.time() - t0, 2)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sweep", choices=["headline", "phase", "sensitivity", "variants", "smoke"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()

    alphas = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0]
    specs = []
    if a.sweep == "smoke":
        specs = [dict(alpha=x, gamma=g, seed=0, M=800, n_mark=8, n_spend=5, iters=12, window=4)
                 for x in (0, .5, 1.0) for g in (0.0, 1.5)]
    elif a.sweep == "headline":
        specs = [dict(alpha=x, gamma=g, seed=s)
                 for s in range(20) for g in (0.0, 1.5) for x in alphas]
    elif a.sweep == "phase":
        gs = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
        specs = [dict(alpha=x, gamma=g, seed=s, M=1500, n_mark=16, n_spend=8)
                 for s in range(4) for g in gs for x in alphas]
    elif a.sweep == "sensitivity":
        base = dict(M=1500, n_mark=12, n_spend=7)
        pert = []
        for k, lo, hi in [("theta_q", 8.0, 16.0), ("lam", 0.7, 1.4),
                          ("beta_h", 0.6, 2.0), ("mu_t", 2.0, 5.0)]:
            for v in (lo, hi):
                pert.append({k: v})
        specs = [dict(alpha=x, gamma=g, seed=s, **base, **pp)
                 for pp in pert for s in range(3) for g in (0.0, 1.5) for x in (0.0, 0.3, 0.5, 1.0)]
    elif a.sweep == "variants":
        base = dict(M=1500, n_mark=12, n_spend=7)
        for v in ("elastic", "hetero", "conflict"):
            for s in range(5):
                for g in (0.0, 1.5):
                    for x in alphas:
                        specs.append(dict(alpha=x, gamma=g, seed=s, variant=v, **base))

    out = a.out or f"results_{a.sweep}.jsonl"
    done = 0
    if os.path.exists(out):
        done = sum(1 for _ in open(out))
        specs = specs[done:]
        print(f"resuming: {done} already done, {len(specs)} to go", flush=True)

    from multiprocessing import Pool
    t0 = time.time()
    with Pool(a.procs) as pool, open(out, "a") as fh:
        for i, r in enumerate(pool.imap_unordered(job, specs, chunksize=1), 1):
            fh.write(json.dumps(r) + "\n"); fh.flush()
            if i % 10 == 0 or i == len(specs):
                el = time.time() - t0
                print(f"{i}/{len(specs)}  {el/60:.1f}m elapsed  "
                      f"{(el/i)*(len(specs)-i)/60:.1f}m left", flush=True)
    print("wrote", out, flush=True)


if __name__ == "__main__":
    main()
