# Failed runs, kept as evidence

`2026-09-19_claude-sonnet-5_all-failed.jsonl` — first live attempt. Every call failed with
KeyError 'text': the Anthropic parser indexed `content[0]` and assumed it was a text block.
It is not reliably the answer; a non-text block can come first, and with a 16-token output
budget the answer could be starved entirely.

Two defects, not one:
1. The parser. Fixed: it now finds the first block whose type is "text", records the
   stop reason when there is none, and the output budget defaults to 64 tokens.
2. No failure guard. Every safeguard in run.py watched dollars. A run that fails 100% of
   its calls spends nothing, so nothing tripped — it ran 13 minutes and would have run
   about 20 hours recording an empty dataset. Fixed: a calibration window aborts if more
   than 25% of the first 40 calls fail, and 15 consecutive failures abort at any point.

These rows must NOT sit in the runner's output path. The runner treats every recorded
(set, arm, framing, rep) as done, so failed cells would be silently skipped on resume and
become permanent holes in the design.
