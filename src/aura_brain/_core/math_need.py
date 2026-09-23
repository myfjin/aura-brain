#!/usr/bin/env python3
"""math_need.py — the Brain's front-door detector for "this needs exact math".

Step 1 of BRAIN-MATHBRAIN-CONNECTION.md. The call-graph proved node.step has NO
delegation hook — recognition fires reasoning-moves and has no notion of "this is a
computation." This is the missing eye: a cheap, deterministic classifier that spots an
explicit computation and hands the payload to the MathematicalBrain (mathbrain.solve).

It is deliberately NARROWER + cheaper than mathbrain.classify (which then picks the exact
sympy op). This only answers: *is there a computation here, what is it, and (maybe) what
operation is named?* No LLM, no sympy — pure regex.

Contract:
    math_need(text) -> Need(is_math, expression, op_hint, confidence)
      is_math     : route to mathbrain?  (True only when a real math expression is found)
      expression  : the math payload WITHOUT the verb (feed straight to mathbrain)
      op_hint     : solve|factor|simplify|expand|diff|integrate  or None (let mathbrain classify)
      confidence  : 0.9 verb+expr · 0.75 strong expr, no verb · 0.0 no route

HONEST SCOPE (v1 = explicit signals only):
  - Precision over recall: a math VERB alone does not fire ("expand the team",
    "factor in the cost") — an expression must be present. Implicit/word-problem math
    ("the sum of 2 and 3") is DEFERRED (Step 4 review queue tunes from real misses).
  - Guards the prose-number traps: IPs, times, versions, dates, and bare integer ranges
    ("10-20 minutes") do NOT fire.
  - Guards the prose-word traps (C1 miss-loop, 2026-07-05): operands must LOOK like math
    (numbers, 1-letter symbols, known function names) — "C++ and", "re-running", file
    paths, "edge. = real", and markdown ==== separators do NOT fire.
  - Guards the prose-CODE traps (L2 audit, 2026-07-25): measured against the real review
    queue, 516 of 531 pending rows (97.2%) were never math — dates, ISO timestamps, the
    mesh roster (6E+4Q), footprint codes (A4/A5/A6), progress counters (370/370). Five
    shape guards close it: see "shape guards" below. Ground truth + the teeth-proof live
    in math_gate_corpus.py; the before/after replay in math_gate_test.py.

Run: python3 math_need.py            # self-test (explicit math fires, prose doesn't)
     python3 math_need.py "solve x**2 - 5*x + 6 = 0"
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass


@dataclass
class Need:
    is_math: bool
    expression: str
    op_hint: str | None
    confidence: float

    def for_mathbrain(self) -> str:
        """Format the payload the way mathbrain._parse understands: 'op: expr' when an
        operation is named, else the bare expression."""
        return f"{self.op_hint}: {self.expression}" if self.op_hint else self.expression


# a math run = operand (operator operand)+ , operator is one-or-more of - + * / ^ =
# (so ** and other repeats are one operator). operands allow digits, vars, ., ().
_MATH_EXPR = re.compile(r"[\w.()]+(?:\s*[-+*/^=]+\s*[\w.()]+)+")

# named operations → mathbrain op. None = generic ("compute") → let mathbrain classify.
_VERB_OP = [
    (re.compile(r"\bfactor(?:ing|ize|ise|ed)?\b", re.I), "factor"),
    (re.compile(r"\bexpand(?:ing|ed)?\b", re.I), "expand"),
    (re.compile(r"\bsimplif(?:y|ies|ying|ied)\b", re.I), "simplify"),
    (re.compile(r"\bsolv(?:e|ing|ed|es)\b", re.I), "solve"),
    (re.compile(r"\b(?:differentiate|derivative|diff)\b", re.I), "diff"),
    (re.compile(r"\b(?:integrate|integral)\b", re.I), "integrate"),
    (re.compile(r"\b(?:compute|evaluate|calculate|calc)\b", re.I), None),
]

# ── shape guards (L2 audit, 2026-07-25) ──────────────────────────────────────
# A date is NOT a subtraction. v1 anchored this guard with ^...$, so it only ever saw a
# candidate that was EXACTLY a date — but the extractor hands over "(2026-07-23" and
# "2026-07-21)." and "2026-07-15T20", and every one of those walked straight past it.
# 216 of 531 queued rows were a date or an ISO timestamp. Unanchored, and it knows slashes.
_DATEISH = re.compile(r"""
      \d{4}\s*-\s*\d{1,2}\s*-\s*\d{1,2}        # 2026-07-15  (also the ...T20 slices)
    | \d{1,2}\s*-\s*\d{1,2}\s*-\s*\d{2,4}      # 15-07-26
    | \d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{2,4}      # 24/07/2026
    | \d{4}\s*/\s*\d{1,2}\s*/\s*\d{1,2}        # 2026/07/24
