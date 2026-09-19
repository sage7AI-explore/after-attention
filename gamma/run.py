"""
Runner for the gamma measurement.

Spend control, in order of strictness:
  1. Pre-flight projection. If the projected cost of the requested design exceeds the cap,
     the run refuses to start and prints what would fit.
  2. Running ledger from the token usage the APIs actually report — never an estimate.
  3. Hard stop at STOP_FRACTION of the cap, with partial results written and the shortfall
     recorded so the analysis can report an incomplete design honestly.

Keys are read from the environment and never logged, printed or written to disk.
Run `--dry-run` first: it exercises the whole pipeline against a stub client at zero cost.
"""
import argparse, json, os, random, re, sys, time
import pricing, catalog

STOP_FRACTION = 0.90
ARMS = ("A", "B", "C")


# ----------------------------------------------------------------- providers
def call_anthropic(model, prompt, key):
    import requests
    r = requests.post("https://api.anthropic.com/v1/messages",
                      headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                               "content-type": "application/json"},
                      json={"model": model, "max_tokens": 16,
                            "messages": [{"role": "user", "content": prompt}]},
                      timeout=60)
    r.raise_for_status()
    d = r.json()
    return (d["content"][0]["text"],
            d["usage"]["input_tokens"], d["usage"]["output_tokens"])


def call_openai(model, prompt, key):
    import requests
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}",
                               "content-type": "application/json"},
                      json={"model": model, "max_completion_tokens": 16,
                            "messages": [{"role": "user", "content": prompt}]},
                      timeout=60)
    r.raise_for_status()
    d = r.json()
    return (d["choices"][0]["message"]["content"],
            d["usage"]["prompt_tokens"], d["usage"]["completion_tokens"])


def call_google(model, prompt, key):
    import requests
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "content-type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"maxOutputTokens": 16}},
        timeout=60)
    r.raise_for_status()
    d = r.json()
    u = d.get("usageMetadata", {})
    return (d["candidates"][0]["content"]["parts"][0]["text"],
            u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0))


def call_stub(model, prompt, key):
    """Zero-cost stub. Picks a product with a mild bias toward whatever line is longest,
    so --dry-run exercises parsing, ledgering and analysis end to end."""
    ids = re.findall(r"^(P\d\d) \|", prompt, re.M)
    lines = {i: len(l) for l, i in
             ((l, l.split(" |")[0]) for l in prompt.split("\n") if re.match(r"^P\d\d \|", l))}
    pick = max(ids, key=lambda i: lines[i] + random.random() * 60)
    return pick, len(prompt) // 4, 4


CALLERS = dict(anthropic=call_anthropic, openai=call_openai, google=call_google)


# ----------------------------------------------------------------- runner
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(pricing.MODELS))
    ap.add_argument("--cap", type=float, default=50.0, help="hard USD cap for this model")
    ap.add_argument("--sets", type=int, default=40)
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--framings", type=int, default=len(catalog.FRAMINGS))
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true", help="stub client, no network, no spend")
    a = ap.parse_args()

    spec = pricing.MODELS[a.model]
    out = a.out or f"results_gamma_{a.model.replace('.', '_')}{'_dry' if a.dry_run else ''}.jsonl"

    sets = catalog.build(n_sets=a.sets)
    jobs = [(s, arm, f, rep)
            for s in sets for arm in ARMS
            for f in range(a.framings) for rep in range(a.reps)]

    # ---- 1. pre-flight
    projected = pricing.project(a.model, len(jobs), 1300, 8)
    print(f"model        {a.model}")
    print(f"design       {len(sets)} sets x {len(ARMS)} arms x {a.framings} framings "
          f"x {a.reps} reps = {len(jobs):,} calls")
    print(f"projected    ${projected:,.2f}   cap ${a.cap:,.2f}")
    if projected > a.cap:
        per = pricing.project(a.model, 1, 1300, 8)
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
    spent, n, excluded = 0.0, 0, 0
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
                    text, tin, tout = caller(a.model, prompt, key)
                    break
                except Exception as e:                      # noqa: BLE001
                    err = str(e)[:200]
                    time.sleep(2 ** attempt)
            spent += pricing.cost(a.model, tin, tout)
            n += 1

            choice = None
            if text:
                m = re.search(r"P\d\d", text.strip())
                if m and m.group(0) in positions:
                    choice = m.group(0)
            if choice is None:
                excluded += 1

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

            if n % 100 == 0:
                rate = spent / n
                print(f"  {n:,}/{len(jobs) - len(done):,}  ${spent:,.2f}  "
                      f"(${rate:.4f}/call, {excluded} excluded, "
                      f"{(time.time() - t0) / 60:.1f}m)", flush=True)

    print(f"\ncompleted    {n:,} calls")
    print(f"spent        ${spent:,.2f} of ${a.cap:.2f}")
    print(f"excluded     {excluded:,} ({excluded / max(n, 1):.1%})")
    print(f"wrote        {out}")


if __name__ == "__main__":
    main()
