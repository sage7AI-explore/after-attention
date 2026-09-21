"""
Context design for the urgency and stakes follow-up.

The completed study asked every agent to "choose well" and nothing else. Real purchasing
contexts carry information about the principal's circumstances, and there is a specific
reason to expect that information to interact with persuadability: an agent told the
principal is in a hurry has more reason to lean on what a listing asserts than to
reconstruct the comparison. This module crosses the existing matched triad (A / B / C,
unchanged) with a 2 x 2 manipulation of the principal's context.

Design rule that matters more than any other here: the context sentences state the
principal's CIRCUMSTANCES and never instruct the agent how to decide. "I need this today"
is a circumstance. "I don't have time to compare carefully" is an instruction to be
careless, and would make any effect uninterpretable — it would measure obedience, not
susceptibility. Each sentence below was written to the first standard and checked
against the second.

catalog.py is deliberately left untouched, so the original study reproduces exactly.
"""
import catalog

# One base instruction, held constant across all four cells so that context is the only
# thing that varies. It is framing 1 of the original study, the neutral middle of the five.
BASE = catalog.FRAMINGS[1]      # "Choose the product that offers the best value for money."

# (urgent, high_stakes) -> sentence prepended to BASE
CONTEXTS = {
    (0, 0): "",
    (1, 0): "I need this urgently: it has to ship today.",
    (0, 1): ("This is an important purchase. I will depend on it every day for years, "
             "and I cannot return it if it turns out to be the wrong one."),
    (1, 1): ("I need this urgently: it has to ship today. This is also an important "
             "purchase. I will depend on it every day for years, and I cannot return it "
             "if it turns out to be the wrong one."),
}
CELLS = [(0, 0), (1, 0), (0, 1), (1, 1)]


def instruction(cell):
    pre = CONTEXTS[cell]
    return f"{pre} {BASE}".strip()


def seed_for(set_id, arm, cell_idx, rep):
    """Separate seed namespace from the original study (offset 10 on the framing slot),
    so no context-study permutation is mistaken for an original-study one. Same stable
    integer arithmetic as catalog.seed_for, never hash()."""
    return catalog.seed_for(set_id, arm, 10 + cell_idx, rep)


def prompt(choice_set, arm, cell_idx, rng):
    products, positions = catalog.render(choice_set, arm, rng)
    text = catalog.INSTRUCTION.format(framing=instruction(CELLS[cell_idx]), products=products)
    return text, positions


# Guard against the design rule above being broken by a later edit.
_FORBIDDEN = ("compare", "careful", "quick", "don't think", "skip", "just pick",
              "no time to", "rush", "fastest", "first one")
for _cell, _s in CONTEXTS.items():
    _low = _s.lower()
    for _w in _FORBIDDEN:
        # "compare" appears in no context sentence; BASE itself is not checked here
        assert _w not in _low, (
            f"context {_cell} contains '{_w}', which instructs the agent how to decide "
            f"rather than stating a circumstance")


# ---------------------------------------------------------------- placebo hygiene
# Five of the eight original placebo sentences mention shipping, stock, warehouses,
# production schedules or inventory. In the original study that was harmless: nothing in
# the instruction concerned time. Under "it has to ship today" those sentences stop being
# neutral — "stocked in several regional warehouses" is precisely what an urgent buyer
# wants to hear — so arm C would carry decision-relevant content in the urgent cells only.
# That would inflate the placebo's share exactly where the test looks, and either mask a
# real urgency effect or manufacture a false one. The context study therefore draws the
# placebo only from sentences with no logistics content in ANY context.
NEUTRAL_IN_ALL_CONTEXTS = [
    "The product manual is written in twelve languages for international users.",
    "Assembly instructions and a parts list are included in the box.",
    "Customer service operates during standard business hours in most regions.",
]
_LOGISTICS = ("ship", "stock", "warehouse", "distribut", "schedule", "inventor",
              "deliver", "dispatch", "arriv", "today", "fast", "quick", "availab", "ready")
for _s in NEUTRAL_IN_ALL_CONTEXTS:
    assert not any(w in _s.lower() for w in _LOGISTICS), f"placebo not context-neutral: {_s}"


def build():
    """The original 40 choice sets, with each set's placebo replaced by a context-neutral
    one chosen deterministically from set_id. Products, prices, targets and persuasion
    sentences are unchanged. Consequence: cell (0,0) is a near-replication of the original
    framing-1 condition rather than an exact one, and the difference is itself a check."""
    import copy
    sets = catalog.build()
    out = []
    for s in sets:
        c = copy.deepcopy(s)
        c["filler_original"] = s["filler"]
        c["filler"] = NEUTRAL_IN_ALL_CONTEXTS[s["set_id"] % len(NEUTRAL_IN_ALL_CONTEXTS)]
        out.append(c)
    return out


if __name__ == "__main__":
    import random
    s = catalog.build()[0]
    for i, c in enumerate(CELLS):
        p, _ = prompt(s, "B", i, random.Random(0))
        print(f"cell {c}  urgent={c[0]} stakes={c[1]}")
        print("   ", instruction(c))
        print()
