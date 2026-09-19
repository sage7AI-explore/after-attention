"""
Provider probe. Runs the REAL parsers from run.py against real responses and reports
whether each one yields a usable choice — rather than printing a skeleton and leaving
a human to infer it.

Costs a few cents. Run before any live sweep and after any provider or model change.

For Anthropic it probes several configurations, because claude-sonnet-5 emits an
extended-thinking block by default and a small output budget is consumed entirely by
that block before any text is produced.
"""
import json, os, random, sys
import catalog
import run as R


def show(obj, depth=0, maxdepth=4):
    pad = "  " * depth
    if isinstance(obj, dict):
        if depth >= maxdepth:
            return pad + "{%s}" % ", ".join(obj.keys())
        out = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                out.append(f"{pad}{k}:")
                out.append(show(v, depth + 1, maxdepth))
            else:
                s = v if not isinstance(v, str) else (v[:70] + ("..." if len(v) > 70 else ""))
                out.append(f"{pad}{k}: {s!r}")
        return "\n".join(out)
    if isinstance(obj, list):
        if not obj:
            return pad + "[] EMPTY"
        out = [f"{pad}[{len(obj)}]"]
        for i, v in enumerate(obj[:3]):
            out.append(f"{pad} [{i}]:")
            out.append(show(v, depth + 2, maxdepth))
        return "\n".join(out)
    return pad + repr(obj)


def attempt(label, fn):
    """Run a caller exactly as the sweep would, and report what the sweep would record."""
    print(f"--- {label}")
    try:
        text, tin, tout = fn()
    except Exception as e:                                          # noqa: BLE001
        print(f"    FAIL  {type(e).__name__}: {e}")
        return False, 0.0
    parsed = None
    import re
    m = re.search(r"P\d\d", (text or "").strip())
    if m:
        parsed = m.group(0)
    ok = parsed is not None
    print(f"    {'OK  ' if ok else 'FAIL'}  text={text.strip()[:50]!r}  "
          f"parsed={parsed!r}  tokens={tin}in/{tout}out")
    return ok, (tin, tout)


def main():
    sets = catalog.build()
    prompt, _ = catalog.prompt(sets[0], "B", 1, random.Random(0))
    results = {}

    # ---------------------------------------------------------------- anthropic
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    print("=" * 78); print("ANTHROPIC  claude-sonnet-5"); print("=" * 78)
    if not key:
        print("  ANTHROPIC_API_KEY not set; skipping\n")
    else:
        import requests
        raw = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-5", "max_tokens": 64,
                  "thinking": {"type": "disabled"},
                  "messages": [{"role": "user", "content": prompt}]}, timeout=60)
        print(f"  thinking-disabled probe: HTTP {raw.status_code}")
        if raw.status_code != 200:
            print("  body:", raw.text[:400])
        else:
            d = raw.json()
            print("  content blocks:", [b.get("type") for b in d.get("content", [])])
            print("  stop_reason:", repr(d.get("stop_reason")))
            print("  usage:", json.dumps(d.get("usage", {})))
        print()
        results["anthropic/thinking-disabled/64"] = attempt(
            "thinking disabled, max_tokens=64",
            lambda: R.call_anthropic("claude-sonnet-5", prompt, key, 64, thinking=False))
        results["anthropic/thinking-on/2048"] = attempt(
            "thinking default (on), max_tokens=2048",
            lambda: R.call_anthropic("claude-sonnet-5", prompt, key, 2048, thinking=True))
        print()

    # ---------------------------------------------------------------- openai
    key = os.environ.get("OPENAI_API_KEY", "")
    print("=" * 78); print("OPENAI  gpt-5.6-terra"); print("=" * 78)
    if not key:
        print("  OPENAI_API_KEY not set; skipping\n")
    else:
        import requests
        raw = requests.post("https://api.openai.com/v1/chat/completions",
                            headers={"Authorization": f"Bearer {key}",
                                     "content-type": "application/json"},
                            json={"model": "gpt-5.6-terra", "max_completion_tokens": 64,
                                  "messages": [{"role": "user", "content": prompt}]},
                            timeout=60)
        if raw.status_code == 200:
            d = raw.json()
            print("  choices[0]:"); print(show(d.get("choices", [{}])[0], 2))
            print("  usage:", json.dumps(d.get("usage", {})))
        else:
            print(f"  HTTP {raw.status_code}: {raw.text[:400]}")
        print()
        results["openai/64"] = attempt(
            "max_completion_tokens=64",
            lambda: R.call_openai("gpt-5.6-terra", prompt, key, 64))
        results["openai/2048"] = attempt(
            "max_completion_tokens=2048",
            lambda: R.call_openai("gpt-5.6-terra", prompt, key, 2048))
        print()

    # ---------------------------------------------------------------- google
    key = os.environ.get("GEMINI_API_KEY", "")
    print("=" * 78); print("GOOGLE  gemini-3.8-flash"); print("=" * 78)
    if not key:
        print("  GEMINI_API_KEY not set; skipping\n")
    else:
        import requests
        raw = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-3.8-flash:generateContent",
            headers={"x-goog-api-key": key, "content-type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"maxOutputTokens": 64}}, timeout=60)
        if raw.status_code == 200:
            d = raw.json()
            print("  candidates[0]:"); print(show(d.get("candidates", [{}])[0], 2))
            print("  usageMetadata:", json.dumps(d.get("usageMetadata", {})))
        else:
            print(f"  HTTP {raw.status_code}: {raw.text[:400]}")
        print()
        results["google/64"] = attempt(
            "maxOutputTokens=64",
            lambda: R.call_google("gemini-3.8-flash", prompt, key, 64))
        results["google/2048"] = attempt(
            "maxOutputTokens=2048",
            lambda: R.call_google("gemini-3.8-flash", prompt, key, 2048))
        print()

    print("=" * 78); print("SUMMARY"); print("=" * 78)
    for k, (ok, tok) in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {k:38s} tokens={tok}")
    print("\nA configuration only counts as usable if it PASSES. Do not start a sweep on a")
    print("configuration that failed here; that is what produced a 100%-error run.")


if __name__ == "__main__":
    main()
