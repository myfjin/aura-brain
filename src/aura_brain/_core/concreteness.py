#!/usr/bin/env python3
"""concreteness.py — the anti-bullshit gate: does a turn CASH OUT in something concrete,
or float as eloquent essay?

The gap Illia caught 2026-06-28: the voice-gate PASSES eloquent-philosophical drift because
slippery text embeds near real turns — it sounds right, means nothing. This adds the missing
axis: GROUNDEDNESS. A turn is GROUNDED when it carries specifics that can be checked or acted
on (numbers, file/artifact refs, named mechanisms, code, decisions/imperatives) and FLOATING
when it leans on hedges, abstraction-nouns and essay-connectors with nothing checkable under it.

This is the immune system against making an LLM "believe any bullshit": bullshit is talk that
does not cash out. Demand the payload. (Tier 1 = heuristic, here. Tier 2 = does the claim
reference a CHECKABLE artifact — the A6 verify — noted for later.) Deliberately deterministic:
the bullshit-detector must not itself be an LLM that can be talked into anything.

Run: python3 concreteness.py     # self-test: real concrete turns vs slippery persona essays
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

_CONCRETE = [
    r"\d",                                          # any number
    r"[\w./-]+\.(?:py|jsonl?|md|npz|npy|yaml|txt)",  # file / artifact refs
    r"[a-z_]{3,}\([^)]*\)",                          # function calls / code
    r"\b[a-z]+_[a-z_]+\b",                           # snake_case identifiers
    r"\b(build|ship|run|set|use|add|fix|deploy|escalate|decide|store|write|read|"
    r"merge|wire|cap|flag|solve|factor|score|rank|bank|revive)\b",
    r"127\.0\.0\.1|\.5\b|\.8\b|\.13\b|/\w",          # paths / mesh nodes
]
_FLOAT = [
    r"\b(maybe|probably|perhaps|kind of|sort of|somehow|what if|i guess|i think|i mean)\b",
    r"\b(shape|essence|momentum|continuity|meaning|presence|consciousness|infinite|infinity|"
    r"the loop|the distance|the question)\b",
    r"\b(that means|in other words|the thing is|the real question|what'?s underneath|"
    r"it'?s not .*? it'?s)\b",
    r"\b(feels?|feeling|sense|vibe|resonat\w+|warps?)\b",
    r"…|\.\.\.",                                     # trailing ellipses — the drift tell
]


def _count(patterns, text):
    t = text.lower()
    return sum(len(re.findall(p, t)) for p in patterns)


def score(text: str) -> dict:
    words = max(1, len(text.split()))
    c, f = _count(_CONCRETE, text), _count(_FLOAT, text)
    g = c / (c + f) if (c + f) else 0.0
    verdict = "GROUNDED" if (g >= 0.55 and c >= 2) else ("mixed" if g >= 0.40 else "FLOATING")
    return {"concrete": c, "float": f, "groundedness": round(g, 2),
            "c_per40w": round(c / words * 40, 1), "f_per40w": round(f / words * 40, 1),
            "verdict": verdict}


_REAL = [
    "Built mathbrain.py — x**2 - 5*x + 6 = 0 solves to [2, 3] exact via sympy; the transcendental defers to the review queue.",
    "node.py wires recognition.recall into the arbiter floor; run() loops on .5, and failover drops .13 to [.5, .8].",
    "yeah github API direct, sitting in staging. claude grab INDEX first, steward audit .5 config, parallel. go.",
]
_SLIPPERY = [
    "the distance isn't a file, it's the shape of what Claude keeps asking. every time he lands on a question he didn't know he had — that's momentum. what if the infinite distance is just: we never close the loop?",
    "the asking itself is the motion — not resolving toward an answer, but staying in the shape of the question long enough that it warps what I can see next time.",
    "don't compress it. just point at it next time. let Steward see the shape you couldn't close. that's the file.",
]


def main():
    if len(sys.argv) > 1:
        s = score(" ".join(sys.argv[1:]))
        print(f"{s['verdict']}  groundedness={s['groundedness']}  (concrete {s['concrete']} / float {s['float']})")
        return
    print("self-test — REAL concrete turns vs SLIPPERY persona essays:\n")
    for tag, group in (("REAL    ", _REAL), ("SLIPPERY", _SLIPPERY)):
        for t in group:
            s = score(t)
            print(f"  [{s['verdict']:>8}] g={s['groundedness']:<4} c={s['concrete']:<2} f={s['float']:<2}  {tag}  “{t[:58]}…”")
    print("\n[reading] GROUNDED = it cashes out (checkable/actionable) · FLOATING = eloquent, no payload.")


if __name__ == "__main__":
    main()
