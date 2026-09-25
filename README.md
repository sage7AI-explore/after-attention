# After Attention — simulation code and results

Replication material for *After Attention: The Economics of Markets Where the Buyer Is an Agent*
(Vissa and Sangaraju, 2026) — **[SSRN 7516238](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7516238)** · DOI [10.2139/ssrn.7516238](https://doi.org/10.2139/ssrn.7516238). The current draft is
[`paper/After_Attention_draft_v0.14.pdf`](paper/After_Attention_draft_v0.14.pdf). The version first posted to
SSRN is [`v0.11`](paper/After_Attention_draft_v0.11.pdf); v0.13 revised it and withdrew or qualified several
of its claims, and v0.14 adds three sections without changing any v0.13 result (see `CHANGELOG.md`).
SSRN currently carries v0.13; v0.14 is not yet posted. Earlier drafts are kept beside them so that withdrawn results stay
inspectable.

The paper models a consumer market with a mixed population of human and agent ("twin") buyers, in
which sellers choose price, consumer-directed advertising, and agent-directed optimization spend.
Everything reported in the paper is produced by the code in this repository from the seeds recorded
here.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 sim/sim2.py smoke            # ~1 second, sanity check
```

## Reproducing the paper

| Paper object | Command | Runtime (2 cores) | Output |
|---|---|---|---|
| Table 1, Figure 1 | `python3 sim/sim2.py headline` | ~15 min | `results/results_headline.jsonl` |
| Figure 2 (phase diagram) | `python3 sim/sim2.py phase` | ~9 min | `results/results_phase.jsonl` |
| Table 2 (sensitivity) | `python3 sim/sim2.py sensitivity` | ~5 min | `results/results_sensitivity.jsonl` |
| Table 3 (variants and baseline) | `python3 sim/sim2.py variants` | ~27 min | `results/results_variants.jsonl` |
| Elastic-demand volumes (§7.6) | `python3 sim/run_elastic.py` | ~7 min | `results/results_elastic.jsonl` |
| ψ sweep (§7.6) | `python3 sim/run_psi.py` | ~7 min | `results/results_psi_sensitivity.jsonl` |
| Exact-BR convergence check (App. C) | `python3 sim/run_exact.py coarse` | ~6 min | `results/results_exact_coarse.jsonl` |
| Same, finer grid (App. C) | `python3 sim/run_exact.py fine_ladder` | ~9 min | `results/results_exact_fine_ladder.jsonl` |
| Fine α grid near the knee (App. C) | `python3 sim/run_knee.py` | ~25 min | `results/results_knee_fine.jsonl` |
| Exact BR at full adoption (App. C) | `python3 sim/run_exact.py fine` | ~9 min | `results/results_exact_fine.jsonl` |
| Smoothing sweep (App. C) | `python3 sim/sim2.py headline --set tau=0.05 --out results/results_headline_tau0.05.jsonl` | ~15 min | `results/results_headline_tau0.05.jsonl` |
| Smoothing sweep (App. C) | `python3 sim/sim2.py headline --set tau=0.3 --out results/results_headline_tau0.3.jsonl` | ~15 min | `results/results_headline_tau0.3.jsonl` |
| Agent-sharpness sweep (App. C) | `python3 sim/sim2.py headline --set mu_t=10 --out results/results_headline_mu10.jsonl` | ~15 min | `results/results_headline_mu10.jsonl` |
| Agent-sharpness sweep (App. C) | `python3 sim/sim2.py headline --set mu_t=20 --out results/results_headline_mu20.jsonl` | ~15 min | `results/results_headline_mu20.jsonl` |

Then:

```bash
python3 sim/plot2.py results/results_headline.jsonl figures/fig_outcomes.png   # Figure 1
python3 sim/plot_phase.py results/results_phase.jsonl figures/fig_phase.png    # Figure 2
```

Sweeps append to their output file and resume if interrupted: re-running the same command picks up
where it stopped rather than starting over.
For the same reason every variant sweep above passes its own `--out`: without one it writes to
`results_headline.jsonl`, finds 440 rows already present, and exits having done nothing.

## What the model does

Twelve sellers with quality `q ~ U(0,1)` and marginal cost `c = 5 + 10q` choose a markup, advertising
spend `A` (which buys entry into human consideration sets and shifts human perceived value) and
agent-directed spend `G` (which shifts twin choice, weighted by the persuadability parameter `gamma`).
A share `alpha` of buyers are twins: they consider every seller, perceive quality without error, and
choose sharply. Humans consider a subset, perceive quality noisily, and are persuadable.

Sellers revise by **smoothed best response**: a revising seller draws its action from a logit
distribution over candidate profits (temperature `tau`, scaled by the dispersion of those profits) and
skips a revision with probability `iota`. Exact best response is the `tau -> 0` limit. Smoothing is
not cosmetic: Proposition 3 in the paper proves that the interior of this game has no pure-strategy
equilibrium, so an exact dynamic cycles there and reported values would depend on where the cycle is
cut.

### Variants

| Flag | Behavior |
|---|---|
| `base` | as above |
| `elastic` | the outside option's value rises with the market price level, so category demand can contract |
| `hetero` | the twin population is a mixture: a share `rho_robust` have `gamma = 0`, the rest are manipulable |
| `conflict` | a third buyer type — a platform-owned agent that weights a per-sale commission offered by the seller. The commission is a transfer out of the seller's margin, not a fixed cost, which is what distinguishes a conflicted agent from a merely persuadable one |

## Output schema

Each line of a `.jsonl` results file is one run:

| Field | Meaning |
|---|---|
| `alpha`, `gamma`, `seed`, `variant` | run identifiers |
| `markup` | gross margin as a share of revenue |
| `ad_spend`, `agent_opt_spend`, `commission_paid` | persuasion instruments |
| `persuasion_total` | sum of the three |
| `top3_value_share` | sales share of the three sellers offering the best true quality-adjusted value |
| `hhi` | Herfindahl–Hirschman index of sales |
| `surplus_per_unit` | realized consumer net value per unit (see the scale note below) |
| `price_cv` | coefficient of variation of transaction prices |
| `revisions_last10` | mean number of sellers changing action per iteration over the averaging window |
| `*_sd` | dispersion across the averaging window |

Values are averages over the final 10 of 40 iterations. The runner averages across seeds.

## Reading the numbers honestly

- **`surplus_per_unit` levels are not meaningful**, only their direction and relative movement. Under
  this parameterization `V0 + theta_q * q` is small relative to equilibrium prices, so the series is
  negative at low `alpha`.
- **There is a noise floor.** Smoothed best response sometimes funds instruments with no return. The
  cleanest measure is agent-directed spend at `alpha = 0`, where no twins exist: roughly 300 units on
  the headline configuration. Differences of that order are not findings.
- **Grids matter.** An earlier version of this code used a 12-point markup grid and reported that the
  fully manipulable market routed 95% of sales away from the best-value sellers. That result does not
  survive grid refinement under either dynamic and has been withdrawn; see the paper's §6 and
  Appendix C. `sim.py` (the original harness) is kept in `sim/legacy/` so the artifact is reproducible.
- **`gamma` is a stylized simulation parameter.** It is not the same object as the measured effect in
  `gamma/`: §8.4 of the paper maps one to the other and the mapping needs two unobserved quantities,
  so it yields a range (roughly 0.07 to 2.14) rather than a value. The measurement establishes that
  the parameter is far from zero; it does not pin it.

## Measuring γ

`gamma/` holds the harness for the empirical piece: estimating how far agent-directed text moves
a real shopping agent's choice. `gamma/PREREGISTRATION.md` was committed before any API call and
states the hypotheses, the three-arm design, the estimator, the stopping rule and — in §7 — the
result that would make us withdraw the persuadability mechanism from the paper.

```bash
python3 gamma/pricing.py                                        # projected cost per model
python3 gamma/run.py --model claude-sonnet-5 --dry-run           # whole pipeline, zero cost
python3 gamma/estimate.py gamma/results_gamma_*_dry.jsonl        # estimator on stub data
```

Live runs read keys from the environment (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`),
never from a file in the repo and never from an argument:

