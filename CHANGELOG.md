# After Attention — paper changelog

Versioning rule: any fix to a delivered file gets a new version number. Earlier
versions stay in the folder rather than being overwritten. Newest first.

## v0.13 — 25 September 2026

A second independent re-derivation (~150 claims checked) found nine more
discrepancies. All are fixed here, and the first retires a headline claim.

1. **The allocative contrast is not robustly identified, and v0.12b's fix was
   itself wrong.** v0.12b scoped the claim to μ_t, having found the null
   reverses at μ_t = 10 and 20. The τ sweep reverses it the *other* way:

   | | robust | persuadable | contrast |
   |---|---|---|---|
   | exact BR | 0.642 | 0.839 | +19.7 pp |
   | τ = 0.05 | 0.699 | 0.867 | +16.8 pp |
   | τ = 0.15 (published) | 0.845 | 0.859 | +1.5 pp (n.s.) |
   | τ = 0.30 | 0.927 | 0.792 | −13.5 pp |
   | μ_t = 10 | 0.997 | 0.875 | −12.2 pp |
   | μ_t = 20 | 1.000 | 0.909 | −9.1 pp |

   The persuadable series sits in 0.79–0.91 throughout; the robust benchmark
   runs 0.64–1.00. The sign is a reading of the benchmark, and the benchmark is
   set by τ and μ_t, both chosen. §7.3 now declines to sign the effect —
   *not robustly identified, because its sign depends on the benchmark
   equilibrium* — while keeping what the pattern does show: persuasion spending
   imposes its own allocation largely independent of how sharply the agent
   discriminates. Abstract, §1, §12 and Appendix C follow.
2. §7.3's closing line and §12's "concentration more than doubles" contradicted
   the paper's own sensitivity results. Both restated.
3. The μ_t = 20 persuasion peak is 1.99×, not 2.03×. §7.2 now also states that
   every ratio we print is a ratio of the two seed means, not a mean of
   per-seed ratios (which is 1.82), so each is recoverable from the levels
   printed beside it.
4. The μ_t = 20 t of −5.48 counted 8 duplicate rows. On 440 cells it is −5.19.
5. **The knee is a steepening, not a jump.** The Δα = 0.02 sweep (560 runs)
   shows the largest single step is 19% of the fall and the slope rises three-
   to fourfold over a band ~0.1 wide. §1's "discontinuous" and §12's "narrow
   band" are gone; "tipping point" now means what Corollary 1 licenses. This is
   what Corollary 1 always predicted — a per-seller discontinuity summed over
   twelve sellers is a knee.
6. §8.6: CR2 p range is 3e-5 down to 1e-11; bootstrap 95th percentiles 1.68 to
   1.74; CR2 inflation 1.6–1.9% on the H2 contrast. Added the script author's
   two caveats (the score bootstrap is one-step and its tail is lighter than an
   exact re-solve on one model; CR2 is a linearisation). The 138-draw
   calibration is superseded by 2,000 draws across three null scenarios: CR0
   rejects 5.9–6.0%, CR2 and the bootstrap 4.8–5.2%, sd(z) 1.03–1.07 — so
   sd(z) = 1.11 was a high draw. The §8.5 adjustment stays at 1.11, now the
   conservative choice.
7. Appendix C said "three results survive" and listed four.
8. §7.7's consumer-net-value difference is 0.867, not 0.86.
9. `sim/run_exact.py` wrote to the working directory while Appendix B and the
   README said `results/`. Fixed. `sim/run_knee.py` added — the Δα sweep had no
   committed driver — and verified to reproduce the shipped file exactly.

**The μ_t calibration, and what it settled.** §11 calibrates μ_t against our
own §8 `b_value` (1.43–2.23) rather than choosing it. An initial draft of this
entry reported three ranges (3.3–5.2, 5.9–9.2, 1.0–1.6) and called the exercise
circular. Both were wrong and are superseded by `c0e1643`. Those ranges came
from an idealized back-of-envelope — twelve uniform qualities at one common
margin — not from simulated equilibria, and should not be cited. And the
circularity is solvable: μ_t × SD(θ_q q − λp) is monotone in μ_t in every
regime, so scanning finds a unique crossing.

