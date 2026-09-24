"""
Small-sample robustness of the preregistered estimator's clustered inference (G = 40 sets).

Nothing here changes estimate.py or the preregistered specification. The point estimates
are estimate.py's conditional logit, reproduced here in vectorised form and asserted equal
to estimate.fit (b and clustered SE) before anything else is reported.

  python3 gamma/robust_se.py [--seed 20260924] [--boot 9999] [--mc 1000] [--mc-boot 499]
                             [--procs 3] [--skip-mc]

What is computed, per model, for b_value, b_B, b_C, b_pos and the H2 contrast b_B - b_C:

  CR0   estimate.fit's clustered sandwich  H^-1 (sum_g S_g S_g') H^-1   (no small-sample factor).
  CR2   a Bell-McCaffrey-type bias-reduced sandwich with Satterthwaite degrees of freedom.
        THIS IS AN APPROXIMATION of the linear-model CR2, not an exact analogue. The
        conditional logit is linearised at the fitted b: with W_i = diag(p_i) - p_i p_i' and
        X_i the 12 x 4 attribute matrix, the cluster score is S_g = B_g u_g with
        B_g = [X_i' W_i^(1/2)]_{i in g} and Pearson-type residuals u_g = W^(+1/2)(e_y - p).
        The cluster leverage is Hat_gg = B_g' H^-1 B_g, whose non-zero eigenvalues are those
        of T_g = H^-1/2 H_g H^-1/2 (H_g = cluster information, H = sum_g H_g). CR2 replaces
        S_g by B_g (I - Hat_gg)^(-1/2) u_g, which reduces exactly to
            S~_g = S_g + H_g H^-1/2 f(T_g) H^-1/2 S_g,   f(l) = ((1-l)^(-1/2) - 1)/l,
        so only 4 x 4 matrices are needed. Satterthwaite df = (tr G)^2 / ||G||_F^2 with
        G = diag(q) - F' H^-1 F (q_g, F_g closed forms below), the standard Pustejovsky-Tipton
        construction under the working model Var(u_g) = I. Because the working model is the
        model-based one, the identity  tr G = c'H^-1 c  is checked numerically as a test of
        the implementation, not of the data.
  WILD   wild cluster bootstrap-t for H2 with Rademacher weights, imposing the null b_B = b_C.
        Because the outcome is a multinomial choice there is no residual to perturb, so this is
        the wild SCORE bootstrap (Kline & Santos 2012): fit the null-restricted model once,
        perturb its cluster scores with Rademacher weights, one Newton step (b* - b~ =
        H~^-1 sum_g w_g S~_g), studentise with the bootstrap-world CR0. The statistic
        bootstrapped is the same CR0 t that estimate.py's z is. It is checked against exact
        re-solves of the perturbed estimating equations for a few draws. With G = 40 there are
        2^40 weight vectors, so 9,999 draws are a Monte Carlo subset; p-values have resolution
        1/(R+1).

Also here: the calibration checks the paper's 8.6 asks for (Monte Carlo on the real design
and the real 40 clusters under three nulls) and the exact binomial arithmetic behind
"9 rejections in 138 draws".
"""
import os
for _v in ("OMP_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import sys, math, time, argparse
from multiprocessing import Pool
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import catalog, estimate

MODELS = [("claude-sonnet-5", "results_gamma_claude-sonnet-5.jsonl"),
          ("gemini-3.8-flash", "results_gamma_gemini-3_8-flash.jsonl"),
          ("gpt-5.6-terra", "results_gamma_gpt-5_6-terra.jsonl"),
          ("gemma4:12b", "results_gamma_gemma4_12b.jsonl")]
NAMES = ["b_value", "b_B", "b_C", "b_pos"]
C_H2 = np.array([0., 1., -1., 0.])
Z95 = 1.6448536269514722


# ------------------------------------------------------------- t distribution (numpy only)
def _betacf(a, b, x, itmax=500, eps=3e-16):
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, itmax):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > tiny else tiny)
        c = 1 + aa / c; c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > tiny else tiny)
        c = 1 + aa / c; c = c if abs(c) > tiny else tiny
        de = d * c; h *= de
        if abs(de - 1) < eps:
            break
    return h


