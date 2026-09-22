"""
Preflight: check a run command against experiments.json BEFORE any call is made.

Exists because a run was once launched at 10 repetitions against a registration of 20.
The preregistration and the command were two sources of truth and nothing compared them.
This compares them, and refuses to proceed on any mismatch.

Also reports CUMULATIVE spend across sessions. run.py's cap is per session, so a resumed
run could otherwise spend a second full cap without anyone noticing.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


class PreflightError(SystemExit):
    pass


def check(model, design, reps, sets, cap, max_tokens, dry_run=False):
    reg = json.load(open(os.path.join(HERE, "experiments.json")))
    if design not in reg:
        raise PreflightError(f"PREFLIGHT: design '{design}' is not registered in experiments.json")
    e = reg[design]
    problems = []
    if e.get("status") == "complete" and not dry_run:
        problems.append(f"design '{design}' is marked complete; a live run would add data to a "
                        f"closed study")
    if model not in e["models"]:
        problems.append(f"model {model} is not registered for '{design}' "
                        f"(registered: {', '.join(e['models'])})")
    if reps != e["reps"]:
        problems.append(f"--reps {reps} but '{design}' is registered at {e['reps']}")
    if sets != e["sets"]:
        problems.append(f"--sets {sets} but '{design}' is registered at {e['sets']}")
    if max_tokens != e["max_tokens"]:
        problems.append(f"--max-tokens {max_tokens} but '{design}' is registered at {e['max_tokens']}")
    want_cap = e["caps"].get(model)
    if want_cap is not None and cap < want_cap:
        problems.append(f"--cap {cap} is below the registered {want_cap}; the 90% hard stop "
                        f"would halt before the design completes")
    calls = sets * e["arms"] * e["levels"] * reps
    if calls != e["calls_per_model"]:
        problems.append(f"design computes to {calls:,} calls but {e['calls_per_model']:,} are registered")

    if problems and not dry_run:
        print("\nPREFLIGHT REFUSED — command does not match the registered design:")
        for p in problems:
            print(f"  x {p}")
        print(f"\nRegistered '{design}': {e['sets']} sets x {e['arms']} arms x {e['levels']} "
              f"{e['level_name']} x {e['reps']} reps = {e['calls_per_model']:,} calls per model.")
        raise PreflightError(4)
    if problems and dry_run:
        print("preflight    (dry run — mismatches noted but not enforced)")
    else:
        print(f"preflight    OK — matches registered '{design}' ({e['calls_per_model']:,} calls, "
              f"{e['reps']} reps)")
    return e


def cumulative_spend(out_path):
    if not os.path.exists(out_path):
        return 0.0, 0
    n, usd = 0, 0.0
    for line in open(out_path):
        r = json.loads(line); n += 1; usd += r.get("usd", 0.0)
    return usd, n


if __name__ == "__main__":
    # self-test: the exact commands that were, and should have been, run
    cases = [
        ("the command actually issued (missing --reps 20)", "claude-sonnet-5", "context", 10, 40, 60, 8192, True),
        ("context study re-run after it was closed",        "claude-sonnet-5", "context", 20, 40, 60, 8192, True),
        ("the correct local replication command",           "gemma4:12b",      "base_local", 10, 40, 1, 2048, False),
        ("cap too low for the design",                      "claude-sonnet-5", "context", 20, 40, 50, 8192, True),
        ("unregistered model",                              "gemini-3.8-flash","context", 20, 40, 50, 8192, True),
        ("live run against the closed base study",          "claude-sonnet-5", "base",    10, 40, 50, 2048, True),
    ]
    bad = 0
    for label, m, d, r, s, c, mt, expect_refuse in cases:
        try:
            check(m, d, r, s, c, mt)
            refused = False
        except PreflightError:
            refused = True
        ok = refused == expect_refuse
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {'refused ' if refused else 'allowed '} {label}\n")
    print("preflight self-test:", "PASS" if not bad else f"{bad} FAILURES")
    sys.exit(1 if bad else 0)