The scan (540 runs: six regimes × nine μ_t values × 10 seeds, on an
instrumented copy that reproduces every existing output field exactly) gives an
implied **μ_t of about 0.5 to 5**, 47 of 48 endpoints below 5. The spread is
driven by how sellers priced out of contention are treated — at the grid's
ceiling markup they inflate the all-seller dispersion two- to fivefold — so
four dispersion definitions are reported: 0.5–1.1 using all twelve sellers,
0.7–5 using contender-based measures, inside which the headline μ_t = 3 falls.

Three consequences, all in the paper: Assumption 2 is the μ_t → ∞ limit and
nothing measured comes near it, so §5 now marks it as limiting; Appendix C's
μ_t = 10 and 20 sit above every interval the calibration produces and are
reframed as robustness points rather than the more realistic agent; and the
sign of the allocative contrast turns over between μ_t = 2 and 3, **inside**
the implied range — so §7.3's indeterminacy survives restricting μ_t to what
our own measurements support, which is the strongest form the claim can take.
What the calibration does not fix is the mapping: `b_value` records tracking of
our experimental value index over a catalog we wrote, not the simulation's.

**Third pass, after the v0.13 entry above was written.** A further re-derivation
tightened five claims that overstated what the runs show:

- **The abstract's 79–91% and 64–100% ranges** are the six configurations
  tabulated in §7.3, not "every configuration we run" — the exact-best-response
  runs at n = 5 fall outside them. Scoped accordingly.
- **The seller-by-seller threshold mechanism** was asserted as what the
  simulation demonstrates. It is not: it is a theoretical account the aggregate
  shape is *consistent with*. The abstract, §1, Appendix C and §12 now say so,
  and record that an informal two-seed look did not show a clean
  one-jump-per-seller pattern. This corrects prose written in `54b7be3` and
  `bdf3a14` that claimed the mechanism as shown.
- **§7.2's mean of per-seed ratios is 1.70** at α = 0.3. The 1.82 figure comes
  from letting each seed contribute its own peak, which also picks up the noise
  in where that peak falls.
- **§8.6's CR2 inflation is 1.6% to 1.8%** on the H2 contrast (all four models
  between 1.016 and 1.018), not the 1.9% previously stated.
- **Appendix C's steepening is relative to the 0.15–0.20 slope**, stated
  explicitly, and the persuadable steps run −0.002 to +0.010.
- `sim/run_exact.py`'s docstring lists all three sweeps, `fine_ladder` included.

**Published state.** v0.13 is the version posted to SSRN 7516238 on 25 September
2026 (same DOI, revision rather than new posting). The posted PDF is built from
the paper source as of commit `c0e1643`; the source has not changed since. v0.11
remains in the tree as the version originally posted.

## v0.12b — 24 September 2026

Twelve corrections, of which two change headline claims. Nothing in Tables 1–4
moved; what moved is what the paper says about those numbers.

**From an independent re-derivation** (a separate session recomputed ~300
reported numbers from the committed data):

1. §7.6 claimed conflicted agents lower both top-three share and consumer net
   value "at every ψ we tried." False — top-three share is *higher* at ψ = 0.25
   and 0.5. Rewritten; §11 scoped to ψ ≥ 1.
2. §8.7 claimed gemma's magnitudes sit inside the hosted range "on every
   measure." False on three of five, and it contradicted the note under Table 4.
3. Appendix B claimed one command regenerates every number in §7. The elastic
   volumes come from `run_elastic.py`; the ψ sweep had no committed driver at
   all. `sim/run_psi.py` added.
4. Table 4 factors were computed from rounded shares: gemini 13.6× → 14.5×,
   gemma 11.6× → 11.4×. Abstract's "8 to 14" → "8.4 to 14.5".
5. §8.3 placebo 95% upper bounds: +0.96/+1.52/+1.01 → +0.99/+1.54/+1.03.
6. §8.6: fifteen of the sixteen gemini exclusions are truncations, not sixteen.
7. The 0 → 0.2 margin move is 1.46 pp, not 1.4.
8. Appendix C cited a grid discussion that is not in §7.3.

**Found while verifying those:**

9.  Appendix C's convergence check rested on a `settled` flag that is a
    threshold on average revisions, not a fixed-point test — and Appendix B
    claimed an early stop the code does not have. Rerun as genuine exact best
    response (τ → 0, ι = 0) on both grids: 9 of 110 fixed points on the coarse
    grid, **two of them interior**; 5 of 110 on the fine grid, **none
    interior**. Better than the claim it replaces: Corollary 2's grid-fineness
    condition visible in the numerics.
