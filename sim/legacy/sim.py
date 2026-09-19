"""
After Attention — twin-buyer market simulation (v0.1)
Mixed population: share alpha of buyers are agent 'twins', rest human.
Sellers choose price markup, ad spend A (targets humans), agent-optimization spend G (targets twins)
by iterated best response on expected profit. Common random numbers for stability.
"""
import numpy as np, json, sys

def run(alpha, gamma=0.0, seed=0, N=12, M=3000, iters=40):
    rng = np.random.default_rng(seed)
    q = np.sort(rng.uniform(0, 1, N))            # true quality
    c = 5 + 10*q                                  # marginal cost
    # buyer parameters
    theta_q, lam_h, lam_t = 12.0, 1.0, 1.0        # same true tastes for both
    beta_h = 1.2                                  # brand/ad persuasion weight (humans)
    noise_h = 1.0                                 # humans: noisy perception of quality
    mu_t = 3.0                                    # twins: more deterministic choice (logit scale)
    a0, a1 = -1.5, 0.9                            # human consideration: pi = sigmoid(a0 + a1*log1p(A))
    V0 = 5.0                                      # category baseline value
    Mh, Mt = int(round(M*(1-alpha))), int(round(M*alpha))
    # common random numbers
    rh = rng.uniform(size=(Mh, N))                # consideration draws
    qn = rng.normal(0, noise_h, size=(Mh, N))     # humans' perception error on quality
    gh = rng.gumbel(size=(Mh, N)); gh0 = rng.gumbel(size=(Mh, 1))
    gt = rng.gumbel(size=(Mt, N)); gt0 = rng.gumbel(size=(Mt, 1))

    marks = np.array([0.01,0.02,0.05,0.1,0.2,0.3,0.45,0.6,0.8,1.0,1.3,1.7])
    Agrid = np.array([0,5,15,40,100,250,600,1500])
    Ggrid = np.array([0,5,15,40,100,250,600,1500]) if gamma > 0 else np.array([0])
    m = np.full(N, 0.5); A = np.full(N, 15.0); G = np.zeros(N)

    def util_h(j, p, Aj):
        return V0 + theta_q*(q[j] + qn[:, j]) - lam_h*p + beta_h*np.log1p(Aj) + gh[:, j]
    def util_t(j, p, Gj):
        return mu_t*(V0 + theta_q*q[j] - lam_t*p + gamma*np.log1p(Gj)) + gt[:, j]
    def consider(Aj):
        return 1/(1+np.exp(-(a0 + a1*np.log1p(Aj))))

    def choices(m, A, G):
        p = c*(1+m)
        Uh = np.stack([util_h(j, p[j], A[j]) for j in range(N)], 1) if Mh else np.zeros((0,N))
        Ch = (rh < consider(A)[None, :]) if Mh else np.zeros((0,N),bool)
        Uh = np.where(Ch, Uh, -np.inf)
        Ut = np.stack([util_t(j, p[j], G[j]) for j in range(N)], 1) if Mt else np.zeros((0,N))
        return p, Uh, Ut

    def outcomes(m, A, G):
      p, Uh, Ut = choices(m, A, G)
      def share(U, g0):
          k = np.argmax(U, 1); win = U[np.arange(len(U)), k] > g0[:,0]
          return np.bincount(k[win], minlength=N), win.mean() if len(U) else 0
      sh, buy_h = share(Uh, gh0) if Mh else (np.zeros(N), 0)
      st, buy_t = share(Ut, gt0) if Mt else (np.zeros(N), 0)
      sales = sh + st; S = sales.sum()
      rev = (p*sales).sum(); gm = ((p-c)*sales).sum()
      value = V0 + theta_q*q                                     # true value per unit
      surplus = ((value - p)*sales).sum()                       # realized true consumer surplus (quality-based)
      vpd = q/c; best_vpd = np.argsort(-(theta_q*q - p))[:3]    # top-3 true net value
      tp = np.repeat(p, sales.astype(int))
      return dict(          markup=float(gm/rev) if rev else 0, ad_spend=float(A.sum()), agent_opt_spend=float(G.sum()),
          profit=float(gm - A.sum() - G.sum()), gross_margin=float(gm), revenue=float(rev),
          price_cv=float(tp.std()/tp.mean()) if len(tp) else 0,
          units=float(S), surplus_per_unit=float(surplus/S) if S else 0,
          top3_value_share=float(sales[best_vpd].sum()/S) if S else 0,
          ad_price_corr=float(np.corrcoef(A, m)[0,1]) if A.std()>0 and m.std()>0 else 0,
          hhi=float(((sales/S)**2).sum()*10000) if S else 0)


    snaps = []
    for it in range(iters):
        if it >= iters-10: snaps.append((m.copy(), A.copy(), G.copy()))
        order = rng.permutation(N)
        changed = 0
        for j in order:
            p, Uh, Ut = choices(m, A, G)
            # best competing utility per buyer excluding j (incl. outside option = gumbel)
            oh = np.maximum(np.max(np.delete(Uh, j, 1), 1) if N>1 else -np.inf, gh0[:,0]) if Mh else None
            ot = np.maximum(np.max(np.delete(Ut, j, 1), 1), gt0[:,0]) if Mt else None
            best, bestv = None, -1e18
            for mk in marks:
                pj = c[j]*(1+mk)
                for Aj in Agrid:
                    dh = 0
                    if Mh:
                        uh = util_h(j, pj, Aj); ch = rh[:, j] < consider(Aj)
                        dh = np.sum(ch & (uh > oh))
                    for Gj in Ggrid:
                        dt = np.sum(util_t(j, pj, Gj) > ot) if Mt else 0
                        prof = (pj - c[j])*(dh+dt) - Aj - Gj
                        if prof > bestv: bestv, best = prof, (mk, Aj, Gj)
            if best != (m[j], A[j], G[j]): changed += 1
            m[j], A[j], G[j] = best
        if changed == 0:
            snaps = [(m.copy(), A.copy(), G.copy())]; break
    conv = changed == 0
    res = [outcomes(*sn) for sn in snaps]
    keys = [k for k in res[0] if isinstance(res[0][k], float)]
    avg = {k: float(np.mean([r[k] for r in res])) for k in keys}
    avg.update(alpha=alpha, gamma=gamma, seed=seed, iters=it+1, converged=bool(conv))
    return avg

if __name__ == "__main__":
    out = []
    alphas = [0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]
    for gamma in [0.0, 1.5]:
        for s in range(int(sys.argv[1]) if len(sys.argv)>1 else 3):
            for a in alphas:
                r = run(a, gamma=gamma, seed=s); out.append(r)
                print(json.dumps({k:(round(v,3) if isinstance(v,float) else v) for k,v in r.items()}), flush=True)
    json.dump(out, open("results.json","w"), indent=1)
