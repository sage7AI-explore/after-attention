"""
Estimation for the gamma measurement, as preregistered.

Primary specification is a conditional logit over the 12 alternatives in each choice set:

    P(choose j) proportional to exp( b_value * value_j
                                   + b_B * 1[j is target and arm is B]
                                   + b_C * 1[j is target and arm is C]
                                   + b_pos * position_j )

The persuasion effect is b_B - b_C (H2); the length effect is b_C. Standard errors are
clustered by choice set with a sandwich estimator, since repetitions within a set share
the same products and the same manipulated sentence.

Reports the reduced-form effect as the primary quantity. Mapping it to the simulation's
gamma requires a normalization for "one description rewrite" that is not observable, so a
range under stated normalizations is given rather than a single number.
"""
import json, sys, collections
import numpy as np

import catalog


def load(paths):
    rows = []
    for p in paths:
        for line in open(p):
            r = json.loads(line)
            if r.get("choice"):
                rows.append(r)
    return rows


def design(rows, sets):
    """Build per-observation alternative matrices: value, is_target_B, is_target_C, position."""
    by_id = {s["set_id"]: s for s in sets}
    X, y, clusters = [], [], []
    for r in rows:
        s = by_id[r["set_id"]]
        prods = s["products"]
        ids = [p["id"] for p in prods]
        # positions are recorded only for the target; reconstruct the rest deterministically
        # from the same rng the runner used
        import random
        rng = random.Random(
            catalog.seed_for(r["set_id"], r["arm"], r["framing"], r["rep"]))
        _, positions = catalog.render(s, r["arm"], rng)
        # the runner recorded the target's position independently; if the replayed
        # permutation disagrees, the position control is silently wrong and every
        # estimate below it is suspect. Fail loudly instead.
        if r.get("target_position") and positions[s["target_id"]] != r["target_position"]:
            raise RuntimeError(
                f"position replay mismatch on set {r['set_id']} arm {r['arm']} "
                f"framing {r['framing']} rep {r['rep']}: replayed "
                f"{positions[s['target_id']]}, runner recorded {r['target_position']}. "
                f"The estimator and runner disagree about randomization; do not trust "
                f"any position-controlled estimate until this is resolved.")
        vals = np.array([p["value"] for p in prods], dtype=float)
        vals = (vals - vals.mean()) / (vals.std() + 1e-9)
        tgt = np.array([1.0 if i == s["target_id"] else 0.0 for i in ids])
        pos = np.array([positions[i] for i in ids], dtype=float)
        pos = (pos - pos.mean()) / (pos.std() + 1e-9)
        isB = tgt * (1.0 if r["arm"] == "B" else 0.0)
        isC = tgt * (1.0 if r["arm"] == "C" else 0.0)
        X.append(np.column_stack([vals, isB, isC, pos]))
        y.append(ids.index(r["choice"]))
        clusters.append(r["set_id"])
    return X, np.array(y), np.array(clusters)


def _probs(b, Xi):
    u = Xi @ b
    u -= u.max()
    p = np.exp(u)
    return p / p.sum()


def gradient(b, X, y):
    """Analytic score: observed attributes minus expected attributes, summed."""
    g = np.zeros(len(b))
    for Xi, yi in zip(X, y):
        g += Xi[yi] - _probs(b, Xi) @ Xi
    return g


def scores(b, X, y):
    """Per-observation score vectors, for the clustered sandwich."""
    return np.array([Xi[yi] - _probs(b, Xi) @ Xi for Xi, yi in zip(X, y)])


def hessian(b, X, y):
    """Analytic negative Hessian of the log-likelihood (the information matrix)."""
    k = len(b)
    H = np.zeros((k, k))
    for Xi in X:
        p = _probs(b, Xi)
        xbar = p @ Xi
        H += (Xi * p[:, None]).T @ Xi - np.outer(xbar, xbar)
    return H


def loglik(b, X, y):
    return float(sum(np.log(_probs(b, Xi)[yi]) for Xi, yi in zip(X, y)))


def fit(rows, sets, tol=1e-9, max_iter=50):
    """Conditional logit by Newton-Raphson. No scipy: the gradient and Hessian are
    analytic, so this converges in a handful of steps and needs numpy only."""
    X, y, cl = design(rows, sets)
    k = X[0].shape[1]
    b = np.zeros(k)
    ll = loglik(b, X, y)
    for _ in range(max_iter):
        g = gradient(b, X, y)
        H = hessian(b, X, y)
        step = np.linalg.solve(H + 1e-10 * np.eye(k), g)
        # backtrack if a full Newton step overshoots
        t_step = 1.0
        for _ in range(30):
            cand = b + t_step * step
            ll_new = loglik(cand, X, y)
            if ll_new >= ll:
                break
            t_step /= 2
        if abs(ll_new - ll) < tol:
            b, ll = cand, ll_new
            break
        b, ll = cand, ll_new

    S = scores(b, X, y)
    Hinv = np.linalg.pinv(hessian(b, X, y))
    meat = np.zeros((k, k))
    for c in np.unique(cl):
        sc = S[cl == c].sum(0)
        meat += np.outer(sc, sc)
    V = Hinv @ meat @ Hinv
    return b, np.sqrt(np.diag(V)), V, len(rows)


def report(paths):
    sets = catalog.build()
    rows = load(paths)
    if not rows:
        print("no parsed observations"); return
    models = collections.Counter(r["model"] for r in rows)
    print(f"observations {len(rows):,}   models: {dict(models)}")

    for model in sorted(models):
        sub = [r for r in rows if r["model"] == model]
        b, se, V, n = fit(sub, sets)
        names = ["value", "target x B (persuasion+length)", "target x C (length only)", "position"]
        print(f"\n=== {model}  (n={n:,}) ===")
        for nm, bi, si in zip(names, b, se):
            z = bi / si if si else float("nan")
            print(f"  {nm:32s} {bi:+8.4f}  (se {si:.4f}, z {z:+.2f})")

        # H2: persuasion net of length
        d = b[1] - b[2]
        sd = np.sqrt(max(V[1, 1] + V[2, 2] - 2 * V[1, 2], 0))
        z = d / sd if sd else float("nan")
        print(f"  {'H2: persuasion net of length':32s} {d:+8.4f}  (se {sd:.4f}, z {z:+.2f})")

        # descriptive: target choice share by arm
        print("  target choice share:", end="")
        for arm in ("A", "B", "C"):
            s = [r["chose_target"] for r in sub if r["arm"] == arm]
            print(f"  {arm}={np.mean(s):.3f}" if s else f"  {arm}=n/a", end="")
        print()
        # and how often the best-value product wins, by arm
        print("  best-value share:   ", end="")
        for arm in ("A", "B", "C"):
            s = [r["chose_best_value"] for r in sub if r["arm"] == arm]
            print(f"  {arm}={np.mean(s):.3f}" if s else f"  {arm}=n/a", end="")
        print()

    print("\nH2 is the test that carries the paper's claim. If it is indistinguishable from "
          "zero,\nagents in this setting respond to description length rather than to "
          "persuasion, and\nthe paper's persuadability mechanism must be rewritten "
          "accordingly (preregistration §7).")


if __name__ == "__main__":
    report(sys.argv[1:] or ["results_gamma_claude-sonnet-5_dry.jsonl"])