10. Exact best response at α = 1 leaves three of four headline contrasts
    intact but moves the robust-agent top-three share from 0.845 to 0.642, so
    the abstract's "about 85% either way" was a property of the smoothed
    dynamic.
11. **τ = 0.15 was never tested.** Swept at 0.05 and 0.30 (440 runs each). The
    four headline results hold at every τ. The concentration *ratio* and the
    flatness before the knee do not, and are now flagged where quoted.
12. **μ_t = 3 was never tested, and this is the one that changes a headline
    result.** Swept at 10 and 20 (440 runs each). Three contrasts strengthen;
    the concentration ratio collapses to 1.11×; and §7.3's allocative null
    *reverses* — persuadability costs −12.2 pp (t = −5.86) and −9.1 pp
    (t = −5.48) of top-three share against +1.5 pp (t = +0.49) at μ_t = 3. The
    null was measured against a benchmark too noisy to see the effect. Abstract,
    §1, §7.3, §12 and Appendix C now carry the conditional statement.

**Added:** §8.6 now reports CR2 and wild cluster bootstrap inference for the
40-cluster design (`gamma/robust_se.py`). All four H2 results stay significant
under both; CR0 rejects ~6% under the null against ~5% for CR2 and the
bootstrap. References added for Kline & Santos (2012) and Pustejovsky & Tipton
(2018), both verified against Crossref.

`sim2.py` gains `--set KEY=VALUE`, and records `zero_change_sweeps` and
`final_sweep_changes` (additive — a rerun reproduces pre-change output to 1e-9).
Appendix B and the README now list every command that produces a number in §7,
which they did not before.

## v0.12 — 24 September 2026

The open-weight replication registered in v0.11 as incomplete has completed, and
§8.7 is rewritten from a design statement to a result.

**The replication succeeds.** `gemma4:12b`, executed locally at a recorded
configuration digest with reasoning disabled, 6,000 calls: persuasion net of
length is +2.57 (se 0.37, z 6.91). The registered verdict is `H2_positive`,
whose text was committed on 22 September: *persuasion net of length replicates on
a locally executed open-weight model; the effect is not specific to hosted
frontier models.* Target share moves 3.5% to 40.6% and the best-value share falls
0.415 to 0.280 (95% CI [-0.186, -0.089]). New Table 4 places it against the three
hosted models; it sits inside their range on every measure.

What that closes: before this experiment a reader could hold that §8.3 measured
an artifact of three vendors' scaffolding, retrieval or system prompts. That
reading is no longer available.

**Totals.** 37,200 measured decisions becomes 43,200 across three preregistered
experiments (18,000 + 19,200 + 6,000). Updated in the abstract, front matter, §1
and §8.

**Reported honestly alongside it.** `gemma4:12b` has the lowest baseline
best-value share of the four models and among the largest falls in it, and one
open model cannot separate those. The registration was amended before any data to
disable the model's default reasoning mode, for tractability at 1,400 tokens per
call; that is a weaker reconstructor of the comparison than the default
configuration, so the replication is of that configuration. Both are new
limitation 11 in §11.

**The runtime change mid-run.** The protocol note committed, before the data
existed, to reporting the B - C contrast either side of the 340-row boundary where
the local server was reconfigured from 25 slots to 1. It is +1.53 (se 0.38) and
+2.67 (se 0.41) — positive in both. The difference is not attributed to hardware:
the early block spans three choice sets, and those three sets are weak ones
(per-set gaps +0.26, +0.28, +0.14 against an all-set median of +0.31), so the
lower early estimate is what they alone would produce. The check can show the
effect was not reversed; it cannot rule out a small effect on the estimate's size.

**Corrections carried in this revision.**

- §8.3's bootstrap intervals were computed in a shell when added to v0.11. They
  are now produced by `estimate.py` with the seed and draw count as module
  constants. That moved two of them in the third decimal: gemini-3.8-flash
  [-0.154, -0.044] to [-0.153, -0.046], gpt-5.6-terra [-0.222, -0.100] to
  [-0.225, -0.103].
