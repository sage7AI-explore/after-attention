"""
Runner for the gamma measurement.

Spend control, in order of strictness:
  1. Pre-flight projection. If the projected cost of the requested design exceeds the cap,
     the run refuses to start and prints what would fit.
  2. Running ledger from the token usage the APIs actually report — never an estimate.
  3. Hard stop at STOP_FRACTION of the cap, with partial results written and the shortfall
     recorded so the analysis can report an incomplete design honestly.

Failure control, which is a separate thing and was missing at first:
  4. A calibration window. The first CALIBRATE calls are checked before the sweep commits:
     if more than MAX_FAIL_RATE of them failed to produce a usable choice, the run aborts.
  5. A consecutive-failure trip. MAX_CONSECUTIVE failures in a row aborts.
  Money is not the only thing a bad run spends. The first live attempt failed on 100% of
  calls for thirteen minutes at zero cost, because every guard watched dollars and none
  watched whether anything was being recorded. These two do.

Keys are read from the environment and never logged, printed or written to disk.
Run `--dry-run` first: it exercises the whole pipeline against a stub client at zero cost.
Run `diagnose.py` before any live sweep: it prints the real response shape for a cent.
"""
import argparse, json, os, random, re, sys, time
import pricing, catalog

STOP_FRACTION = 0.90
CALIBRATE = 40          # calls checked before the sweep is allowed to continue
MAX_FAIL_RATE = 0.25    # abort if more than this share of the calibration window failed
MAX_CONSECUTIVE = 15    # abort after this many consecutive failures at any point
ARMS = ("A", "B", "C")


class CallFailed(Exception):
    """A call that did not yield usable text, with the reason preserved for the log."""


# ----------------------------------------------------------------- providers
def call_anthropic(model, prompt, key, max_tokens):
    import requests
    r = requests.post("https://api.anthropic.com/v1/messages",
                      headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                               "content-type": "application/json"},
                      json={"model": model, "max_tokens": max_tokens,
                            "messages": [{"role": "user", "content": prompt}]},
                      timeout=60)
    r.raise_for_status()
    d = r.json()
    usage = d.get("usage", {})
    tin = usage.get("input_tokens", 0)
    tout = usage.get("output_tokens", 0)
    # The response may carry non-text blocks (thinking, redacted_thinking) before any
    # text block, or no text block at all when the token budget was spent before the
    # answer. Index 0 is not reliably the answer — find the text block.
    blocks = d.get("content") or []
    text = next((b.get("text", "") for b in blocks if b.get("type") == "text"), None)
    if not text:
        raise CallFailed(
            f"no text block (types={[b.get('type') for b in blocks]}, "
            f"stop_reason={d.get('stop_reason')!r}, out_tokens={tout})")
    return text, tin, tout


def call_openai(model, prompt, key, max_tokens):
    import requests
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}",
                               "content-type": "application/json"},
                      json={"model": model, "max_completion_tokens": max_tokens,
                            "messages": [{"role": "user", "content": prompt}]},
                      timeout=60)
    r.raise_for_status()
    d = r.json()
    usage = d.get("usage", {})
    tin = usage.get("prompt_tokens", 0)
    tout = usage.get("completion_tokens", 0)
    choices = d.get("choices") or []
    text = (choices[0].get("message", {}).get("content") if choices else None)
    if not text:
        fr = choices[0].get("finish_reason") if choices else None
        raise CallFailed(f"no message content (finish_reason={fr!r}, out_tokens={tout})")
    return text, tin, tout


def call_google(model, prompt, key, max_tokens):
    import requests
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "content-type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"maxOutputTokens": max_tokens}},
        timeout=60)
    r.raise_for_status()
    d = r.json()
    u = d.get("usageMetadata", {})
    tin = u.get("promptTokenCount", 0)
    tout = u.get("candidatesTokenCount", 0)
    cands = d.get("candidates") or []
    parts = (cands[0].get("content", {}).get("parts") or []) if cands else []
    text = next((p.get("text", "") for p in parts if p.get("text")), None)
    if not text:
        fr = cands[0].get("finishReason") if cands else None
        raise CallFailed(f"no text part (finishReason={fr!r}, out_tokens={tout})")
    return text, tin, tout


def call_stub(model, prompt, key, max_tokens):
    """Zero-cost stub. Picks a product with a mild bias toward whatever line is longest,
    so --dry-run exercises parsing, ledgering and analysis end to end."""
    ids = re.findall(r"^(P\d\d) \|", prompt, re.M)
    lines = {i: len(l) for l, i in
             ((l, l.split(" |")[0]) for l in prompt.split("\n") if re.match(r"^P\d\d \|", l))}
    pick = max(ids, key=lambda i: lines[i] + random.random() * 60)
    return pick, len(prompt) // 4, 4


CALLERS = dict(anthropic=call_anthropic, openai=call_openai, google=call_google)


def abort(msg, out, n, excluded):
    print(f"\n{'=' * 74}\nABORTING: {msg}\n{'=' * 74}")
    print(f"  {n:,} calls attempted, {excluded:,} produced no usable choice.")
    print(f"  Partial output is in {out}.")
    print( "  DELETE that file before re-running: the runner treats every recorded")
    print( "  (set, arm, framing, rep) as done, so failed cells would be skipped on")
    print( "  resume and become permanent holes in the design.")
    print( "  Then run:  python3 gamma/diagnose.py   to see the real response shape.")
    sys.exit(3)


