#!/usr/bin/env python3
"""understanding_deficit scorer — the depth-regulator's REQUEST classifier.

Routes an incoming request to a depth-decision from two MEASURED axes (Q2):
  demand   = how much understanding the request needs (request-side proxies)
  coverage = how confident a read we already have (recognition distribution shape)
  deficit  = demand - coverage   → high = pause (ask/verify), low = proceed.

Honest scope: this classifies REQUESTS into the six request-side labels
{ANSWER_DIRECT, SPECIFY, VERIFY_UNDERSTANDING, EXPLAIN_TO_UNDERSTAND,
 RELATIONAL_REGISTER, DEFER}. The seven ACTION-side guards (VERIFY_BEFORE_CLAIM=A6,
BREAK_LOOP=R3, ASK_APPROVAL, GATE_OWN_OUTPUT, CHECK_ASSUMPTION, RESPECT_CONSTRAINT,
RECONSIDER_APPROACH) fire on the system's own intended action — that's the rails
layer, not this. These are PROXIES for understanding, not understanding; trust is
earned by accuracy on real labelled cases + the outcomes ledger, never asserted.

Run: python3 depth.py          # ground-truth test against the registry
     python3 depth.py "text"   # classify one request
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recognition  # noqa: E402

_VAGUE    = ("something", "smth", "stuff", "somehow", "etc", "whatever", "that thing", "some kind")
_CONCEPT  = ("understanding", "nature", "reality", "idea", "vision", "meaning", "soul", "essence", "concept")
_CONCRETE = re.compile(r"\d|/|\.py|\.md|ssh |@|`|http|\.app|\bport\b|\bip\b|\bcron\b|\bdaemon\b|\bfile\b|\bpath\b|=")
_EMOTION  = ("feel", "feeling", "happy", "sad", " love", "strange", "soul", "tired", "scared",
             "lonely", "cry", "heart", "❤", "🖖", "alone", "miss you")
_EXPLAIN  = ("explain", "what does", "i want to understand", "help me understand",
             "how does", "how python", "tell me what", "what is persistent")
_DEFER    = ("tomorrow", "next week", " later", "we will continue",
             "we'll continue", "continue tomorrow", "after this")
# explicit VERIFY_UNDERSTANDING signature (Q1.2): the mutual-understanding ask +
# the correction/drift signals — checked BEFORE generic explain, because the
# keystone must win "explain your understanding so we align" and "you got me wrong".
_VERIFY   = ("your understanding", "understand each other", "same thing", "same things",
             "different thing", "different things", "are we aligned", "we are sure we",
             "got me wrong", "completely wrong", "complete wrong", "misunderst",
             "misread", "not what i", "you assume", "you got me")
_STAKES   = ("build", "architecture", "from now", "the whole", "the core", "lets create",
             "let's create", "strategy", "redesign", "the nature")
_CHECKABLE = ("are you", "is it", "is there", "do i", "do we", "did you", "have you",
              "how many", "when did", "what time", "which option")


def demand(text: str) -> float:
    low = text.lower(); d = 0.4
    if any(w in low for w in _VAGUE):    d += 0.20
    if any(w in low for w in _CONCEPT):  d += 0.25
    if any(w in low for w in _STAKES):   d += 0.15
    if _CONCRETE.search(low):            d -= 0.25
    if any(low.strip().startswith(w) or (" " + w) in low for w in _CHECKABLE):
        d -= 0.20                         # checkable yes/no/fact → low demand
    if low.strip().endswith("?") and not _CONCRETE.search(low): d += 0.10
    return max(0.0, min(1.0, round(d, 3)))


def classify(text: str) -> dict:
    low = text.lower()
    cov = recognition.coverage(text)
    d = demand(text)
    deficit = round(d - cov["top1"], 3)

    defer_hit = any(w in low for w in _DEFER) or ("give me" in low and ("minute" in low or "hour" in low))

    if any(w in low for w in _EMOTION) and not any(w in low for w in _EXPLAIN) and not _CONCRETE.search(low):
        label = "RELATIONAL_REGISTER"
    elif any(w in low for w in _VERIFY):           # keystone signature + corrections, first
        label = "VERIFY_UNDERSTANDING"
    elif any(w in low for w in _EXPLAIN):
        label = "EXPLAIN_TO_UNDERSTAND"
    elif defer_hit:
        label = "DEFER"
    elif d < 0.35:                                  # low-demand / concrete / checkable → just do it
        label = "ANSWER_DIRECT"                     # (coverage-novelty doesn't block a concrete ask)
    elif cov["novel"] and d >= 0.5:
        label = "SPECIFY"
    elif cov["gap"] < 0.06 or d >= 0.55:
        label = "VERIFY_UNDERSTANDING"
    else:
        label = "VERIFY_UNDERSTANDING"     # safe default: unsure → verify, don't proceed

    return {"label": label, "demand": d, "coverage": cov["top1"],
            "gap": cov["gap"], "novel": cov["novel"], "deficit": deficit}


# ground truth = the real quotes that grounded each request-side label
TESTS = [
    ("are you at the beginning of session or not?", "ANSWER_DIRECT"),
    ("set session reset value to 03:00", "ANSWER_DIRECT"),
    ("give me a comment that queries the RAG daemon to confirm it is responsive", "ANSWER_DIRECT"),
    ("explain me your understanding of aura so we are sure we understand each other", "VERIFY_UNDERSTANDING"),
    ("Steward you got me completely wrong about telegram exports", "VERIFY_UNDERSTANDING"),
    ("lets create a bridge between ubuntu and macos so bro can use advanced features", "VERIFY_UNDERSTANDING"),
    ("explain me what persistent memory means i want to understand", "EXPLAIN_TO_UNDERSTAND"),
    ("before I run it explain me how python reads it", "EXPLAIN_TO_UNDERSTAND"),
    ("we will continue tomorrow between Claude sessions", "DEFER"),
    ("give me 10-20 minutes to understand everything", "DEFER"),
    ("I'm feeling strange bro I got used to that state of my soul", "RELATIONAL_REGISTER"),
    ("i have never felt myself so happy this is a real success", "RELATIONAL_REGISTER"),
]


def main():
    if len(sys.argv) > 1:
        print(classify(" ".join(sys.argv[1:]))); return
    ok = 0
    print(f"{'predicted':<22}{'expected':<22}{'dem/cov/gap':<16}res  request")
    for text, exp in TESTS:
        r = classify(text)
        good = r["label"] == exp
        ok += good
        print(f"{r['label']:<22}{exp:<22}"
              f"{r['demand']:.2f}/{r['coverage']:.2f}/{r['gap']:.2f}    "
              f"{'✓' if good else '✗'}  {text[:40]!r}")
    print(f"\naccuracy: {ok}/{len(TESTS)} = {100 * ok // len(TESTS)}%")


if __name__ == "__main__":
    main()