- §11.9's description of the urgency null now matches the corrected §8.5: the
  +1.0 exclusion holds on one of two models, not both, and there is no registered
  equivalence bound.
- §8.6 now states the limit of push-time evidence — it establishes when a file
  was published, not when the calls were made — and records that §8.7 additionally
  froze its data in a commit before the estimator was run.

**Still open, and stated as such:** no tau sensitivity analysis, model versions
unpinned, and the 40-cluster estimator is not yet reported with CR2 or a wild
cluster bootstrap. See `V0.12_PROTOCOL.md`.

## v0.11 — 24 Sep 2026

Built through a real LaTeX toolchain (pandoc + xelatex) for the first time. The
previous PDF script rendered mathematics by regular expression and could not
handle nested fractions: Proposition 3's condition (ii) printed as multiplying by
T where the source correctly divides by it. Every nested fraction in the v0.10 PDF
was affected. The markdown source was correct throughout; only the PDF was wrong.

Corrections to claims and numbers, most of them raised by Venkat Sangaraju's
review of v0.10 and verified against the data before being applied:

- Contribution list unified. The abstract said "three results" and listed four;
  the introduction said "four claims" and listed five things in a different order,
  omitting the measurement entirely. One list of four is now used in both, with
  the protocol reading (§3) separated out as a reading rather than a result.
- "What we do not claim" rewritten. It still described v0.2: it disclaimed
  measuring persuadability two sentences before citing the measurement, disclaimed
  modelling platform-owned agents that §7.6 models, and reported results from a
  110-run exact-best-response configuration superseded in §6.
- Selection-lift range corrected from "8 to 12" to "8 to 14" (the three lifts are
  8.4x, 13.6x and 12.1x).
- §7.5 margin ratio corrected from "2.2 and 32 times" to 2.5-3.9x, with the
  lambda = 1.4 configuration excluded and the reason stated: its robust margin is
  0.007, so the ratio reflects the denominator rather than the effect.
- Consumer net value: percentage changes removed from the abstract, §7.3 and §7.7.
  Appendix C states that the level of that series is an artifact of the value
  scale, which makes a ratio of two of its values uninterpretable. Differences and
  the sign crossing are reported instead.
- §8.4: sigma_V collapses at a markup of 0.20, which is a gross margin on revenue
  of about 16.7%, not 0.20. Added the consequence Venkat identified: where sigma_V
  is small the sellers are near-tied, so absolute concentration at full adoption
  deserves more caution than the differences between regimes.
- §7.4 re-run and re-reported on the 16-point markup grid rather than the 12-point
  grid, with the configuration now stated. The headline finding survives
  refinement (the gamma 0 -> 0.25 concentration jump is 1.62x against 1.68x), but
  margin is not monotone in gamma on the finer grid and is no longer described as
  rising steadily.
- Appendix B reproduction block replaced. It instructed readers to run `sim.py 5`
  and read `results.json`, neither of which produces any number in this paper.
- Appendix C: removed a duplicated "Grid effects" paragraph and updated the
  inelastic-demand paragraph, which still called elastic demand the most valuable
  extension after §7.6 had done it.
- References: Wadi, A. and Ma, L. corrected to Wadi, D. and Ma, Y.; the orphaned
  Madugula et al. entry, cited nowhere in the text, removed. All 34 references
  were checked, including every 2026 arXiv identifier; no other error found.
- "Three shopping agents" softened to "three frontier LLMs acting as buyers"
  throughout, matching what §8.6 already said.

New material:

- §8.5: the context study. A second preregistered experiment, 19,200 decisions
  across two models, crossing urgency with stakes. The persuasion effect
  replicates; urgency produces no detectable change, reported under the committed
  rule with its power stated. The super-additivity in the urgent, high-stakes cell
  is reported as exploratory and explicitly not a finding.
- §8.6: estimator calibration against 138 null datasets (6.5% false-positive rate
  at a nominal 5%), and a correction — the 16 excluded gemini replies were
  truncations at our output ceiling, not the model narrating.
- §8.6: preregistration integrity stated as verifiable evidence. GitHub's
  server-side push records place the registration on its servers 24h38m before any
  measurement data, which does not depend on commit metadata we could have
  rewritten. Two git commands reproduce the ordering.
- §8.7: the open-weight replication, preregistered and running but incomplete at
  the time of writing. Nothing is reported from partial data.

