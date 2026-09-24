# Independent timestamp for the preregistration

The preregistration's priority does not rest on git commit metadata, which an
author can rewrite. It rests on GitHub's server-side record of when each push was
received. Those push times are recorded by GitHub, not by us, and are visible in
the repository's Activity page.

## The record

| Event | GitHub push | Received (GitHub) | UTC |
|---|---|---|---|
| Repository created | `b43c831` | Sep 18 2026, 11:25 PM CDT | 19 Sep 04:25 |
| **Preregistration pushed** | `b43c831…9b18cd2` | **Sep 18 2026, 11:55 PM CDT** | **19 Sep 04:55** |
| Paper v0.8 | `9b18cd2…8b5680d` | Sep 19 2026, 12:35 AM CDT | 19 Sep 05:35 |
| **First measurement data pushed** | `8b5680d…da4f225` | **Sep 20 2026, 12:33 AM CDT** | **20 Sep 05:33** |

`gamma/PREREGISTRATION.md` was first committed in `0d1983b`. The first file of
measured choices, `results_gamma_claude-sonnet-5.jsonl`, was first committed in
`3545ce3`.

**The preregistration was on GitHub's servers 24 hours and 38 minutes before any
measurement data was.**

## How to verify it

Two commands, against a clone of this repository:

```
git merge-base --is-ancestor 0d1983b 9b18cd2 && echo "prereg in the 9b18cd2 push"
git merge-base --is-ancestor 3545ce3 9b18cd2 || echo "data NOT in the 9b18cd2 push"
```

The first succeeds and the second fails: the preregistration commit is an
ancestor of the ref pushed at 04:55 UTC on 19 September, and the first data
commit is not — it appears only in the push received a day later. Cross-check the
push times on the repository's Activity page, which is GitHub's record.

## What this does and does not establish

It establishes that the registration document existed, in its committed form, on a
third party's servers before the data did. It does not establish anything about
work done before that push, and it is not a registration with a registry such as
OSF or AsPredicted. Studies run after this one are registered with a registry
before data collection begins.

The context study (urgency x stakes) has the same structure: its registration was
pushed in `da4f225…dd0c462`, received Sep 21 2026 12:26 AM CDT, before its data.