def betainc(a, b, x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lb) * _betacf(a, b, x) / a
    return 1 - math.exp(lb) * _betacf(b, a, 1 - x) / b


def t_sf(t, df):
    p = 0.5 * betainc(df / 2, 0.5, df / (df + t * t))
    return p if t > 0 else 1 - p


def t_upper_quantile(alpha, df):
    lo, hi = 0.0, 50.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if t_sf(mid, df) > alpha else (lo, mid)
    return (lo + hi) / 2


# ----------------------------------------------------------------- conditional logit core
def probs(b, X):
    u = X @ b
    u = u - u.max(1, keepdims=True)
    p = np.exp(u)
    return p / p.sum(1, keepdims=True)


def score_info(b, X, y):
    p = probs(b, X)
    xbar = np.einsum("nj,njk->nk", p, X)
    s = X[np.arange(len(y)), y] - xbar
    info = np.einsum("nj,nja,njb->nab", p, X, X, optimize=True) - np.einsum("na,nb->nab", xbar, xbar)
    return s, info


def loglik(b, X, y):
    return float(np.log(probs(b, X)[np.arange(len(y)), y]).sum())


def newton(X, y, tol=1e-11):
    k = X.shape[2]
    b = np.zeros(k)
    ll = loglik(b, X, y)
    for _ in range(100):
        s, info = score_info(b, X, y)
        step = np.linalg.solve(info.sum(0) + 1e-10 * np.eye(k), s.sum(0))
        t = 1.0
        while True:
            cand = b + t * step
            ll2 = loglik(cand, X, y)
            if ll2 >= ll - 1e-12 or t < 1e-8:
                break
            t /= 2
        done = abs(ll2 - ll) < tol
        b, ll = cand, ll2
        if done:
            break
    return b


def by_cluster(A, cl, G):
    out = np.zeros((G,) + A.shape[1:])
    np.add.at(out, cl, A)
    return out


def cluster_stats(b, X, y, cl, G):
    s, info = score_info(b, X, y)
    return info.sum(0), by_cluster(s, cl, G), by_cluster(info, cl, G)


def sym_pow(M, pw):
    w, V = np.linalg.eigh((M + M.T) / 2)
    return (V * w ** pw) @ V.T


def cr0(H, Sg):
    Hi = np.linalg.inv(H)
    return Hi @ (Sg.T @ Sg) @ Hi


def _f(w):
    w = np.asarray(w)
    small = w < 1e-6
    return np.where(small, 0.5 + 0.375 * w, ((1 - np.minimum(w, 1 - 1e-12)) ** -0.5 - 1) / np.where(small, 1.0, w))


def cr2(H, Sg, Hg):
    Hi = np.linalg.inv(H); Hmh = sym_pow(H, -0.5)
    St = np.empty_like(Sg)
    for g in range(len(Sg)):
        w, V = np.linalg.eigh((lambda T: (T + T.T) / 2)(Hmh @ Hg[g] @ Hmh))
        if w.max() >= 1:
            raise RuntimeError("cluster leverage >= 1; CR2 undefined")
        St[g] = Sg[g] + Hg[g] @ Hmh @ ((V * _f(w)) @ V.T) @ Hmh @ Sg[g]
    return Hi @ (St.T @ St) @ Hi


def satterthwaite(c, H, Hg):
    """Returns (df, tr G); tr G must equal c' H^-1 c (working-model unbiasedness of CR2)."""
    Hi = np.linalg.inv(H); Hh = sym_pow(H, 0.5); Hmh = sym_pow(H, -0.5)
    G = len(Hg); q = np.empty(G); F = np.empty((len(c), G)); cc = Hmh @ c
    for g in range(G):
        w, V = np.linalg.eigh((lambda T: (T + T.T) / 2)(Hmh @ Hg[g] @ Hmh))
        q[g] = cc @ ((V * (w / (1 - w))) @ V.T) @ cc
        F[:, g] = Hh @ ((V * (w / np.sqrt(1 - w))) @ V.T) @ cc
    Gam = np.diag(q) - F.T @ Hi @ F
    tr = float(np.trace(Gam))
    return tr ** 2 / float(np.sum(Gam ** 2)), tr


