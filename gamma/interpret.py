"""
Interpretation guard. Turns a fitted contrast into the verdict that was COMMITTED IN ADVANCE
in experiments.json, and lints prose for language that overstates a non-significant result.

The point is to take the interpretive choice away from whoever reads the numbers after
seeing them. The verdict text is fixed before the data; this only selects which one applies.

    python3 gamma/interpret.py lint paper/After_Attention_draft_v0.11.md
"""
import json, os, re, sys
from math import erf, sqrt

HERE = os.path.dirname(os.path.abspath(__file__))
REG = json.load(open(os.path.join(HERE, "experiments.json")))


def p_value(z, test):
    phi = lambda x: 0.5 * (1 + erf(x / sqrt(2)))
    if test == "one-sided-positive":
        return 1 - phi(z)
    return 2 * (1 - phi(abs(z)))


def verdict(design, hyp, estimate, se, alpha=0.05):
    """Return the pre-committed verdict for a hypothesis. No free text is generated here."""
    e = REG[design]; h = e["hypotheses"][hyp]
    z = estimate / se if se else float("nan")
    p = p_value(z, h["test"])
    if hyp == "H3":
        if h["test"] == "one-sided-positive" and z > 0 and p < alpha:
            key = "H3_positive"
        elif z < 0 and p_value(abs(z), "one-sided-positive") < alpha:
            key = "H3_negative"
        else:
            key = "H3_null"
        return key, z, p, e["outcome_rules"][key]
    sig = p < alpha
    return ("significant" if sig else "not significant"), z, p, (
        f"{h['label']}: {'significant' if sig else 'NOT significant'} "
        f"({h['test']}, p = {p:.4f}).")


def lint(path, design="context"):
    """Flag language that describes a non-significant result as if it were an effect."""
    bad = REG[design]["forbidden_language"]
    text = open(path).read()
    hits = []
    for i, line in enumerate(text.split("\n"), 1):
        for phrase in bad:
            if phrase.lower() in line.lower():
                hits.append((i, phrase, line.strip()[:110]))
    if hits:
        print(f"LINT FAILED — {len(hits)} overstating phrase(s) in {path}:")
        for i, ph, ln in hits:
            print(f"  line {i}: '{ph}'\n    {ln}")
        return False
    print(f"lint OK — no overstating language in {path}")
    return True


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "lint":
        sys.exit(0 if lint(sys.argv[2]) else 1)

    # self-test: each committed outcome must be reachable, and only by the right numbers
    cases = [("large positive", 1.20, 0.35, "H3_positive"),
             ("positive, not significant", 0.40, 0.35, "H3_null"),
             ("exactly zero", 0.00, 0.35, "H3_null"),
             ("large negative", -1.10, 0.35, "H3_negative"),
             ("z = 1.60, one-sided p ~ 0.055: just short, must be NULL", 0.56, 0.35, "H3_null")]
    bad = 0
    for label, est, se, want in cases:
        key, z, p, text = verdict("context", "H3", est, se)
        ok = key == want; bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} z={z:+.2f} p={p:.3f} -> {key:12s} ({label})")
    import tempfile
    t = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
    t.write("The urgency effect was directionally positive but not significant.\n"); t.close()
    caught = not lint(t.name)
    print(f"  {'ok  ' if caught else 'FAIL'} lint catches 'directionally positive but not significant'")
    bad += not caught
    print("\ninterpret self-test:", "PASS" if not bad else f"{bad} FAILURES")
    sys.exit(1 if bad else 0)
