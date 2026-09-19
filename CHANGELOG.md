# After Attention — paper changelog

Versioning rule: any fix to a delivered file gets a new version number. Earlier versions stay in
the folder rather than being overwritten.

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
