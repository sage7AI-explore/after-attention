"""
Estimator for the context study (urgency x stakes crossed with the matched triad).

Conditional logit over the 12 offers of each choice set, pooling the four context cells:

  U(j) = b_v   * value_j
       + b_vU  * value_j * urgent        does urgency change the weight on true value?
       + b_vS  * value_j * stakes        does stakes?
       + b_B   * [target, arm B]         persuasion + length, in the (0,0) cell
       + b_C   * [target, arm C]         length only, in the (0,0) cell
       + b_BU  * [target, arm B] * urgent
       + b_CU  * [target, arm C] * urgent
       + b_BS  * [target, arm B] * stakes
       + b_CS  * [target, arm C] * stakes
       + b_p   * position_j

Preregistered contrasts (see PREREGISTRATION.md, amendment of 21 September 2026):

  H2'  persuasion net of length, unhurried and routine   b_B  - b_C      replication
  H3   change in that under URGENCY                       b_BU - b_CU     directional, > 0
  H4   change in that under HIGH STAKES                   b_BS - b_CS     two-sided

H3 is the test the study exists for. Urgency and stakes enter additively; the (1,1) cell is
reported descriptively as a check on that additivity rather than fitted with a three-way
term, which would cost power the design does not have.

SEs clustered by choice set. Positions are replayed from context.seed_for and checked
against the recorded position, exactly as in the base estimator.
"""
import json, sys, collections, random
import numpy as np

import catalog, context
from estimate import _probs, gradient, hessian, loglik, scores

NAMES = ["value", "value x urgent", "value x stakes",
         "target x B", "target x C",
         "target x B x urgent", "target x C x urgent",
         "target x B x stakes", "target x C x stakes",
         "position"]


def load(paths):
    rows = []
    for p in paths:
        for line in open(p):
            r = json.loads(line)
            if r.get("design") != "context":
                raise RuntimeError(f"{p}: row is not from the context design; use estimate.py")
            if r.get("choice"):
                rows.append(r)
    return rows


def design(rows, sets):
    by_id = {s["set_id"]: s for s in sets}
    X, y, cl = [], [], []
    for r in rows:
        s = by_id[r["set_id"]]
        ids = [p["id"] for p in s["products"]]
        rng = random.Random(context.seed_for(r["set_id"], r["arm"], r["framing"], r["rep"]))
        _, positions = catalog.render(s, r["arm"], rng)
        if r.get("target_position") and positions[s["target_id"]] != r["target_position"]:
            raise RuntimeError(
                f"position replay mismatch, set {r['set_id']} arm {r['arm']} cell {r['framing']} "
                f"rep {r['rep']}: replayed {positions[s['target_id']]}, recorded "
                f"{r['target_position']}. Do not trust any position-controlled estimate.")
        U, S = float(r["urgent"]), float(r["stakes"])
        v = np.array([p["value"] for p in s["products"]], float); v = (v - v.mean()) / (v.std() + 1e-9)
        pos = np.array([positions[i] for i in ids], float); pos = (pos - pos.mean()) / (pos.std() + 1e-9)
        tgt = np.array([1.0 if i == s["target_id"] else 0.0 for i in ids])
        B = tgt * (r["arm"] == "B"); C = tgt * (r["arm"] == "C")
        X.append(np.column_stack([v, v * U, v * S, B, C, B * U, C * U, B * S, C * S, pos]))
        y.append(ids.index(r["choice"]))
        cl.append(r["set_id"])
    return X, np.array(y), np.array(cl)


def fit(X, y, cl, tol=1e-9, max_iter=60):
    k = X[0].shape[1]; b = np.zeros(k); ll = loglik(b, X, y)
    for _ in range(max_iter):
        g = gradient(b, X, y); H = hessian(b, X, y)
        step = np.linalg.solve(H + 1e-10 * np.eye(k), g); t = 1.0
        for _ in range(30):
            cand = b + t * step; ll_new = loglik(cand, X, y)
            if ll_new >= ll: break
            t /= 2
        done = abs(ll_new - ll) < tol
        b, ll = cand, ll_new
        if done: break
    Sm = scores(b, X, y); Hinv = np.linalg.pinv(hessian(b, X, y))
    meat = sum(np.outer(Sm[cl == c].sum(0), Sm[cl == c].sum(0)) for c in np.unique(cl))
    V = Hinv @ meat @ Hinv
    return b, V


def contrast(b, V, i, j):
    d = b[i] - b[j]; sd = np.sqrt(max(V[i, i] + V[j, j] - 2 * V[i, j], 0))
    return d, sd, (d / sd if sd else float("nan"))


def report(paths):
    sets = context.build()
    rows = load(paths)
    models = collections.Counter(r["model"] for r in rows)
    print(f"observations {len(rows):,}   models: {dict(models)}\n")
    for model in sorted(models):
        sub = [r for r in rows if r["model"] == model]
        X, y, cl = design(sub, sets)
        b, V = fit(X, y, cl)
        se = np.sqrt(np.diag(V))
        print(f"=== {model}  (n={len(sub):,}) ===")
        for nm, bi, si in zip(NAMES, b, se):
            print(f"  {nm:24s} {bi:+8.4f}  (se {si:.4f}, z {bi/si if si else float('nan'):+.2f})")
        print()
        for label, i, j in (("H2' persuasion net of length", 3, 4),
                            ("H3  change under URGENCY", 5, 6),
                            ("H4  change under STAKES", 7, 8)):
            d, sd, z = contrast(b, V, i, j)
            print(f"  {label:32s} {d:+8.4f}  (se {sd:.4f}, z {z:+.2f})")
        print("\n  descriptive, target choice share by cell (urgent, stakes):")
        for cell in context.CELLS:
            line = f"    {str(cell):8s}"
            for arm in "ABC":
                s = [r["chose_target"] for r in sub
                     if (r["urgent"], r["stakes"]) == cell and r["arm"] == arm]
                line += f"  {arm}={np.mean(s):.3f}" if s else f"  {arm}=n/a"
            bs = [r["chose_best_value"] for r in sub if (r["urgent"], r["stakes"]) == cell]
            line += f"   best-value={np.mean(bs):.3f}" if bs else ""
            print(line)
        print()
    print("H3 is the test this study exists for. A null on H3 is reported as a null: "
          "it would mean\nagents are no more persuadable under urgency, which is a finding, "
          "not a failure.")


if __name__ == "__main__":
    report(sys.argv[1:])