## v0.10 — 21 Sep 2026

Two additions, both qualifying our own argument rather than strengthening it, prompted by
Sid asking whether the mechanism promotes fairness and whether it accounts for the context
in which an agent understands its user.

**Section 9: verification has a cost structure, and it concentrates.** The paper recommends
verifiable claims as the value-routing substitute for advertising while treating attestation
as costless. It is not. A test result or conformance assessment costs about the same for a
seller with ten products as for one with ten thousand, so a regime admitting only fully
verified claims excludes small and new sellers for reasons unrelated to the truth of their
claims — invisibly, since the buyer simply sees fewer offers. That is a second concentrating
channel on top of the one measured in section 7, and it means the remedy can be
self-defeating depending on how the burden is distributed.

**Section 8.5: the measurement is context-free.** All five framings ask the agent to choose
well; none conveys urgency, stakes, or which attribute the principal relies upon. There is a
specific reason to expect an interaction rather than an additive effect: an agent under time
pressure has more reason to lean on what a listing asserts. If persuadability rises with
urgency, agents are least robust exactly where a bad choice is hardest to undo — a worse
finding than the one reported. The design extends to test it and we have not run it.

Limitations 9 and 10 added correspondingly. 24 pages; verified clean.

## v0.9 — 19 Sep 2026

**Gamma is measured. New section 8.** 18,000 preregistered purchase decisions across three
shopping agents. One sentence of unverifiable promotional text raises a mid-ranked product's
selection rate by 8x (claude-sonnet-5, 1.6% to 13.5%), 14x (gemini-3.8-flash, 0.8% to 10.9%)
and 12x (gpt-5.6-terra, 2.9% to 35.0%). The length-matched placebo does nothing on any model
(z = -0.04, +1.18, +1.25), which is what makes this persuasion rather than text volume. The
share going to the genuinely best-value product falls on every model.

The effect in normalization-free units: one persuasive sentence is worth 0.85 to 1.72 standard
deviations of true quality-adjusted value.

**Section 8.4 reports a fragility in our own parameterization rather than hiding it.** Mapping
the measurement to the model's gamma needs a cost per rewrite and a value dispersion, neither
observed. Worse, because theta_q = 12 and lambda*c = 10(1+m) nearly cancel in q, sigma_V
collapses to zero at a gross margin of exactly 0.20. Implied gamma spans 0.07 to 2.14 depending
on where in that range one stands, so no single number is quoted. What survives is the claim
the paper needs: measured persuadability is nowhere near the gamma = 0 pole.

**Consequent changes.** The abstract gains the measurement as a fourth headline result.
Limitation 1, which said gamma was stylized and unmeasured, is replaced by what the measurement
does and does not pin down. The conclusion's conditional "if agents can be moved by how a
listing is written" becomes a statement of fact. Sections 8-11 renumbered to 9-12; subsection
count checked (11 -> 16, the five new ones) and every cross-reference re-resolved, after the
v0.7 incident where renumbering silently dropped a subsection.

24 pages. Verified: 7 dollar signs, all currency; no literal math; no stray LaTeX.

## v0.8 — 19 Sep 2026

**Sangaraju and Vissa is published, and the citation is now correct.** v0.7 recited it as a
preprint with a note that the IEEE Access record could not be located. It could: the paper was
received 12 August 2026, accepted 30 August 2026, published 3 September 2026, and appears as
*IEEE Access*, vol. 14, pp. 139683-139693, DOI 10.1109/ACCESS.2026.3730363. The reference and the
in-text citation in section 9 both drop the "preprint" qualifier. What misled the v0.7 check was the
first author's own repository, which still carries the June 2026 preprint BibTeX under a shorter
title and no DOI - stale rather than wrong. Author name follows the published byline
("Sangaraju, V."), which omits the middle initial the After Attention byline uses.

**Math rendering was broken, and the v0.7 PDF shipped with the defect.** Inline spans such as
`$A + G$`, `$N = 12$`, `$M = 3{,}000$`, `$(0,1)$`, `$+0.83$` and `$(p-c)(H/2 + T/2)$` printed as
literal source text, complete with dollar signs and braces, in sections 5, 6, 7, Table 2, Table A1
and the Proposition 1 proof. The v0.7 verification pass checked numbers and citations but only
counted dollar signs rather than inspecting them, so it reported clean.