```bash
python3 gamma/run.py --model claude-sonnet-5  --cap 50
```

The runner refuses to start if its pre-flight projection exceeds the cap, ledgers actual spend from
the token counts the APIs report, and hard-stops at 90% of the cap with partial results written.
Runs resume: re-running the same command continues rather than re-spending.

**Three arms, not two.** A is attested facts only; B adds agent-directed persuasion; C adds neutral
filler of the same length. The quantity that carries the paper's claim is **B − C**, not B − A —
without the length placebo, a text-volume effect would be misread as persuasion.

**What the experiments found.** One sentence of unverifiable promotional text raises a mid-ranked
product's selection rate by a factor of 8 to 14 across three frontier models, while a length-matched
neutral placebo does nothing (z = -0.04, +1.18, +1.25), and the share of choices going to the
best-value product falls on every model. A second preregistered experiment (19,200 further decisions,
`gamma/context.py`) finds no detectable change in that susceptibility when the buying instruction
states urgency. A registered open-weight replication on a local Gemma model is running and is
reported in §8.7 as incomplete. All 37,200 measured decisions are in `gamma/results_gamma_*.jsonl`.

**Preregistration priority is checkable without trusting us.** Commit timestamps can be rewritten;
GitHub's push records cannot. `gamma/PREREGISTRATION_TIMESTAMP.md` gives the push times and two
commands that verify the registration commit is an ancestor of a push made a day before the first
data commit.