def restricted_fit(X, y):
    """Null b_B = b_C: fit with the two target columns merged, return the 4-vector."""
    Xr = np.concatenate([X[..., :1], (X[..., 1] + X[..., 2])[..., None], X[..., 3:]], axis=2)
    br = newton(Xr, y)
    return np.array([br[0], br[1], br[1], br[2]])


def wild_score_t(bt, X, y, cl, G, c, W):
    """Bootstrap-world CR0 t for each Rademacher row of W (R x G), null-restricted scores."""
    H, Sg, Hg = cluster_stats(bt, X, y, cl, G)
    Hi = np.linalg.inv(H)
    dev = (W @ Sg) @ Hi
    Sb = W[:, :, None] * Sg[None] - np.einsum("gab,rb->rga", Hg, dev)
    M = np.einsum("rga,rgb->rab", Sb, Sb)
    V = np.matmul(np.matmul(Hi[None], M), Hi[None])
    return (dev @ c) / np.sqrt(np.einsum("a,rab,b->r", c, V, c))


def exact_wild_t(bt, X, y, cl, G, c, w):
    """Same draw, but solving sum_g S_g(b) = sum_g (1 - w_g) S~_g exactly (no linearisation)."""
    _, Sg, _ = cluster_stats(bt, X, y, cl, G)
    tau = ((1 - w)[:, None] * Sg).sum(0)
    b = bt.copy()
    s, info = score_info(b, X, y)
    F = s.sum(0) - tau
    for _ in range(100):
        try:
            step = np.linalg.solve(info.sum(0), F)
        except np.linalg.LinAlgError:
            return float("nan")
        t = 1.0
        while True:                                   # damped: accept only if the residual shrinks
            s2, info2 = score_info(b + t * step, X, y)
            F2 = s2.sum(0) - tau
            if np.linalg.norm(F2) < np.linalg.norm(F) or t < 1e-6:
                break
            t /= 2
        b = b + t * step
        s, info, F = s2, info2, F2
        if np.abs(t * step).max() < 1e-11:
            break
    if np.linalg.norm(F) > 1e-6:                      # no solution near b~ for this draw
        return float("nan")
    H, Sgb, _ = cluster_stats(b, X, y, cl, G)
    R = Sgb - (1 - w)[:, None] * Sg
    Hi = np.linalg.inv(H)
    V = Hi @ (R.T @ R) @ Hi
    return float(c @ (b - bt)) / math.sqrt(float(c @ V @ c))


# --------------------------------------------------------------------------- real data
def build(path, sets):
    rows = estimate.load([os.path.join(HERE, path)])
    X, y, cl = estimate.design(rows, sets)
    _, cl = np.unique(cl, return_inverse=True)
    return np.stack(X), np.asarray(y), cl, rows