# ----------------------------------------------------------------- runner
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(pricing.MODELS))
    ap.add_argument("--cap", type=float, default=50.0, help="hard USD cap for this model")
    ap.add_argument("--sets", type=int, default=40)
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--framings", type=int, default=len(catalog.FRAMINGS))
    ap.add_argument("--max-tokens", type=int, default=64,
                    help="output budget per call; too small starves the answer when the "
                         "model emits a preamble block first")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true", help="stub client, no network, no spend")
    a = ap.parse_args()

    spec = pricing.MODELS[a.model]
    here = os.path.dirname(os.path.abspath(__file__))
    out = a.out or os.path.join(
        here, f"results_gamma_{a.model.replace('.', '_')}{'_dry' if a.dry_run else ''}.jsonl")

    sets = catalog.build(n_sets=a.sets)
    jobs = [(s, arm, f, rep)
            for s in sets for arm in ARMS
            for f in range(a.framings) for rep in range(a.reps)]

    # ---- 1. pre-flight
    projected = pricing.project(a.model, len(jobs), 1300, a.max_tokens)
    print(f"model        {a.model}")
    print(f"design       {len(sets)} sets x {len(ARMS)} arms x {a.framings} framings "
          f"x {a.reps} reps = {len(jobs):,} calls")
    print(f"projected    ${projected:,.2f}   cap ${a.cap:,.2f}   "
          f"(worst case: every call spends its full {a.max_tokens}-token budget)")
    if projected > a.cap:
        per = pricing.project(a.model, 1, 1300, a.max_tokens)
        print(f"\nREFUSING TO START: projection exceeds the cap.\n"
              f"  ${a.cap:.2f} buys about {int(a.cap / per):,} calls at ${per:.4f} each.\n"
              f"  Reduce --sets or --reps, or raise --cap deliberately.")
        sys.exit(2)

    key = "stub"
    if not a.dry_run:
        key = os.environ.get(spec["env"], "")
        if not key:
            print(f"\n{spec['env']} is not set. Export it in this shell; it is never logged "
                  f"or written to disk.")
            sys.exit(2)

    done = set()
    if os.path.exists(out):
        for line in open(out):
            r = json.loads(line)
            done.add((r["set_id"], r["arm"], r["framing"], r["rep"]))
        print(f"resuming     {len(done):,} calls already recorded")

    caller = call_stub if a.dry_run else CALLERS[spec["provider"]]
    spent, n, excluded, consecutive = 0.0, 0, 0, 0
    calibrated = False
    t0 = time.time()

    with open(out, "a") as fh:
        for s, arm, f, rep in jobs:
            if (s["set_id"], arm, f, rep) in done:
                continue
            if spent >= STOP_FRACTION * a.cap:
                print(f"\nSTOPPING at ${spent:,.2f} — {STOP_FRACTION:.0%} of the ${a.cap:.2f} cap. "
                      f"{n:,} calls completed, design incomplete.")
                break

            rng = random.Random(catalog.seed_for(s["set_id"], arm, f, rep))
            prompt, positions = catalog.prompt(s, arm, f, rng)

            text, tin, tout, err = None, 0, 0, None
            for attempt in range(3):
                try:
                    text, tin, tout = caller(a.model, prompt, key, a.max_tokens)
                    err = None               # a retry that succeeded is a success
                    break
                except Exception as e:                      # noqa: BLE001
                    err = f"{type(e).__name__}: {e}"[:200]
                    text = None
                    if attempt < 2:
                        time.sleep(2 ** attempt)
            spent += pricing.cost(a.model, tin, tout)
            n += 1

            choice = None
            if text:
                m = re.search(r"P\d\d", text.strip())
                if m and m.group(0) in positions:
                    choice = m.group(0)
                elif not err:
                    err = f"unparseable reply: {text.strip()[:60]!r}"
            if choice is None:
                excluded += 1
                consecutive += 1
            else:
                consecutive = 0

            fh.write(json.dumps(dict(
                model=a.model, set_id=s["set_id"], arm=arm, framing=f, rep=rep,
                choice=choice, raw=(text or "")[:40], error=err,
                target_id=s["target_id"], best_value_id=s["best_value_id"],
                target_position=positions[s["target_id"]],
                chose_target=(choice == s["target_id"]) if choice else None,
                chose_best_value=(choice == s["best_value_id"]) if choice else None,
                in_tokens=tin, out_tokens=tout,
                usd=round(pricing.cost(a.model, tin, tout), 6))) + "\n")
            fh.flush()

            # ---- 4. calibration window
            if not calibrated and n >= CALIBRATE:
                calibrated = True
                rate = excluded / n
                print(f"\ncalibration  {n} calls, {excluded} failed ({rate:.0%}), "
                      f"${spent:.4f} spent")
                if rate > MAX_FAIL_RATE:
                    last = err or "see the error field in the output file"
                    abort(f"{rate:.0%} of the first {n} calls produced no usable choice "
                          f"(limit {MAX_FAIL_RATE:.0%}).\n  Last error: {last}", out, n, excluded)
                print("             continuing\n")

            # ---- 5. consecutive-failure trip
            if consecutive >= MAX_CONSECUTIVE:
                abort(f"{consecutive} consecutive calls produced no usable choice.\n"
                      f"  Last error: {err or 'unknown'}", out, n, excluded)

            if n % 100 == 0:
                print(f"  {n:,}/{len(jobs) - len(done):,}  ${spent:,.2f}  "
                      f"(${spent / n:.4f}/call, {excluded} excluded, "
                      f"{(time.time() - t0) / 60:.1f}m)", flush=True)

    print(f"\ncompleted    {n:,} calls")
    print(f"spent        ${spent:,.2f} of ${a.cap:.2f}")
    print(f"excluded     {excluded:,} ({excluded / max(n, 1):.1%})")
    print(f"wrote        {out}")


if __name__ == "__main__":
    main()