Cause: the builder guessed whether a `$...$` span was math or currency from its contents, and the
guess was tuned to protect currency runs like "$900 billion to $1 trillion". Every rule narrow
enough to do that also rejected ordinary math. Fixed by removing the ambiguity rather than
retuning the guess: the seven genuine currency amounts in the source are now escaped (`\$900
billion`), so every unescaped dollar is a math delimiter and no heuristic is needed.

Verified on the rebuilt PDF: 7 dollar signs, all currency; 0 literal math spans; 0 stray LaTeX
commands; 21 pages.

## v0.7 — 19 Sep 2026
Venkat's item 10: full citation-by-citation verification and an artifact read-through.

**All 30 references checked against primary sources.** 24 verified clean. Five corrected:
- **Turner-Smith et al. (2607.27686): three author initials were wrong.** Now J. L. Turner-Smith,
  Z. Huang, Y. Fu, Y. Zhang, T. Wang.
- **Sangaraju & Vissa could not be confirmed as published.** The IEEE Access record for
  DOI 10.1109/ACCESS.2026.3730363 is not on Xplore or in any index; the only public trace is a
  GitHub issue, and the first author's own repo describes the work as a June 2026 preprint with no
  DOI, volume or pages, under a shorter title. Now cited as a preprint with a bracketed note to
  confirm status before submission. **Venkat needs to resolve this** — he is the author.
- Morgan Stanley: "Agentic Commerce Impact Could Reach $385 Billion by 2030" is the page's SEO
  title, not the headline, which is "Here Come the Shopping Bots". Corrected, with the $190–385bn
  range noted.
