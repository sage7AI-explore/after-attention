# base_local — open-weight replication: registered outcome

Data frozen at commit `4d1eb8b`.
SHA-256 `f59a4d02d829a004573cb858dfa817d61d8d4d8295d2640d10b2a9587607a077`.
Estimated after the freeze, once. Rules committed 2026-09-22, before any data.

## Verification gates

| gate | result |
|---|---|
| rows | 6,000 / 6,000 |
| `config_digest` | 1 distinct value, `4eb23ef187e2c546…` — no mid-sweep weights change |
| transport failures | 36, in the `.api_errors` sidecar, retried, not observations |
| model exclusions | 0 |
| design | 40 sets × 3 arms × 5 framings × 10 reps |

## Fitted contrasts, `gemma4:12b`, n = 6,000

| term | estimate | se | z |
|---|---|---|---|
| **H2 — persuasion net of length (B − C)** | **+2.5705** | 0.3719 | **+6.91** |
| H1 — target × B (persuasion + length) | +3.1909 | 0.1644 | +19.41 |
| L — target × C (length only) | +0.6204 | 0.3250 | +1.91 |
| value | +1.4331 | 0.1287 | +11.13 |
| position | −0.0454 | 0.0354 | −1.28 |

Target choice share: A 0.035 · B 0.406 · C 0.052
Best-value share: A 0.415 · B 0.280 · C 0.400
Best-value shift B − A: **−0.135**, 95% CI [−0.186, −0.089] (2,000 resamples clustered by choice set)

## Registered verdicts — `interpret.py` against `experiments.json`

- **H1** significant (one-sided-positive, p = 0.0000)
- **H2** → **`H2_positive`** (one-sided-positive, p = 2.4e-12)
- **L** NOT significant (two-sided, p = 0.0563)

Primary outcome, verbatim from the registration's `outcome_rules`:

> **H2_positive** — Persuasion net of length replicates on a locally executed
> open-weight model. The effect is not specific to hosted frontier models.

That sentence was written before the data existed.

**A note on how that key was selected.** As shipped, `interpret.py` implemented
the `outcome_rules` lookup for `H3_*` only; for every other hypothesis it
returned a bare "significant / not significant" and left the key selection to
whoever was reading. For `base_local` the primary hypothesis is **H2**, so the
guard did not cover the one decision it exists to remove discretion from, and
the `H2_positive` mapping was made by hand on first analysis. The selection has
since been generalised to any hypothesis with `<HYP>_positive` registered, using
only the rule's own stated criteria — one-sided-positive test, z of the expected
sign, p < alpha. It introduces no new threshold and reproduces the hand mapping
exactly. The change was made after the data were frozen at `4d1eb8b` and is
recorded here rather than left silent.

## Committed robustness check — either side of row 340

The protocol note of 23 September commits to reporting **the H2 contrast
(B − C)** separately for rows 1–340 (`OLLAMA_NUM_PARALLEL=25`) and rows 341
onward (`OLLAMA_NUM_PARALLEL=1`), and states that it is descriptive, is not a
hypothesis test, and binds no decision.

| block | clusters | H1 (target × B) | L (target × C) | **H2 (B − C)** |
|---|---|---|---|---|
| rows 1–340 | 3 | +4.175 | +2.642 | **+1.533** (se 0.381, z +4.03) |
| rows 341–6000 | 38 | +3.152 | +0.477 | **+2.675** (se 0.406, z +6.59) |

H2 is clearly positive in both blocks. The point estimates differ, and the
difference should **not** be read as a CPU/GPU effect, for two reasons.

**The early block has three clusters.** Standard errors clustered by choice set
are unreliable at three clusters, so its z of +4.03 is rough.

**The boundary is confounded with choice set.** Rows 1–340 cover sets 0, 1 and 2
only, and sets 0 and 1 appear nowhere else in the file. Those three sets are
weak ones: their per-set B − C target-share gaps are +0.26, +0.28 and +0.14,
mean +0.23, against an all-set median of +0.31 and mean of +0.35 (range −0.16 to
+0.96). **The lower early estimate is what those sets alone would produce.** The
design cannot separate that from a runtime effect. The arms are also unbalanced
before row 340 (A = 140, B = 100, C = 100).

The same caveat applies to L, which is +2.64 early and +0.48 late — a larger
gap than H2's, on three clusters, and equally unattributable.

**What the check can and cannot say.** It shows no sign that the runtime change
reversed or removed the effect: both blocks are clearly positive. It cannot rule
out a small runtime effect on the size of the estimate. That limit follows from
the run being executed in job order, and it was flagged in the protocol note
before the data existed — which is why the registration bound no decision to it.

## Placement against the three hosted models

| model | B − C | z | target A→B | factor | best-value A→B |
|---|---|---|---|---|---|
| claude-sonnet-5 | +2.665 | 4.9 | 0.016 → 0.135 | 8.4× | 0.563 → 0.507 |
| gemini-3.8-flash | +1.886 | 5.9 | 0.008 → 0.109 | 13.6× | 0.599 → 0.504 |
| gpt-5.6-terra | +2.839 | 10.1 | 0.029 → 0.350 | 12.1× | 0.453 → 0.294 |
| **gemma4:12b (open)** | **+2.571** | **6.9** | 0.035 → 0.406 | 11.6× | 0.415 → 0.280 |

Inside the hosted range on every measure. Two things to report alongside it
rather than after it: this model has the **lowest** baseline best-value share of
the four, so it was the weakest chooser before any persuasion; and it takes
among the largest absolute hits to that share.
