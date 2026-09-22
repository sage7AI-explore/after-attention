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
  Both of those count MODEL EXCLUSIONS only. A call that got no response at all is a
  transport failure, not an observation (see PREREGISTRATION.md), so it is counted and
  tripped separately by MAX_API_FAIL_RATE: a broken pipe stops the run, but it never
  gets reported as the model failing to answer.
  Money is not the only thing a bad run spends. The first live attempt failed on 100% of
  calls for thirteen minutes at zero cost, because every guard watched dollars and none
  watched whether anything was being recorded. These two do.

Keys are read from the environment and never logged, printed or written to disk.
Run `--dry-run` first: it exercises the whole pipeline against a stub client at zero cost.
Run `diagnose.py` before any live sweep: it prints the real response shape for a cent.
"""
import argparse, collections, json, os, random, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
import pricing, catalog, context

STOP_FRACTION = 0.90
CALIBRATE = 40          # calls checked before the sweep is allowed to continue
MAX_FAIL_RATE = 0.25    # abort if more than this share of the calibration window failed
RECENT_WINDOW = 50      # rolling window used instead of a consecutive count
MAX_RECENT_FAIL = 0.60  # abort if this share of the last RECENT_WINDOW calls failed
MAX_API_FAIL_RATE = 0.10  # stop if this share of calls got no response at all (transport)
ARMS = ("A", "B", "C")


class CallFailed(Exception):
    """A call that did not yield usable text, with the reason preserved for the log."""


def parse_choice(text, valid):
    """Accept a reply ONLY if it is a bare product ID, as the instruction demands.

    The earlier version used re.search for the first P\d\d anywhere in the reply. On a
    model that writes prose instead of complying — which happens when reasoning is off
    and the budget is tight — that extracts a product code from mid-sentence
    deliberation and records it as the agent's choice. The probe caught exactly this:
    a reply beginning "Looking at value per dollar across all metrics, I'" was parsed
    as a choice of P10.

    A wrong choice silently recorded is worse than a failed call, because nothing
    downstream can detect it. Anything that is not a bare ID is excluded and logged.
    """
    s = (text or "").strip()
    m = re.fullmatch(r"[*`\s]*(P\d\d)[*`.\s]*", s)
    if not m:
        return None, f"non-compliant reply (not a bare ID): {s[:70]!r}"
    pid = m.group(1)
    if pid not in valid:
        return None, f"ID not in this choice set: {pid}"
    return pid, None


# ----------------------------------------------------------------- providers
class APIError(Exception):
    """The provider refused the request. Carries the response body, which is where the
    reason is (credit balance, auth, malformed request). No model response exists, so
    this is not an observation and is never written to the results file."""
    def __init__(self, status, body):
        self.status, self.body = status, body
        super().__init__(f"HTTP {status}: {body[:300]}")

    @property
    def fatal(self):
        b = self.body.lower()
        return (self.status in (401, 403)
                or (self.status == 400 and any(w in b for w in
                    ("credit balance", "billing", "quota", "insufficient"))))


def _check(r):
    if r.status_code >= 400:
        raise APIError(r.status_code, r.text or "")


def call_anthropic(model, prompt, key, max_tokens, thinking=True):
    """thinking=True leaves the provider default alone; False sends thinking: disabled.

    The default is ON, which is the provider default and therefore what the original
    preregistration specifies. An earlier amendment disabled it on the premise that the
    OpenAI and Google models answer directly; the provider probe showed they do not.
    gpt-5.6-terra reported reasoning_tokens equal to its whole budget and
    gemini-3.8-flash reported thoughtsTokenCount of 57. All three deliberate by default,
    so disabling it for Anthropic alone would have created the very cross-model confound
    the amendment was written to avoid. Disabling it also made this model answer in
    prose rather than with a bare ID, which the strict parser now rejects.

    The real fix for the original failure was the output budget, not the reasoning
    setting: 64 tokens is consumed by deliberation before any answer is emitted, on all
    three providers. See PREREGISTRATION.md, amendment of 19 September 2026 as corrected.
    """
    import requests
    payload = {"model": model, "max_tokens": max_tokens,
               "messages": [{"role": "user", "content": prompt}]}
    if not thinking:
        payload["thinking"] = {"type": "disabled"}   # --no-thinking only
    r = requests.post("https://api.anthropic.com/v1/messages",
                      headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                               "content-type": "application/json"},
                      json=payload, timeout=60)
    _check(r)
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
    _check(r)
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
    _check(r)
    d = r.json()
    u = d.get("usageMetadata", {})
    tin = u.get("promptTokenCount", 0)
    # candidatesTokenCount excludes thoughtsTokenCount, but thoughts are billed as
    # output. Counting only candidates under-reports spend by an order of magnitude
    # here (3 answer tokens against 57 thought tokens in the probe), which would make
    # the cap meaningless for this provider.
    tout = u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
    cands = d.get("candidates") or []
    parts = (cands[0].get("content", {}).get("parts") or []) if cands else []
    text = next((p.get("text", "") for p in parts if p.get("text")), None)
    if not text:
        fr = cands[0].get("finishReason") if cands else None
        raise CallFailed(f"no text part (finishReason={fr!r}, out_tokens={tout})")
    return text, tin, tout


OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if not OLLAMA.startswith("http"):
    OLLAMA = "http://" + OLLAMA


def ollama_config(model):
    """The identity of a locally executed model is its weights and settings, not its name.
    Returns the digest Ollama reports for the pulled weights plus the quantization and
    parameter details, so every row can be tied to exactly what ran."""
    import requests
    tags = requests.get(f"{OLLAMA}/api/tags", timeout=30).json().get("models", [])
    m = next((t for t in tags if t.get("name") == model or t.get("model") == model), None)
    if m is None:
        raise SystemExit(f"\n{model} is not pulled in Ollama. Run:  ollama pull {model}")
    show = requests.post(f"{OLLAMA}/api/show", json={"model": model}, timeout=60).json()
    det = show.get("details", {}) or m.get("details", {})
    return dict(digest=m.get("digest"), quantization=det.get("quantization_level"),
                parameter_size=det.get("parameter_size"), family=det.get("family"),
                modelfile_parameters=(show.get("parameters") or "").strip()[:300])


def call_ollama(model, prompt, key, max_tokens, thinking=True):
    """Local open-weight model through Ollama's chat endpoint. Provider defaults are kept
    (no temperature or thinking override), matching the hosted runs; only the output
    budget is set, and the context window is set large enough that the ~1,300-token
    prompt plus the budget cannot be silently truncated."""
    import requests
    r = requests.post(f"{OLLAMA}/api/chat",
                      json={"model": model, "stream": False,
                            "messages": [{"role": "user", "content": prompt}],
                            **({} if thinking else {"think": False}),
                            "options": {"num_predict": max_tokens, "num_ctx": 8192}},
                      timeout=900)
    _check(r)
    d = r.json()
    tin = d.get("prompt_eval_count", 0)
    tout = d.get("eval_count", 0)
    text = (d.get("message") or {}).get("content") or None
    if not text:
        raise CallFailed(f"no content (done_reason={d.get('done_reason')!r}, out_tokens={tout})")
    return text, tin, tout


def call_stub(model, prompt, key, max_tokens, thinking=True):
    """Zero-cost stub. Picks a product with a mild bias toward whatever line is longest,
    so --dry-run exercises parsing, ledgering and analysis end to end.

    Draws from a Random seeded by the prompt, NOT from the global random module. Under
    concurrency the global RNG is shared, so its draw order depends on thread
    interleaving and the same cell yields a different pick between a serial and a
    parallel run — which makes the dry run unreproducible and therefore useless as the
    pipeline test. zlib.crc32 is used rather than hash(), which Python salts per process.
    """
    import zlib
    rng = random.Random(zlib.crc32(prompt.encode()))
    ids = re.findall(r"^(P\d\d) \|", prompt, re.M)
    lines = {i: len(l) for l, i in
             ((l, l.split(" |")[0]) for l in prompt.split("\n") if re.match(r"^P\d\d \|", l))}
    pick = max(ids, key=lambda i: lines[i] + rng.random() * 60)
    return pick, len(prompt) // 4, 4


CALLERS = dict(anthropic=call_anthropic, openai=call_openai, google=call_google, ollama=call_ollama)


def transport_stop(msg, out, n, api_failed):
    """Stop because the calls are not reaching the model. This is NOT a statement about
    the model's answers: no observation was produced, so nothing here bears on the
    hypotheses. Resuming re-runs exactly these calls."""
    print(f"\n{'=' * 74}\nSTOPPING: {msg}\n{'=' * 74}")
    print(f"  {api_failed:,} of {n:,} calls this session got no response from the server.")
    print( "  These are transport failures, not model answers. They are NOT observations:")
    print( "  none of them is in the results file and none counts toward any exclusion rate.")
    print(f"  KEEP {out} — every row in it is a real model response.")
    print( "  The failed calls are in the .api_errors.jsonl file beside it and are retried")
    print( "  automatically when you resume. Fix the server, then re-run the same command.")
    sys.exit(4)


def abort(msg, out, n, excluded):
    print(f"\n{'=' * 74}\nABORTING: {msg}\n{'=' * 74}")
    print(f"  {n:,} calls attempted this session, {excluded:,} produced no usable choice.")
    print(f"  KEEP {out} — every row in it is a real model response.")
    print( "  API failures are not in it; they are in the .api_errors.jsonl file beside it")
    print( "  and are retried automatically when you resume.")
    print( "  Model exclusions (bad or truncated answers) ARE in it and are never re-run:")
    print( "  re-running them until they succeed would be optional stopping.")
    sys.exit(3)


def run_one(job, a, spec, key, caller):
    """Execute one call. Pure with respect to shared state: the RNG is seeded from
    (set, arm, framing, rep), so a worker's result does not depend on execution order
    and concurrency cannot change which permutation a cell was shown."""
    s, arm, f, rep = job
    if a.design == "context":
        rng = random.Random(context.seed_for(s["set_id"], arm, f, rep))
        prompt, positions = context.prompt(s, arm, f, rng)
    else:
        rng = random.Random(catalog.seed_for(s["set_id"], arm, f, rep))
        prompt, positions = catalog.prompt(s, arm, f, rng)

    text, tin, tout, err = None, 0, 0, None
    for attempt in range(4):
        try:
            if spec["provider"] in ("anthropic", "ollama") or a.dry_run:
                text, tin, tout = caller(a.model, prompt, key, a.max_tokens,
                                         thinking=not a.no_thinking)
            else:
                text, tin, tout = caller(a.model, prompt, key, a.max_tokens)
            err = None               # a retry that succeeded is a success
            break
        except APIError as e:
            err = f"APIError: {e}"[:500]
            text = None
            if e.fatal:
                return None, False, 0.0, e      # retrying cannot help; stop the run
        except Exception as e:                                      # noqa: BLE001
            err = f"{type(e).__name__}: {e}"[:500]
            text = None
            if attempt < 3:
                # jittered backoff; concurrency makes rate limiting likely, and
                # unjittered retries from several workers arrive together
                time.sleep((2 ** attempt) + random.random())

    choice = None
    if text:
        choice, perr = parse_choice(text, positions)
        if perr and not err:
            err = perr

    row = dict(
        model=a.model, max_tokens=a.max_tokens, thinking=(not a.no_thinking),
        design=a.design,
        set_id=s["set_id"], arm=arm, framing=f, rep=rep,
        urgent=(context.CELLS[f][0] if a.design == "context" else None),
        stakes=(context.CELLS[f][1] if a.design == "context" else None),
        choice=choice, raw=(text or "")[:40], error=err,
        target_id=s["target_id"], best_value_id=s["best_value_id"],
        target_position=positions[s["target_id"]],
        chose_target=(choice == s["target_id"]) if choice else None,
        chose_best_value=(choice == s["best_value_id"]) if choice else None,
        in_tokens=tin, out_tokens=tout,
        usd=round(pricing.cost(a.model, tin, tout), 6),
        config_digest=getattr(a, "config_digest", None))
    if text is None and err:
        # The call never produced a model response (network or provider failure after
        # retries). Not an observation: logged to the sidecar and retried on resume.
        return row, False, pricing.cost(a.model, tin, tout), "transport"
    return row, (choice is not None), pricing.cost(a.model, tin, tout), None


# ----------------------------------------------------------------- runner
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(pricing.MODELS))
    ap.add_argument("--cap", type=float, default=50.0, help="hard USD cap for this model")
    ap.add_argument("--sets", type=int, default=40)
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--framings", type=int, default=len(catalog.FRAMINGS))
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="output budget per call. All three providers deliberate before "
                         "answering, and a small budget is consumed entirely by that "
                         "deliberation — 64 produced a 100%% failure on every provider.")
    ap.add_argument("--expected-out", type=int, default=300,
                    help="typical output tokens per call, used for the cost projection. "
                         "The hard protection is the live ledger and the cap, not this.")
    ap.add_argument("--no-thinking", dest="no_thinking", action="store_true",
                    help="Anthropic: send thinking: disabled (NOT the preregistered hosted "
                         "configuration). Ollama: send think=false, as registered for base_local. "
                         "Hosted: NOT the preregistered "
                         "configuration — the registration fixes provider defaults, and "
                         "all three providers deliberate by default. For the reverse "
                         "comparison only.")
    ap.add_argument("--design", choices=("base", "base_local", "context"), default="base",
                    help="base: the original study (5 framings). context: the matched triad "
                         "crossed with 2 urgency x 2 stakes cells, with a context-neutral "
                         "placebo; see context.py.")
    ap.add_argument("--concurrency", type=int, default=8,
                    help="parallel in-flight calls. Results do not depend on it: every "
                         "cell seeds its own RNG from (set, arm, framing, rep). Raise it "
                         "if the provider tolerates it; drop to 1 to reproduce serially.")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true", help="stub client, no network, no spend")
    a = ap.parse_args()

    spec = pricing.MODELS[a.model]
    # base keeps the 2,048 it was run with, so it reproduces exactly. The context design
    # lifts the ceiling: in the base study gemini-3.8-flash ran within 150 tokens of 2,048
    # on 36% of calls and was truncated 15 times, and a stakes framing that prompts more
    # deliberation would be truncated more in exactly the cells under test.
    if a.max_tokens is None:
        a.max_tokens = 8192 if a.design == "context" else 2048
    here = os.path.dirname(os.path.abspath(__file__))
    out = a.out or os.path.join(
        here, f"results_gamma_{a.model.replace('.', '_').replace(':', '_')}"
              f"{'_context' if a.design == 'context' else ''}{'_dry' if a.dry_run else ''}.jsonl")

    if a.design == "context":
        sets = context.build()[:a.sets]
        a.framings = len(context.CELLS)   # the four context cells take the framing slot
    else:
        sets = catalog.build(n_sets=a.sets)
    jobs = [(s, arm, f, rep)
            for s in sets for arm in ARMS
            for f in range(a.framings) for rep in range(a.reps)]

    # ---- 1. pre-flight
    measured = pricing.expected(a.model, len(jobs), a.design)
    projected = measured if measured is not None else \
        pricing.project(a.model, len(jobs), 1300, a.expected_out)
    worst = pricing.project(a.model, len(jobs), 1300, a.max_tokens)
    print(f"model        {a.model}")
    label = "context cells" if a.design == "context" else "framings"
    print(f"design       {len(sets)} sets x {len(ARMS)} arms x {a.framings} {label} "
          f"x {a.reps} reps = {len(jobs):,} calls")
    src = (f"from 6,000-call run means{' (context-adjusted)' if a.design == 'context' else ''}"
           if measured is not None else f"at {a.expected_out} output tokens/call (not measured)")
    print(f"projected    ${projected:,.2f}   {src}")
    print(f"worst case   ${worst:,.2f}   if every call spent its full {a.max_tokens}-token budget")
    print(f"cap          ${a.cap:,.2f}   enforced on ACTUAL reported spend, not on either estimate")
    if spec["provider"] == "anthropic":
        print(f"thinking     {'DISABLED (not the preregistered configuration)' if a.no_thinking else 'provider default (on)'}")
    import preflight
    preflight.check(a.model, a.design, a.reps, a.sets, a.cap, a.max_tokens, dry_run=a.dry_run,
                    thinking=(not a.no_thinking))
    prior_usd, prior_n = preflight.cumulative_spend(out)
    if prior_n:
        print(f"already      {prior_n:,} rows, ${prior_usd:,.2f} spent in earlier sessions "
              f"(cap applies to this session; cumulative ${prior_usd:,.2f} + this session)")
    if projected > a.cap:
        per = projected / max(len(jobs), 1)
        print(f"\nREFUSING TO START: projection exceeds the cap.\n"
              f"  ${a.cap:.2f} buys about {int(a.cap / per):,} calls at ${per:.4f} each.\n"
              f"  Reduce --sets or --reps, or raise --cap deliberately.")
        sys.exit(2)

    key = "stub"
    config = None
    if spec["provider"] == "ollama" and not a.dry_run:
        config = ollama_config(a.model)
        print(f"weights      digest {config['digest']}  quant {config['quantization']}  "
              f"size {config['parameter_size']}")
        key = "local"
        a.config_digest = config["digest"]
    elif not a.dry_run:
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
    todo = [j for j in jobs if (j[0]["set_id"], j[1], j[2], j[3]) not in done]
    if not todo:
        print("nothing left to do"); return

    spent, n, excluded = 0.0, 0, 0
    recent = collections.deque(maxlen=RECENT_WINDOW)      # observations only: True = usable choice
    recent_api = collections.deque(maxlen=RECENT_WINDOW)  # attempts: True = no response at all
    out_tokens_seen = []
    lock = threading.Lock()
    t0 = time.time()
    stop = False

    print(f"concurrency  {a.concurrency} workers "
          f"({'serial' if a.concurrency == 1 else 'order-independent: each cell is seeded from its own indices'})")
    print()

    fatal_err, api_failed = [None], [0]
    errpath = out.replace(".jsonl", ".api_errors.jsonl")

    def fatal_stop():
        e = fatal_err[0]
        print(f"\n{'=' * 74}\nSTOPPED: the provider refused the request (HTTP {e.status}).\n"
              f"{'=' * 74}\n  {e.body[:400]}\n")
        if "credit" in e.body.lower() or "billing" in e.body.lower():
            print("  Your API credit balance is the likely cause. Add credit in the provider "
                  "console, then\n  re-run the same command; it resumes where it stopped.")
        elif e.status in (401, 403):
            print("  The API key was rejected. Check the key in .env.local.")
        print(f"\n  {out} is intact. Nothing needs deleting.")
        sys.exit(3)

    with open(out, "a") as fh, open(errpath, "a") as errfh:

        def drain(chunk):
            """Run one chunk and fold the results in. Returns False to stop the sweep."""
            nonlocal spent, n, excluded, stop
            with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
                for row, ok, usd, fail in ex.map(lambda j: run_one(j, a, spec, key, caller), chunk):
                    with lock:
                        if isinstance(fail, APIError):
                            stop = True
                            fatal_err[0] = fail
                            continue
                        if fail == "transport":
                            errfh.write(json.dumps(row) + "\n"); errfh.flush()
                            api_failed[0] += 1
                            n += 1; recent_api.append(True)
                            continue
                        spent += usd
                        n += 1
                        recent.append(ok)
                        recent_api.append(False)
                        out_tokens_seen.append(row["out_tokens"])
                        if not ok:
                            excluded += 1
                        fh.write(json.dumps(row) + "\n")
                        fh.flush()
                        if n % 25 == 0:
                            el = (time.time() - t0) / 60
                            rate = n / max(time.time() - t0, 1e-9)
                            eta = (len(todo) - n) / rate / 60 if rate else 0
                            print(f"  {n:,}/{len(todo):,}  ${spent:,.2f}  "
                                  f"({rate:.1f} calls/s, {excluded} excluded, "
                                  f"{el:.1f}m elapsed, ~{eta:.0f}m left)", flush=True)
            return True

        # ---- 4. calibration window, run first and judged before the sweep commits
        head, tail = todo[:CALIBRATE], todo[CALIBRATE:]
        drain(head)
        if fatal_err[0]: fatal_stop()
        observed = n - api_failed[0]
        rate = excluded / max(observed, 1)
        api_rate = api_failed[0] / max(n, 1)
        print(f"\ncalibration  {n} calls attempted: {observed} observations, "
              f"{excluded} excluded ({rate:.0%} of observations), "
              f"{api_failed[0]} no response ({api_rate:.0%} of attempts), ${spent:.4f} spent")
        near = sum(1 for o in out_tokens_seen if o >= 0.9 * a.max_tokens)
        share = near / max(len(out_tokens_seen), 1)
        mean_out = sum(out_tokens_seen) / max(len(out_tokens_seen), 1)
        print(f"             mean output {mean_out:.0f} tokens; {share:.0%} of calls used "
              f">=90% of the {a.max_tokens}-token ceiling")
        if share > 0.05:
            msg = (f"{share:.0%} of calibration calls reached 90% of the output ceiling. The "
                   f"ceiling is close to binding, so truncation will exclude calls and may do so "
                   f"differentially by condition. Raise --max-tokens and re-run.")
            if a.design in ("context", "base_local"):
                abort(msg, out, n, excluded)
            # The base study was run at this ceiling and is reported as run; re-running it
            # must reproduce it rather than refuse. Flag the problem loudly instead.
            print(f"\n  WARNING  {msg}\n  (base design continues so it reproduces as originally "
                  f"run; see gamma/_failed_runs/README.md and the paper, section 8.5)\n")
        if a.design == "base_local" and mean_out > 200:
            abort(f"mean output is {mean_out:.0f} tokens over calibration. A bare product ID is "
                  f"under 10; the model is almost certainly still reasoning before answering, "
                  f"so think=false was not honored. At local speeds the run is not feasible.",
                  out, n, excluded)
        if api_rate > MAX_API_FAIL_RATE:
            transport_stop(f"{api_rate:.0%} of the first {n} calls got no response from the "
                           f"server (limit {MAX_API_FAIL_RATE:.0%}). For a local Ollama server "
                           f"this is usually too many workers for one machine: each concurrent "
                           f"request needs its own context, and the server drops requests it "
                           f"cannot seat. Lower --concurrency and resume.",
                           out, n, api_failed[0])
        if observed and rate > MAX_FAIL_RATE:
            abort(f"{rate:.0%} of the {observed} calibration observations produced no usable "
                  f"choice (limit {MAX_FAIL_RATE:.0%}).", out, n, excluded)
        print("             continuing\n")

        # ---- the sweep, in chunks so the guards are checked between them
        chunk_size = max(a.concurrency * 4, 25)
        for i in range(0, len(tail), chunk_size):
            if spent >= STOP_FRACTION * a.cap:
                print(f"\nSTOPPING at ${spent:,.2f} — {STOP_FRACTION:.0%} of the ${a.cap:.2f} cap. "
                      f"{n:,} calls completed, design incomplete.")
                break
            if config and ollama_config(a.model)["digest"] != config["digest"]:
                abort("the local model's weights changed during the run (digest differs). "
                      "Rows before and after would come from different configurations.",
                      out, n, excluded)
            if len(recent_api) == RECENT_WINDOW:
                api_fail_rate = sum(recent_api) / len(recent_api)
                if api_fail_rate > MAX_API_FAIL_RATE:
                    transport_stop(f"{api_fail_rate:.0%} of the last {RECENT_WINDOW} calls got "
                                   f"no response from the server (limit "
                                   f"{MAX_API_FAIL_RATE:.0%}). Lower --concurrency and resume.",
                                   out, n, api_failed[0])
            if len(recent) == RECENT_WINDOW:
                fail_rate = 1 - (sum(recent) / len(recent))
                if fail_rate > MAX_RECENT_FAIL:
                    abort(f"{fail_rate:.0%} of the last {RECENT_WINDOW} observations produced "
                          f"no usable choice (limit {MAX_RECENT_FAIL:.0%}).", out, n, excluded)
            drain(tail[i:i + chunk_size])
            if fatal_err[0]: fatal_stop()

    print(f"\ncompleted    {n:,} calls")
    print(f"spent        ${spent:,.2f} of ${a.cap:.2f}")
    print(f"excluded     {excluded:,} ({excluded / max(n - api_failed[0], 1):.1%} of "
          f"{n - api_failed[0]:,} observations)   model responses with no usable choice")
    if api_failed[0]:
        print(f"api failures {api_failed[0]:,}   no response; logged to {errpath}, retried on resume")
    if out_tokens_seen:
        hit = sum(1 for o in out_tokens_seen if o >= a.max_tokens - 8)
        print(f"at ceiling   {hit:,} calls ended within 8 tokens of the {a.max_tokens}-token "
              f"ceiling (truncations, not model choices)")
    print(f"wrote        {out}")


if __name__ == "__main__":
    main()
