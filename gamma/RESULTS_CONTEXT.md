# Context study (urgency x stakes) — confirmatory results

Estimator run once, on data frozen at commit efa6f6b, 21 September 2026.
Raw output: `results/context_estimates.txt`. Verdicts selected mechanically by
`interpret.py` from the rules committed before any data: `results/context_verdicts.txt`.

| model | H2' persuasion net of length | H3 change under urgency (primary) | H4 change under stakes |
|---|---|---|---|
| claude-sonnet-5 | +2.37 (se 0.84), z 2.81, p .003 | +0.27 (se 0.41), z 0.67, p .25 — **NULL** | -0.27 (se 0.40), z -0.67, p .50 — n.s. |
| gpt-5.6-terra   | +2.30 (se 0.69), z 3.33, p .0004 | +0.09 (se 0.26), z 0.36, p .36 — **NULL** | +1.16 (se 0.63), z 1.84, p .066 — n.s. |

**H2' replicates** in both models: persuasion net of length is positive and significant in
the unhurried, routine cell, at a size close to the base study.

**H3 is null** in both models, and is reported under the committed rule: no detectable change
in persuadability under urgency. This rules out an urgency effect of +1.0 or larger with 92%
power. It does not rule out a moderate effect (54% power at +0.5), and does not show that
urgency does not matter.

**H4 is not significant** in either model.

Registered secondary, value x urgent (two-sided, no multiplicity correction):
claude -0.056 (se 0.056), p .32; gpt -0.062 (se 0.032), p .048. One of two tests is
nominally significant, the effect is about 4% of the value weight, and no correction for
two models was registered. It is reported, not relied on.

## Exploratory — not a test of any registered hypothesis

The (1,1) cell was registered as a descriptive check on additivity. Target share under
arm B there is higher than either main effect alone suggests (claude 0.048 -> 0.188,
gpt 0.239 -> 0.470), while arms A and C move far less. This is a departure from the
additive model the confirmatory estimates assume. It was not predicted, no test of it was
registered, and it is reported as a hypothesis for a separately preregistered study, not as
a finding.

Data: 9,600 calls per model, all 480 cells x 20 reps present, 0 model exclusions, 0 calls at
the output ceiling. 50 API failures (no response) were logged and re-run per the protocol
note of 21 September. Spend: claude $52.66, gpt $34.91.