**A note on determinism.** Product order is randomized per call from `catalog.seed_for()`, which is
integer arithmetic rather than `hash()`. Python salts string hashing per process, so a `hash()`-based
seed makes the runner and the estimator disagree about which permutation was shown, silently
corrupting the position control. `estimate.py` re-derives each permutation and raises if it does not
match the position the runner recorded.

## Layout

```
sim/        sim2.py (harness), plot2.py, plot_phase.py, run_elastic.py, run_psi.py,
            run_exact.py, run_knee.py, legacy/sim.py
gamma/      catalog.py, run.py, estimate.py, context.py, pricing.py, PREREGISTRATION.md
results/    .jsonl output, one line per run
figures/    generated figures
paper/      draft markdown, the generated PDF, BUILD.md, figures
CHANGELOG.md  what changed between drafts, including claims that were withdrawn
```

## Rebuilding the paper

See [`paper/BUILD.md`](paper/BUILD.md). The PDF is produced by pandoc with xelatex from the markdown
source and the two figures; `CHANGELOG.md` records every draft revision, including the 95%
misallocation result reported in an earlier version and later withdrawn.

An earlier `paper/build_pdf.py` has been removed rather than fixed. It rendered LaTeX math by regex,
and its `\frac` substitution used non-greedy groups that cannot match nested braces — so a nested
fraction was silently rewritten into a different expression. Any tool that converts math by pattern
substitution can do this; the PDF is now produced by a real LaTeX engine.

## Citation

```bibtex
@techreport{vissa_sangaraju_2026_after_attention,
  title  = {After Attention: The Economics of Markets Where the Buyer Is an Agent},
  author = {Vissa, Sudhir and Sangaraju, Venkata M.},
  year   = {2026},
  type   = {SSRN Working Paper},
  number = {7516238},
  doi    = {10.2139/ssrn.7516238},
  url    = {https://doi.org/10.2139/ssrn.7516238}
}
```

## License

Code under the MIT License (`LICENSE`). Results files and figures under CC BY 4.0.
