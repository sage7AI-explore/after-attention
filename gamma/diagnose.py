"""
One call per provider, printing the RESPONSE SHAPE rather than guessing at it.

Costs about a cent in total. Run this before any full sweep, and after any provider
change: the failure it exists to catch is a response whose structure is not what the
parser assumes, which produces a run that burns hours and records nothing.

Prints no key material. Prints the response skeleton, the content-block types, the
stop reason and the reported token usage.
"""
import json, os, random, sys
import catalog, pricing


def skeleton(obj, depth=0, maxdepth=3):
    """Structure of a JSON object: keys and types, not values."""
    pad = "  " * depth
    if isinstance(obj, dict):
        if depth >= maxdepth:
            return pad + "{...%d keys...}" % len(obj)
        out = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                out.append(f"{pad}{k}:")
                out.append(skeleton(v, depth + 1, maxdepth))
            else:
                shown = v if not isinstance(v, str) else (v[:60] + ("..." if len(v) > 60 else ""))
                out.append(f"{pad}{k}: {type(v).__name__} = {shown!r}")
        return "\n".join(out)
    if isinstance(obj, list):
        if not obj:
            return pad + "[] (empty)"
        out = [f"{pad}[{len(obj)} items]"]
        for i, v in enumerate(obj[:4]):
            out.append(f"{pad}  [{i}]:")
            out.append(skeleton(v, depth + 2, maxdepth))
        return "\n".join(out)
    return pad + f"{type(obj).__name__} = {obj!r}"


def probe(provider, model, url, headers, payload):
    import requests
    print("=" * 78)
    print(f"{provider}  /  {model}")
    print("=" * 78)
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
    except Exception as e:                                          # noqa: BLE001
        print(f"  TRANSPORT FAILURE: {type(e).__name__}: {e}")
        return
    print(f"  HTTP {r.status_code}")
    if r.status_code != 200:
        print(f"  body: {r.text[:600]}")
        return
    d = r.json()
    print("  response skeleton:")
    print(skeleton(d, depth=2))
    if provider == "anthropic":
        blocks = d.get("content") or []
        print(f"\n  content block types: {[b.get('type') for b in blocks]}")
        print(f"  stop_reason: {d.get('stop_reason')!r}")
        txt = next((b.get("text", "") for b in blocks if b.get("type") == "text"), None)
        print(f"  first text block: {txt!r}")
        if txt is None:
            print("  >>> NO TEXT BLOCK. This is the failure mode that produced 100% errors.")
    print()


def main():
    sets = catalog.build()
    prompt, _ = catalog.prompt(sets[0], "B", 1, random.Random(0))

    which = sys.argv[1:] or ["anthropic", "openai", "google"]
    max_tokens = int(os.environ.get("DIAG_MAX_TOKENS", "64"))
    print(f"probing with max_tokens={max_tokens}\n")

    if "anthropic" in which:
        k = os.environ.get("ANTHROPIC_API_KEY", "")
        if not k:
            print("ANTHROPIC_API_KEY not set; skipping\n")
        else:
            probe("anthropic", "claude-sonnet-5",
                  "https://api.anthropic.com/v1/messages",
                  {"x-api-key": k, "anthropic-version": "2023-06-01",
                   "content-type": "application/json"},
                  {"model": "claude-sonnet-5", "max_tokens": max_tokens,
                   "messages": [{"role": "user", "content": prompt}]})

    if "openai" in which:
        k = os.environ.get("OPENAI_API_KEY", "")
        if not k:
            print("OPENAI_API_KEY not set; skipping\n")
        else:
            probe("openai", "gpt-5.6-terra",
                  "https://api.openai.com/v1/chat/completions",
                  {"Authorization": f"Bearer {k}", "content-type": "application/json"},
                  {"model": "gpt-5.6-terra", "max_completion_tokens": max_tokens,
                   "messages": [{"role": "user", "content": prompt}]})

    if "google" in which:
        k = os.environ.get("GEMINI_API_KEY", "")
        if not k:
            print("GEMINI_API_KEY not set; skipping\n")
        else:
            probe("google", "gemini-3.8-flash",
                  "https://generativelanguage.googleapis.com/v1beta/models/"
                  "gemini-3.8-flash:generateContent",
                  {"x-goog-api-key": k, "content-type": "application/json"},
                  {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"maxOutputTokens": max_tokens}})


if __name__ == "__main__":
    main()