def real_data(seed, R, sets):
    rng = np.random.default_rng(seed)
    print(f"\n{'=' * 100}\nREAL DATA   seed={seed}   wild score bootstrap R={R:,}   G=40 clusters (choice sets)")
    summary = []
    for name, path in MODELS:
        t0 = time.time()
        X, y, cl, rows = build(path, sets)
        G = int(cl.max()) + 1
        b = newton(X, y)
        H, Sg, Hg = cluster_stats(b, X, y, cl, G)
        V0, V2 = cr0(H, Sg), cr2(H, Sg, Hg)
        # identical to the preregistered estimator
        bE, seE, VE, nE = estimate.fit(rows, sets)
        assert np.allclose(b, bE, atol=1e-6) and np.allclose(np.sqrt(np.diag(V0)), seE, atol=1e-6), \
            "vectorised fit disagrees with estimate.fit"
        print(f"\n--- {name}  n={len(y):,}  G={G}   (b and CR0 SE identical to estimate.fit to 1e-6)")
        print(f"{'':10s}{'est':>9s}{'CR0 se':>9s}{'CR0 z':>8s}{'CR2 se':>9s}{'se ratio':>9s}{'Satt df':>9s}"
              f"{'CR2 t':>8s}{'p (2-sided, t_df)':>19s}")
        cs = [np.eye(4)[i] for i in range(4)] + [C_H2]
        labels = NAMES + ["b_B - b_C"]
        for lab, c in zip(labels, cs):
            est = float(c @ b); s0 = math.sqrt(float(c @ V0 @ c)); s2 = math.sqrt(float(c @ V2 @ c))
            df, tr = satterthwaite(c, H, Hg)
            assert abs(tr - float(c @ np.linalg.inv(H) @ c)) < 1e-8 * max(1, tr), "tr G != c'H^-1c"
            t2 = est / s2
            print(f"{lab:10s}{est:9.4f}{s0:9.4f}{est / s0:8.2f}{s2:9.4f}{s2 / s0:9.3f}{df:9.1f}{t2:8.2f}"
                  f"{2 * t_sf(abs(t2), df):19.2e}")
        # wild score bootstrap-t for H2
        est = float(C_H2 @ b); s0 = math.sqrt(float(C_H2 @ V0 @ C_H2)); t_obs = est / s0
        df2, _ = satterthwaite(C_H2, H, Hg); s2 = math.sqrt(float(C_H2 @ V2 @ C_H2))
        bt = restricted_fit(X, y)
        W = rng.choice([-1.0, 1.0], size=(R, G))
        ts = wild_score_t(bt, X, y, cl, G, C_H2, W)
        p_boot1 = (1 + np.sum(ts >= t_obs)) / (R + 1)
        p_boot2 = (1 + np.sum(np.abs(ts) >= abs(t_obs))) / (R + 1)
        crit = float(np.quantile(ts, 0.95))
        print(f"H2 wild score bootstrap-t: t_obs={t_obs:.2f}  bootstrap 95th pct of t*={crit:.2f} (normal 1.645, "
              f"t_{df2:.0f} {t_upper_quantile(.05, df2):.2f})  sd(t*)={ts.std():.3f}")
        print(f"   one-sided p = {p_boot1:.4f} ({int(np.sum(ts >= t_obs))} of {R:,} draws >= t_obs; floor 1/(R+1)="
              f"{1 / (R + 1):.4f})   two-sided p = {p_boot2:.4f}")
        # linearisation check against exact re-solves
        dif = []
        for k in range(5):
            te = exact_wild_t(bt, X, y, cl, G, C_H2, W[k])
            if not math.isnan(te):
                dif.append(abs(te - ts[k]))
        print(f"   score-bootstrap vs exact re-solve of perturbed equations, {len(dif)} of 5 draws solved: max |t* diff| = "
              f"{max(dif) if dif else float('nan'):.4f}   ({time.time() - t0:.0f}s)")
        summary.append((name, est, s0, est / s0, s2, df2, est / s2, t_sf(est / s2, df2), p_boot1, crit))
    print(f"\n{'=' * 100}\nH2 (b_B - b_C) DECISION-RULE TABLE   (significance = one-sided 5%, the registered H2 test)")
    print(f"{'model':18s}{'est':>8s}{'CR0 se':>8s}{'CR0 z':>7s}{'CR2 se':>8s}{'df':>6s}{'CR2 t':>7s}"
          f"{'p CR2 (1s)':>12s}{'p wild (1s)':>13s}{'wild crit':>10s}  significant under both?")
    for (name, est, s0, z, s2, df, t2, p2, pb, crit) in summary:
        ok = (p2 < .05) and (pb < .05)
        print(f"{name:18s}{est:8.3f}{s0:8.3f}{z:7.2f}{s2:8.3f}{df:6.1f}{t2:7.2f}{p2:12.2e}{pb:13.4f}{crit:10.2f}  "
              f"{'YES' if ok else 'NO'}")
    return summary