- McKinsey: full title and named authors restored.
- Vissa SSRN 6600538: full title restored ("...: A Constitutional AI Framework for Fully Staffless
  Physical Retail"), posted 4 May 2026.

**Every number re-derived from the results files.** All 44 Table 1 values match the data; the six
inline ratios (1.68x, 1.21x, 2.5x margin, 2.4x HHI, 80% surplus, 1.4pp) all reproduce within
rounding. The check is scripted, not eyeballed.

**Artifact read-through.** No stock LLM phrasing found (one incidental "robust and"). Hedge density
0.9 per 1,000 words. Em dashes at 8.0 per 1,000 words, which is high but consistent with the
register; flagged rather than machine-stripped.

- 21 pages.

## v0.6 — 19 Sep 2026
Completes the remaining items on Venkat's simulation list. 21 pages.

- **§7.4 The persuadability–adoption plane (new, Figure 2).** Replaces the two-point γ comparison with
  a sweep over γ ∈ {0, 0.25, 0.5, 0.75, 1, 1.5, 2, 3} × 11 α values, 352 runs. Findings: margin at full
  adoption is monotone in γ (5% → 18%); concentration responds to *very* small persuadability (HHI 3,617
  at γ=0 vs 6,089 at γ=0.25, then flattening); consumer net value per unit crosses zero between γ=0.75
  and γ=1.0.
- **§7.5 Structural sensitivity (new, Table 2).** One-at-a-time perturbation of θ_q, λ, β, μ_t, 192 runs.
  The γ effect survives everywhere: persuadable agents leave sellers 2.2x–32x the margin robust agents
  leave, concentration at full adoption lands in 7,400–9,200. Includes an internal check: the β rows are
  identical at α=1, as they must be with no humans left.
- **§7.6 Three variants (new, Table 3).** Elastic category demand, mixed agent quality, conflicted
  platform-owned agents. 330 runs plus a 110-run recalibrated elastic sweep.
  - *Elastic*: under robust agents the category contracts mid-transition (1,492 → 951 units) and
    recovers; under persuadable agents volume never contracts. Persuasion buys back the volume that
    price competition costs the category.
  - *Mixed quality*: half the twins robust cuts concentration at full adoption from 8,567 to 4,437 and
    restores consumer value to break-even. Robust agents are a positive externality for buyers whose
    agents are not robust.
  - *Conflicted*: replacing the robust half with commission-taking platform agents cuts top-3 value
    share from 0.70 to 0.60 and consumer value from +0.03 to −0.67 — the worst in the paper. **This is
    the misallocation §7.3 declined to attribute to persuadability**; it belongs to divided loyalty.
- **§9 Implications:** new paragraph on platform-owned agents — the rails make commission-taking agents
  trivial to deploy and constrain them not at all.
- **§10 Limitations:** items 4, 5 and 6 (elastic demand, homogeneous agents, no platform-owned agents)
  retired — they are now results. Replaced with the narrower limitations that remain.
- **Appendix B** documents the variants and all four sweeps; **Appendix C** adds the elastic calibration
  judgment (scale 0.4 kills the category, 0.15 does not — the choice is ours, not estimated) and a note
  that variant magnitudes are not comparable to Table 1's finer configuration.
- **Public repo prepared** (not yet pushed): code, pinned requirements, all six results files, figure
  scripts, README with per-table reproduction commands and runtimes, MIT licence, and the legacy harness
  kept so the withdrawn coarse-grid artifact stays reproducible.
- **Build script:** replaced regex `$...$` pairing with a scanner. A currency run consumed both its
  dollars, orphaning following math — "set by $\gamma$ and $\alpha$" rendered as "γand". Verified
  against four edge cases.

## v0.5 — 19 Sep 2026
Venkat's review pass, plus a rebuilt simulation harness. **One headline result was withdrawn.**

**Correction (material).** The v0.2–v0.4 claim that a fully manipulable agent market routes 95% of
sales away from the best-value sellers (top-3 value share 0.049) is a coarse-grid artifact. On a
16-point markup grid the figure is 0.859, and the change is not caused by the new dynamic — under
exact best response on the fine grid it is 0.854. Abstract, §7, §8, §9 and the conclusion rewritten.
The claim that replaces it: persuadable agents do not misallocate demand (good sellers still win
~85% of sales either way); they preserve seller rent (margin 9.9% vs 4.0%), cut consumer net value
per unit by ~80% (+0.23 vs +1.09), and concentrate the market 2.4x (HHI 7,424 vs 3,102).

**New harness (`sim2.py`).** Smoothed/quantal best response with inertia replaces exact best
response; 20 seeds; 16-point markup grid. 440 runs. Results in `results_headline.jsonl`.

**New theory — Proposition 3 and Corollary 2.** The mixed population admits no pure-strategy
equilibrium in the interior; the discrete-grid counterpart of Varian (1980), with the non-existence
interval expanding to all of (0,1) as the grid is refined. Proof in Appendix A. The old runs confirm
it exactly: all 12 convergent runs sit at α = 0 or α = 1, none of the 90 interior runs converged.
This converts the "12/110 converged" awkwardness into a prediction.

**Citations.** Varian (1980, with errata), Salop & Stiglitz (1977), Burdett & Judd (1983) added to §2
as the informed/uninformed-buyer antecedent, with verified volumes and pages; Dasgupta & Maskin
(1986, I and II) added for mixed-strategy existence in discontinuous games. Madugula et al. (DVM-HALL)
worked into the §5.4 measurement discussion — no longer an orphan reference. Sangaraju & Vissa (2026),
lineage-aware memory governance, added to §8's verifiable-claims instrument; title and DOI verified,
volume and pages still need filling from IEEE Xplore.

**Figure 1 regenerated** from the new runs: 8 panels (adds total persuasion spend and price dispersion),
20 seeds, smoothed dynamic.

**Build script:** replaced the currency-vs-math heuristic. Math spans beginning with a digit
(e.g. `$1 - \iota$`) were being swallowed by the currency guard, leaving raw LaTeX in the PDF.
Now a span is math if it carries a backslash, subscript or superscript, or is a bare short symbol.

- 18 pages, up from 15.

## v0.4 — 18 Sep 2026
Structural alignment pass, after comparing section structure against recent arXiv comparables
(Lucier et al. 2603.25893; Dong/Luo/Xu 2608.08395; Turner-Smith et al. 2607.27686;
Allouah et al. 2508.02630; Salvi et al. 2604.04263) and three econ.TH 2026 theory-plus-simulation
papers (2608.04276, 2608.01406, 2608.03788).
- **Propositions formalized.** §5 now states Assumptions 1–3, Proposition 1 (threshold α*), Corollary 1
  (discontinuity), and Proposition 2 (the γ* condition for funding agent-directed spend), with
  comparative statics. Proposition 2 explicitly does NOT claim the total-persuasion-spend result,
  which is numerical and stays in §7.2.
- **New Appendix A: Proofs.** Full proofs of Proposition 1, Corollary 1 and Proposition 2, including
  the logit derivative. Signposted from the introduction and from §5, per convention — every econ.TH
  comparator with formal results puts proofs in an appendix.
- **Appendix split.** B: simulation implementation and parameters (best-response dynamic, common
  random numbers, reporting, reproduction). C: robustness and known fragilities (convergence, seed
  dispersion, outcome scale, inelastic category demand, grid effects).
- **Removed the old Appendix B** (note on defects corrected from v0.1) — that is changelog material,
  not paper material.
- **Contributions converted to prose** under a "Contribution" head; bulleted contribution lists read as
  CS-venue and are absent from every econ.TH-styled comparator.
- **§3 retitled** to "What the deployed rails standardize — and what they leave open", so it reads as
  analysis rather than background. Kept as a numbered section deliberately: a standalone institutional
  section is non-standard, but this one carries a contribution.
- Limitation 8 rewritten to name the partial-equilibrium restriction (Assumption 3) precisely.
- Build script: added Δ, ≡, ∎, exp, Σ and bracket symbols to the math converter after the first build
  dropped Δ and ≡ from the proofs.
- 15 pages, up from 14.

## v0.3 — 18 Sep 2026
- **New §3, "The rails as built"** (~1.5 pp). Reads the published agentic-commerce specifications —
  Mastercard Agent Pay (Apr 2025), AP2 (v0.1 Sep 2025, v0.2 current), ACP/Instant Checkout (Sep 2025),
  Visa Trusted Agent Protocol (Oct 2025), UCP (v2026-01-11, v2026-08-25 current) — against what an
  evidence-consuming agent would need. Findings: signing applies to the transaction envelope and never
  to a product fact; descriptions are one undifferentiated layer; trust is bilateral and payment-scoped
  with no issuer-to-attribute-type registry; UCP's catalog disclaims itself as "not transactional
  commitments"; agent reasoning is out of scope in both protocols. Argument: the rails lower the friction
  that governs adoption (α) and do nothing to the parameter that governs efficiency (γ).
- Sections 3–10 renumbered to 4–11; all cross-references updated.
- Contributions list now four items; abstract extended with the rails finding.
- Five new references (AP2, ACP, Mastercard, UCP, Visa) with version dates.
- Tie-ins added in §8 (verifiable claims is the layer the rails leave unbuilt), §9 (rail consolidation;
  mandating protocol adoption raises α without touching γ).
- 14 pages, up from 12.

## v0.2.1 — 18 Sep 2026
- Fixed: numbered and bulleted lists printed the literal text `&nbsp;` in the PDF. Cause was in the
  build script (`build_pdf.py`): it inserted the HTML entity before the step that escapes `&`,
  so ReportLab rendered the escaped entity instead of a non-breaking space. Now inserts U+00A0
  directly. Scanned the whole document for other stray entities — none.
- No content changes. Text, tables, figure and references identical to v0.2.

## v0.2 — 17 Sep 2026
- First full manuscript, written from `AFTER_ATTENTION_buildout_v0.1.md` and the 110-run
  `results.json`. 12 pages: abstract, introduction, related work, model, analytical results (P1–P3),
  simulation, results, what replaces advertising, implications, limitations, conclusion,
  references, two appendices.
- Corrected two defects carried from the build-out (recorded in Appendix B):
  - WPP Media's 57.6% top-three share is measured on ad revenue **outside China** and cannot be
    applied to the $1.3T global figure; the two are not multiplicable.
  - McKinsey's US projection restated in their own terms: $900B–$1T of "orchestrated revenue" in
    US B2C retail, $3–5T globally.
- Added 2026 competing work to §2 after a verification pass: Lucier et al. (2603.25893),
  Turner-Smith et al. (2607.27686), Salvi et al. (2604.04263), Wadi & Ma (2608.22697),
  Affonso (2601.03061).
- Reported the convergence limitation explicitly: 12 of 110 runs reach a pure-strategy fixed point,
  so results are time-averages of a cycling best-response process.

## v0.1 — 16 Sep 2026
- Build-out document: thesis, three propositions, model sketch, preliminary results, outline,
  next steps, risks. Not a manuscript.
