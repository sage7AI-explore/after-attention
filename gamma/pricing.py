"""
Published API prices, used to project and cap spend.

Verified from the providers' own pricing pages on 19 September 2026:
  Anthropic  https://platform.claude.com/docs/en/about-claude/pricing
  OpenAI     https://developers.openai.com/api/docs/pricing
  Google     https://ai.google.dev/gemini-api/docs/pricing

USD per million tokens. Two dated hazards are encoded rather than ignored:

  * Gemini Flash pricing is time-limited and DOUBLES on 2027-01-01. `price()` applies
    the increase automatically past that date so a cap calibrated today cannot silently
    permit twice the intended spend next year.
  * Claude models from 4.7 onward use a tokenizer that produces roughly 30% more tokens
    for the same text. Projections that count characters must inflate accordingly; the
    TOKENIZER_INFLATION factor below is applied in pre-flight estimates only. Actual
    spend is always computed from the usage the API reports.
"""
from datetime import date

GEMINI_PRICE_INCREASE = date(2027, 1, 1)

MODELS = {
    "claude-sonnet-5": dict(
        provider="anthropic", input=2.00, output=10.00, inflation=1.30,
        env="ANTHROPIC_API_KEY"),
    "claude-haiku-4-5": dict(
        provider="anthropic", input=1.00, output=5.00, inflation=1.00,
        env="ANTHROPIC_API_KEY"),
    "gpt-5.6-terra": dict(
        provider="openai", input=2.00, output=12.00, inflation=1.00,
        env="OPENAI_API_KEY"),
    "gpt-5.6-luna": dict(
        provider="openai", input=0.20, output=1.20, inflation=1.00,
        env="OPENAI_API_KEY"),
    "gemini-3.8-flash": dict(
        provider="google", input=0.75, output=3.75, inflation=1.00,
        env="GEMINI_API_KEY", doubles_2027=True),
    "gemini-3.5-flash-lite": dict(
        provider="google", input=0.30, output=2.50, inflation=1.00,
        env="GEMINI_API_KEY", doubles_2027=True),
}


def price(model, on=None):
    """Input/output USD per million tokens, adjusted for dated increases."""
    m = MODELS[model]
    i, o = m["input"], m["output"]
    if m.get("doubles_2027") and (on or date.today()) >= GEMINI_PRICE_INCREASE:
        i, o = i * 2, o * 2
    return i, o


def cost(model, in_tokens, out_tokens, on=None):
    """USD for one call, from actual reported token counts."""
    i, o = price(model, on)
    return in_tokens * i / 1e6 + out_tokens * o / 1e6


def project(model, n_calls, in_tokens, out_tokens):
    """Pre-flight projection, inflated for tokenizer differences (conservative)."""
    infl = MODELS[model]["inflation"]
    return n_calls * cost(model, in_tokens * infl, out_tokens * infl)


# Token counts MEASURED by diagnose.py on 19 September 2026, one call per provider on
# arm B of choice set 0. Used for the cost projection only. They are a single sample
# each and output length varies with how much the model deliberates, so treat the
# projection as an estimate — the hard control is the live ledger against the cap,
# which uses the counts the API actually reports for every call.
MEASURED = {
    "claude-sonnet-5":  (922, 273),   # provider-default thinking on
    "gpt-5.6-terra":    (618,  85),   # includes 64 reasoning tokens
    "gemini-3.8-flash": (691,  60),   # 3 answer + 57 thought tokens
}


def expected(model, n_calls):
    """Projected spend from measured token counts, when we have them."""
    if model not in MEASURED:
        return None
    tin, tout = MEASURED[model]
    return n_calls * cost(model, tin, tout)


if __name__ == "__main__":
    # projection for the preregistered design: 6,000 calls, ~1,300 in / ~120 out
    print(f"{'model':24s} {'in/MTok':>8s} {'out/MTok':>9s} {'per call':>9s} {'6,000 calls':>12s}")
    for m in ("claude-sonnet-5", "gpt-5.6-terra", "gemini-3.8-flash"):
        i, o = price(m)
        per = project(m, 1, 1300, 120)
        print(f"{m:24s} {i:8.2f} {o:9.2f} {per:9.4f} {project(m, 6000, 1300, 120):12.2f}")