# ------------------------------------------------------------------ Monte Carlo calibration
_MC = {}


def _mc_init(X, cl, G):
    _MC.update(X=X, cl=cl, G=G)


def _mc_one(args):
    scen, ss, mc_boot = args
    rng = np.random.default_rng(ss)
    X, cl, G = _MC["X"], _MC["cl"], _MC["G"]
    n = len(cl)
    if scen == "A":                                    # uniform random choice, as null_check.py
        y = rng.integers(0, 12, size=n)
    else:
        B = np.tile([1.43, 0.62, 0.62, -0.045], (G, 1))
        if scen == "C":                                # set-level heterogeneity in both target effects
            B[:, 1] += rng.normal(0, 0.5, G); B[:, 2] += rng.normal(0, 0.5, G)
        p = np.exp(np.einsum("njk,nk->nj", X, B[cl]))
        p /= p.sum(1, keepdims=True)
        y = np.minimum((np.cumsum(p, 1) < rng.random(n)[:, None]).sum(1), 11)
    b = newton(X, y)
    H, Sg, Hg = cluster_stats(b, X, y, cl, G)
    V0, V2 = cr0(H, Sg), cr2(H, Sg, Hg)
    est = float(C_H2 @ b); s0 = math.sqrt(float(C_H2 @ V0 @ C_H2)); s2 = math.sqrt(float(C_H2 @ V2 @ C_H2))
    df, _ = satterthwaite(C_H2, H, Hg)
    bt = restricted_fit(X, y)
    W = rng.choice([-1.0, 1.0], size=(mc_boot, G))
    ts = wild_score_t(bt, X, y, cl, G, C_H2, W)
    pb = (1 + np.sum(ts >= est / s0)) / (mc_boot + 1)
    return est / s0, est / s2, df, pb


def wilson(k, n, z=1.959964):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def monte_carlo(seed, N, mc_boot, procs, sets):
    X, y, cl, _ = build("results_gamma_gemma4_12b.jsonl", sets)
    G = int(cl.max()) + 1
    print(f"\n{'=' * 100}\nMONTE CARLO CALIBRATION   seed={seed}   {N:,} datasets per scenario, wild score bootstrap "
          f"R={mc_boot}, {procs} processes\nreal design (arms, framings, reps, positions, 40 clusters); H2 true b_B - b_C = 0"
          f" in every scenario")
    desc = {"A": "A  uniform random choice (what null_check.py does; no value effect)",
            "B": "B  value-driven choice (b_value 1.43), b_B = b_C = 0.62, no set heterogeneity",
            "C": "C  as B plus set-level heterogeneity in both target effects, sd 0.5 (stress test; illustrative)"}
    ss_all = np.random.SeedSequence(seed).spawn(3)
    out = {}
    for si, scen in enumerate("ABC"):
        t0 = time.time()
        seeds = ss_all[si].spawn(N)
        with Pool(procs, initializer=_mc_init, initargs=(X, cl, G)) as pool:
            res = pool.map(_mc_one, [(scen, s, mc_boot) for s in seeds], chunksize=4)
        z, t2, df, pb = (np.array(v) for v in zip(*res))
        crit2 = np.array([t_upper_quantile(.05, d) for d in df])
        rej = {"CR0 z > 1.645 (estimate.py as used)": int(np.sum(z > Z95)),
               "CR2 t > t_df(0.95) (Satterthwaite)": int(np.sum(t2 > crit2)),
               "wild score bootstrap-t p < .05": int(np.sum(pb < .05))}
        print(f"\n{desc[scen]}   [{time.time() - t0:.0f}s]")
        print(f"   z (CR0): mean {z.mean():+.3f}  sd {z.std(ddof=1):.3f} (se of sd ~ {z.std(ddof=1) / math.sqrt(2 * (N - 1)):.3f})"
              f"   mean Satterthwaite df {df.mean():.1f}")
        for k, v in rej.items():
            lo, hi = wilson(v, N)
            print(f"   one-sided 5% rejection, {k:42s} {v / N:6.3f}   95% CI [{lo:.3f}, {hi:.3f}]   ({v}/{N})")
        out[scen] = (z.std(ddof=1), {k: v / N for k, v in rej.items()})
    return out


