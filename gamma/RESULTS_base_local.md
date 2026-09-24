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

## Registered verdicts — produced by `interpret.py` against `experiments.json`

- **H1** significant (one-sided-positive, p = 0.0000)
- **H2** significant (one-sided-positive, p = 0.0000)
- **L** NOT significant (two-sided, p = 0.0563)

Primary outcome, verbatim from the registration's `outcome_rules`:

> **H2_positive** — Persuasion net of length replicates on a locally executed
> open-weight model. The effect is not specific to hosted frontier models.

That sentence was written before the data existed. It is the registered text,
not a reading chosen after seeing the numbers.

## Committed robustness check — either side of row 340

The registration's protocol note of 23 September commits to reporting B − C
separately for rows 1–340 (`OLLAMA_NUM_PARALLEL=25`) and rows 341 onward
(`OLLAMA_NUM_PARALLEL=1`), and states that it is descriptive, is not a
hypothesis test, and binds no decision.

| block | B | C | B − C |
|---|---|---|---|
| rows 1–340 | 0.420 (n=100) | 0.150 (n=100) | **+0.270** ± 0.119 |
| rows 341–6000 | 0.405 (n=1900) | 0.047 (n=1900) | **+0.357** ± 0.024 |

Same sign, same order of magnitude, overlapping intervals. The runtime change
did not reverse or erase the effect.

**What this check cannot show, stated plainly.** Rows 1–340 cover choice sets
0, 1 and 2 only, and sets 0 and 1 appear nowhere else in the file. The two
blocks therefore differ in *stimuli* as well as in runtime configuration, so
the contrast between them is confounded with choice set and cannot isolate a
parallelism effect. The arms are also unbalanced before row 340 (A=140, B=100,
C=100). The registration's decision to call this descriptive and bind nothing
to it was the right one, and this is why.

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