""", re.X)

# A scientific-notation literal is a NUMBER, not a computation — and its exponent sign is
# not an operator. Masking it first makes "1e-6" collapse to a bare number (no operator
# left → not a computation) while "2.5e-3 * x" keeps its real multiplication.
_SCI_LIT = re.compile(r"(?<![\w.])\d+(?:\.\d+)?[eE][-+]?\d+(?![\w.])")

# operands = what sits between operators and parens.
# A fenced code block is EXPOSITION, not a request. Measured on the live corpus: every
# expression inside one was a listing, a spec or a command — a directory tree ("r/ 60
# patterns"), a rule banning `abs(a-b) > eps` asserts, "the fraction of keys moved is ~1/N",
# "Beta, a/(a+b) [n=…]", `rustc --edition 2021 -D warnings`. Nobody asks the Brain to
# compute the contents of a listing they pasted. INLINE backticks are deliberately NOT
# stripped — measurement showed they carry real asks (`x**2 - 5*x + 6 = 0`, `sin(x/2)`,
# `acos(-1.0)`), so stripping them would be exactly the over-suppression this audit forbids.
_FENCE = re.compile(r"```.*?```", re.S)
_OPEN_FENCE = re.compile(r"```.*", re.S)      # an unclosed fence runs to end of turn

_OPERAND_SPLIT = re.compile(r"[-+*/^=()]+")
_ALNUM = re.compile(r"[0-9A-Za-z]")

# "2." is a legal float to sympy and a LIST MARKER to everyone else. Live specimen:
# "2. **I care" → the extractor read the markdown bold run as exponentiation.
_LIST_MARKER = re.compile(r"^\d+\.$")

# markdown bold vs exponentiation. A real power operator is spaced SYMMETRICALLY —
# "x**2" or "x ** 2". Markdown emphasis hugs its text on one side only: "s **23
# patterns**", ".13.** I care". Same family as the ==== separator guard v1 already carries.
_MD_BOLD = re.compile(r"\s\*\*\S|\S\*\*\s")

# A command-line flag, not a subtraction: " -D", " -o". Same asymmetric-spacing tell as
# markdown bold — a real minus is spaced symmetrically ("x - y") or not at all ("x-y"),
# while a flag hugs its letter. Fence-stripping already removes most of these (11 of 13 on
# the live corpus were inside code blocks); this catches the ones written inline, as in
# "the gate is `rustc -O --edition 2021 -D warnings`". Known collateral, accepted: the
# sloppily-spaced "x -y" no longer routes — "x - y" and "x-y" both still do.
_CLI_FLAG = re.compile(r"\s-[A-Za-z](?!\w)")

# words that legitimately appear inside a math expression (functions, constants).
# NOT here on purpose: "re" (sympy's re() — but in prose it's "re-running").
_MATH_WORDS = {"sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh",
               "exp", "log", "ln", "sqrt", "cbrt", "abs", "pi", "oo", "mod"}

# operator runs that are never math: ++/-- increments ("C++"), ===+ markdown separators,
# // C-style comment markers ("120     // A" — floor division loses, comments are commoner).
_CODE_RUN = re.compile(r"\+\+|--|===|//")


def _balanced(expr: str) -> bool:
    """Real expressions close their parentheses. An unbalanced run means the extractor
    sliced through prose — "(20/20", ")**2", "k=0)", "374 + R)". 29 queued rows."""
    depth = 0
    for ch in expr:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _is_code_token(tok: str) -> bool:
    """An operand mixing letters and digits is an IDENTIFIER, not a number: the mesh
    roster (4Q, 6E, 5S), footprint codes (A4, B2), percentiles (p50), build tags (w16,
    v15), durations (1h), octal/hex literals (0o777, 0x11E), timestamp slices (15T20).
    142 queued rows. Underscored names are exempt — x_2 is sympy's own subscript form,
    so subscripted variables stay routable when written the way sympy reads them."""
    return "_" not in tok and bool(re.search(r"[A-Za-z]", tok)) and bool(re.search(r"\d", tok))


# PROJECT VOCABULARY — a named list, NOT a shape rule, and it must stay honest about that.
# "a+r" is structurally indistinguishable from "a+b"; no regex can separate them, and any
# rule that tried would blind the gate to real algebra. What makes it junk is a fact about
# THIS corpus, so it is written down as a fact: measured on the live dialogue, "a+r" fires
# 16 times and is "aura-router" every single one.
#
# Exact WHOLE-expression match only (after whitespace and wrapper punctuation are dropped),
# so "a+r+1", "2*(a+r)" and every real expression merely CONTAINING these symbols still
# route. Re-measure before trusting this list against a different corpus; extend it only
# with the same evidence — a count from the live stream, never a hunch.
_ABBREVIATIONS = {"a+r"}


def _is_abbreviation(expr: str) -> bool:
    return re.sub(r"\s+", "", expr).strip("().") in _ABBREVIATIONS


_BARE_LITERAL = re.compile(r"^[\d.]+$")


def _is_tautology(expr: str) -> bool:
    """An equation with nothing to DO. "n=3", "p=0.89", "R² = 0.998", ".13=u" — a bare
    symbol bound to a bare literal. Solving it returns the number already typed.

    This is PARAMETER NOTATION in prose ("with n=3 samples", "p=0.89") and after the
    2026-07-25 shape guards it was the largest remaining fire class on the live corpus.
    The justification is structural, not stylistic — there is no operation to perform —
    so unlike the counter guard it fires even when a verb is present: "solve n = 3" is
    just as empty as "n = 3".

    An operation or a function call on EITHER side means real work, and is kept:
    "sin(x) = 0.5" (call), "n/2 = 8" (operation), "b = a+b+1", "y=x²" all survive.
    Living in _looks_math means a rejected "n = 3" merely drops out of the candidate
    list — so "let n = 3, then compute n**2" still routes, on n**2."""
    e = expr.strip()
    while e.startswith("(") and e.endswith(")") and _balanced(e[1:-1]):
        e = e[1:-1].strip()
    sides = re.split(r"=+", e)
    if len(sides) != 2:
        return False
    sides = [s.strip() for s in sides]
    if any((not s) or re.search(r"[-+*/^()]", s) for s in sides):
        return False
    return any(_BARE_LITERAL.match(s) for s in sides)


def _looks_math(expr: str) -> bool:
    """Operand sanity: every alphabetic run must be a 1-letter symbol or a known math
    word — prose words ("and", "running", path segments) disqualify the candidate.
    Operator sanity: ++/--/===/// runs are code/markdown, never math.
    Shape sanity (2026-07-25): dates, line-crossing runs, unbalanced parens, identifier
    operands, and float-literal-only "operators" are never a computation."""
    if "\n" in expr:
        return False            # the run crossed a line boundary → prose, not an expression
    if _CODE_RUN.search(expr):
        return False
    if _MD_BOLD.search(expr) or _CLI_FLAG.search(expr):
        return False
    if _DATEISH.search(expr):
        return False
    if not _balanced(expr):
        return False
    if _is_tautology(expr):
        return False
    if _is_abbreviation(expr):
        return False
    expr = _SCI_LIT.sub("0", expr)          # a float literal is one number, not an operation
    if not re.search(r"[-+*/^=]", expr):
        return False            # the only "operator" was a scientific-notation sign ("1e-6")
    # empty splits are just paren boundaries ("(x + 1)/(x - 1)") — the unbalanced-paren
    # guard above already owns the sliced-fragment case, so only NON-empty operands are judged.
    for tok in (t.strip() for t in _OPERAND_SPLIT.split(expr)):
        if not tok:
            continue
        if not _ALNUM.search(tok):
            return False        # punctuation-only operand ("r/...")
        if _is_code_token(tok):
            return False
        if _LIST_MARKER.match(tok):
            return False        # "2." before a markdown bold run — list numbering, not a float
    letters = re.findall(r"[A-Za-z]+", expr)
    # SELF-AWARENESS seed (2026-07-10, mechanism #2): a lone op between bare single
    # UPPERCASE letters with NO digit is a prose ABBREVIATION (A/B test, I/O, R/W, Q&A),
    # not a computation. Live specimen: "A/B" → MathBrain "solved" it to [(0,B)]. Kept
    # targeted (loud-first, don't over-suppress): lowercase single letters (x/y) and any
    # digit keep it routable — this only kills the uppercase-abbreviation false positive.
    if letters and all(len(w) == 1 and w.isupper() for w in letters) and not re.search(r"\d", expr):
        return False
    return all(len(w) == 1 or w.lower() in _MATH_WORDS for w in letters)


# How far before the expression a request-verb may sit. Measured, not guessed: every
# positive control reads "<verb> ... <expr>" within 26 characters ("what is the derivative
# of x**2 + 3*x" is the longest), so 48 clears them all with margin.
_VERB_WINDOW = 48


def _detect_verb(text: str, expr: str = ""):
    """Return (verb_found, op_hint). First matching operation wins.

    PROXIMITY (L2 audit, 2026-07-25): the verb must sit NEAR the expression, on the same
    line. v1 searched the WHOLE turn, so a paragraph mentioning "diff" and a later
    paragraph containing "10/10" combined into a 0.9-confidence "differentiate this" —
    and 0.9 outranks every shape guard. Measured on the live dialogue corpus, whole-turn
    verb matching was the single largest remaining false-positive source. "solve",
    "diff", "expand", "factor" and "compute" are ordinary English; only their ADJACENCY
    to an expression makes them a request."""
    windows, i = [], text.find(expr) if expr else -1
    while i >= 0:                   # EVERY occurrence, not just the first: a turn can
        line_start = text.rfind("\n", 0, i) + 1     # mention "250 / 370" in passing and
        windows.append(text[max(line_start, i - _VERB_WINDOW):i + len(expr)])
        i = text.find(expr, i + 1)                  # then ask to compute it a line later
    for rx, op in _VERB_OP:         # first matching OPERATION wins, as in v1
        if any(rx.search(w) for w in (windows or [text])):
            return True, op
    return False, None


def _strip_code_blocks(text: str) -> str:
    """Fenced blocks out, replaced by a newline so no run is glued across the boundary."""
    return _OPEN_FENCE.sub("\n", _FENCE.sub("\n", text))


def _extract_expr(text: str) -> str:
    """Longest math run in the text, minus date-shaped and prose-shaped false positives."""
    cands = [c.strip() for c in _MATH_EXPR.findall(text)]
    cands = [c for c in cands if _looks_math(c)]     # _looks_math now owns the date guard
    return max(cands, key=len) if cands else ""


def _is_bare_number_run(expr: str) -> bool:
    """No symbol anywhere — every operand is a literal. In a dialogue stream that is a
    progress counter (370/370), a score list (0.40 / 0.29 / 0.28), a CIDR (10.200.200.0/24)
    or a build id, never a question. 125 queued rows were counters alone. This fires only
    on the NO-VERB path: "compute 250 / 370" still routes, because an explicit verb is an
    explicit request and outranks any shape heuristic."""
    return not re.search(r"[A-Za-z]", _SCI_LIT.sub("0", expr))


def _is_strong(expr: str) -> bool:
    """A strong expression carries a math signal beyond a single +/- between integers
    (which is usually a range/date/phone in prose). Strong = a variable, an '=', a
    mul/div/pow operator, or two or more operators."""
    return bool(
        re.search(r"[A-Za-z]", expr)          # a variable/symbol
        or "=" in expr                          # an equation
        or re.search(r"\*\*|[*/^]", expr)      # multiplication / division / power
        or len(re.findall(r"[-+*/^=]+", expr)) >= 2
    )


def math_need(text: str) -> Need:
    if not text or not text.strip():
        return Need(False, "", None, 0.0)
    text = _strip_code_blocks(text)     # before extraction AND before verb detection: a
                                        # verb inside a code listing is not a request either
    expr = _extract_expr(text)
    if not expr:
        return Need(False, "", None, 0.0)          # no expression → never route (kills "expand the team")
    verb_found, op = _detect_verb(text, expr)
    if verb_found:
        return Need(True, expr, op, 0.9)            # explicit op named + a real expression
    if _is_bare_number_run(expr):
        return Need(False, "", None, 0.0)           # counter/ratio/id in prose, nothing asked
    if _is_strong(expr):
        return Need(True, expr, None, 0.75)         # unmistakable expression, no verb
    return Need(False, "", None, 0.0)               # weak (bare int +/- int) → defer, don't guess


# ── self-test: explicit math must fire; prose must not ─────────────────────────
_POS = [
    ("solve x**2 - 5*x + 6 = 0", "solve"),
    ("factor: x**3 - 1", "factor"),
    ("please expand (a + b)**2", "expand"),
    ("simplify (x**2 - 1)/(x - 1)", "simplify"),
    ("what is the derivative of x**2 + 3*x", "diff"),
    ("integrate x**2 dx", "integrate"),
    ("compute 2 + 2*3", None),                       # generic verb → op_hint None
    ("x**2 - 5*x + 6 = 0", None),                    # strong expr, no verb
    ("(x + 1)/(x - 1)", None),                        # strong expr, no verb
    ("exp(x) + sin(x) = x**3", None),                # math words stay routable
    ("sin(x) = 0.5", None),                           # math words stay routable
]
_NEG = [
    "they keep misunderstanding what I mean",
    "explain me your understanding of aura so we align",
    "let's meet at 8:19 pm",
    "the node is at 172.20.10.5",
    "we shipped on 2026-07-01",
    "python 3.11 runs the daemon",
    "give me 10-20 minutes to understand",           # range, not math
    "expand the team and factor in the cost",        # verbs but NO expression
    "I have 2 projects and 3 goals",                 # numbers, no operator
    # the wild false-positive class (math_misses.jsonl, graded 2026-07-05):
    "C++ and Python twins shipped",                  # ++ is code, not addition
    "re-running the sweep tomorrow",                 # hyphenated word, not subtraction
    "brother.\n\n==========================\nhypothesis",  # markdown separator, not equation
    "edge. = real",                                  # prose =, operands are words
    "S1. - what did we leave off",                   # prose -, operands are words
    "card at team/notes/PROBE-COMPACTION.md.",              # path, not division
    "the organ/operator split",                      # prose /, operands are words
    "memories = each moment we shared",              # prose =, operands are words
]


def _selftest() -> int:
    ok = 0
    total = len(_POS) + len(_NEG)
    print("POSITIVE (must fire, op_hint must match):")
    for text, exp_op in _POS:
        n = math_need(text)
        good = n.is_math and n.op_hint == exp_op
        ok += good
        print(f"  {'OK ' if good else 'XX '} is_math={n.is_math!s:5} op={str(n.op_hint):9} "
              f"conf={n.confidence}  expr={n.expression!r}  <= {text!r}")
    print("\nNEGATIVE (must NOT fire):")
    for text in _NEG:
        n = math_need(text)
        good = not n.is_math
        ok += good
        print(f"  {'OK ' if good else 'XX '} is_math={n.is_math!s:5}  expr={n.expression!r}  <= {text!r}")
    print(f"\naccuracy: {ok}/{total} = {100 * ok // total}%")
    return ok == total


def main():
    if len(sys.argv) < 2:
        raise SystemExit(0 if _selftest() else 1)
    n = math_need(" ".join(sys.argv[1:]))
    print(f"is_math    : {n.is_math}")
    print(f"expression : {n.expression!r}")
    print(f"op_hint    : {n.op_hint}")
    print(f"confidence : {n.confidence}")
    print(f"→ mathbrain: {n.for_mathbrain()!r}" if n.is_math else "→ (not routed)")


if __name__ == "__main__":
    main()