# ------------------------------------------------------------------ the 138-draw arithmetic
def binom_tail(k, n, p):
    return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1))


def clopper_pearson(k, n, a=0.05):
    def cdf_lower(p, kk):   # P(X <= kk)
        return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(0, kk + 1))
    lo, hi = 0.0, 1.0
    for _ in range(100):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if binom_tail(k, n, m) < a / 2 else (lo, m)
    L = hi
    lo, hi = 0.0, 1.0
    for _ in range(100):
        m = (lo + hi) / 2
        lo, hi = (lo, m) if cdf_lower(m, k) < a / 2 else (m, hi)
    return L, lo


def chi2_sf(x, k):
    """Upper tail of chi-square(k) via the regularised upper incomplete gamma (series / CF)."""
    a, xx = k / 2, x / 2
    if xx < a + 1:
        term = s = 1 / a
        for n in range(1, 2000):
            term *= xx / (a + n); s += term
            if abs(term) < 1e-16 * abs(s): break
        return 1 - s * math.exp(-xx + a * math.log(xx) - math.lgamma(a))
    tiny = 1e-300
    b = xx + 1 - a; c = 1 / tiny; d = 1 / b; h = d
    for i in range(1, 2000):
        an = -i * (i - a); b += 2; d = an * d + b; d = d if abs(d) > tiny else tiny
        c = b + an / c; c = c if abs(c) > tiny else tiny
        d = 1 / d; de = d * c; h *= de
        if abs(de - 1) < 1e-16: break
    return math.exp(-xx + a * math.log(xx) - math.lgamma(a)) * h


def arithmetic():
    print(f"\n{'=' * 100}\nTHE 138-DRAW ARITHMETIC (paper 8.6 / paper/CLI_RUN_REQUEST.md item 4.3)")
    p = binom_tail(9, 138, 0.05)
    lo, hi = clopper_pearson(9, 138)
    print(f"   P(X >= 9 | n=138, p=0.05) = {p:.4f}   (exact binomial, one-sided)   expected rejections = {138 * .05:.1f}")
    print(f"   observed 9/138 = {9 / 138:.3f}; exact 95% Clopper-Pearson CI [{lo:.3f}, {hi:.3f}] contains 0.05")
    s = 1.11
    q = 137 * s * s
    print(f"   sd(z) = {s} from n=138 draws: (n-1)s^2 = {q:.1f} vs chi2(137) mean 137; upper-tail p = {chi2_sf(q, 137):.3f}"
          f" (assumes z is normal)   se of sd = {s / math.sqrt(2 * 137):.3f}")


# ------------------------------------------------------------------------------ self-tests
def self_test():
    assert abs(t_sf(1.6848, 39) - 0.05) < 2e-4, t_sf(1.6848, 39)
    assert abs(t_sf(2.0227, 39) - 0.025) < 2e-4
    assert abs(t_upper_quantile(.05, 1000) - 1.6465) < 2e-3
    assert abs(chi2_sf(137, 137) - 0.4839) < 2e-3, chi2_sf(137, 137)   # Wilson-Hilferty: 0.484
    assert abs(chi2_sf(3.841458820694124, 1) - 0.05) < 1e-9
    assert abs(binom_tail(1, 10, .5) - (1 - .5 ** 10)) < 1e-12
    print("self-test: t, chi-square and binomial helpers OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260924)
    ap.add_argument("--boot", type=int, default=9999)
    ap.add_argument("--mc", type=int, default=1000)
    ap.add_argument("--mc-boot", type=int, default=499)
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--skip-mc", action="store_true")
    a = ap.parse_args()
    print(f"seed = {a.seed}")
    self_test()
    sets = catalog.build()
    real_data(a.seed, a.boot, sets)
    arithmetic()
    if not a.skip_mc:
        monte_carlo(a.seed, a.mc, a.mc_boot, a.procs, sets)
