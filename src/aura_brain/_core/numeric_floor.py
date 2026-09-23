#!/usr/bin/env python3
"""numeric_floor.py — the FRAME-RELATIVE numeric floor (Step 3: where mathbrain earns organ-hood).

A6/whypass asks of a truth-claim: "checked or claimed?" This asks it of a *computed*
claim: "does this number hold — and under WHICH frame?"

The design principle (Illia, 2026-07-01, sparked by Radiohead's "2+2=5"):
  A computed claim is only true RELATIVE TO A FRAME — the operators/base/rounding in force.
  Standard arithmetic is NOT "the truth"; it is the DEFAULT frame, one entry among many.
  So this floor NEVER returns "false". It returns, three-valued:
    HOLDS          — recomputes to the claim under the given frame.
    DOESNT_HOLD    — differs under the given frame (and any known frame) → it does NOT say
                     "lie"; it says "name the frame you mean (operator/base/rounding), or fix it."
    CANT_EVALUATE  — not a recomputable arithmetic assertion → defer, don't force.

Why never "false": if the floor declared "2+2=5 is false" it would be assuming standard
arithmetic without knowing the author's frame — not-knowing + not-asking + asserting the
convenient version = the LIE, committed by the organ built to catch lies. So it flags the
GAP (the unstated frame), never the verdict.

The guard that keeps frame-relativity from dissolving the floor ("everything's true under
SOME frame"): a frame must be DECLARED and RUNNABLE. "Some frame" is not a frame. A frame
enters the library only when its own formula EXECUTES and yields its witness — the same
run-gate as mathbrain's sympy floor and the harvester's __main__ gate. You may extend the
truth infinitely; each extension just has to compute.

Run: python3 numeric_floor.py        # self-test (incl. the Radiohead frame where 2+2=5)
"""
from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass

# ── verdicts ───────────────────────────────────────────────────────────────
HOLDS = "HOLDS"
DOESNT_HOLD = "DOESNT_HOLD"        # → name/teach the frame, or fix it (NEVER "false")
CANT_EVALUATE = "CANT_EVALUATE"    # not a recomputable arithmetic assertion → defer


class FrameError(Exception):
    pass


@dataclass
class Frame:
    """A frame = the operator definitions in force. name → how a computation is evaluated."""
    name: str
    ops: dict          # ast-op-class-name -> callable
    description: str = ""


# the DEFAULT frame — ordinary arithmetic. ONE frame among many, with NO privileged status.
_STD_OPS = {
    "Add": operator.add, "Sub": operator.sub, "Mult": operator.mul,
    "Div": operator.truediv, "Pow": operator.pow, "Mod": operator.mod,
    "USub": operator.neg, "UAdd": operator.pos,
}
STANDARD = Frame("standard", dict(_STD_OPS), "ordinary base-10 arithmetic (the default frame)")

# only arithmetic AST nodes are allowed — no Name/Call/Attribute → the evaluator is safe.
_ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd)


def evaluate(expr: str, frame: Frame = STANDARD):
    """Evaluate an arithmetic expression UNDER a frame's operator definitions. Safe:
    only arithmetic nodes permitted (no names, calls, attributes)."""
    tree = ast.parse(expr.strip(), mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            raise FrameError(f"non-arithmetic node {type(node).__name__}")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
                return n.value
            raise FrameError("non-numeric constant")
        if isinstance(n, ast.BinOp):
            op = type(n.op).__name__
            if op not in frame.ops:
                raise FrameError(f"frame {frame.name!r} has no operator {op}")
            return frame.ops[op](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp):
            op = type(n.op).__name__
            if op not in frame.ops:
                raise FrameError(f"frame {frame.name!r} has no unary {op}")
            return frame.ops[op](ev(n.operand))
        raise FrameError(f"unhandled {type(n).__name__}")

    return ev(tree)


# ── frame library + the RUN-GATE on frames ─────────────────────────────────
_REGISTRY = {"standard": STANDARD}


def register_frame(frame: Frame, witness: tuple) -> Frame:
    """Admit a frame to the library ONLY if it RUNS and yields its witness.
    witness = (expr, expected). A frame is real only when its formula computes what it
    claims — 'some frame' is not a frame; a running one is. (Run-gate, applied to frames.)"""
    expr, expected = witness
    got = evaluate(expr, frame)                       # must not raise
    if not _num_eq(got, expected):
        raise FrameError(f"frame {frame.name!r} REJECTED by run-gate: {expr} = {got}, not {expected}")
    _REGISTRY[frame.name] = frame
    return frame


def frames() -> dict:
    return dict(_REGISTRY)


def _num_eq(a, b) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return a == b


# ── the check: three-valued, frame-relative, never "false" ─────────────────
@dataclass
class Verdict:
    claim: str
    verdict: str
    frame: str
    actual: object = None
    message: str = ""


def check_claim(expr: str, claimed, frame: Frame = STANDARD) -> Verdict:
    claim_str = f"{expr} = {claimed}"
    try:
        actual = evaluate(expr, frame)
    except FrameError:
        return Verdict(claim_str, CANT_EVALUATE, frame.name,
                       message="not a recomputable arithmetic assertion — defer")
    if _num_eq(actual, claimed):
        return Verdict(claim_str, HOLDS, frame.name, actual, f"holds under frame {frame.name!r}")
    # differs under the given frame — does it hold under ANY OTHER registered frame?
    for fname, f in _REGISTRY.items():
        if fname == frame.name:
            continue
        try:
            if _num_eq(evaluate(expr, f), claimed):
                return Verdict(claim_str, DOESNT_HOLD, frame.name, actual,
                    f"does NOT hold under {frame.name!r} ({expr} = {actual}), but HOLDS under "
                    f"{fname!r} — name the frame you mean, or fix it")
        except FrameError:
            continue
    # differs under every known frame → still NOT "false": surface the unstated frame.
    return Verdict(claim_str, DOESNT_HOLD, frame.name, actual,
        f"does NOT hold under {frame.name!r} ({expr} = {actual}) or any known frame — "
        f"state your frame (operator/base/rounding), declare it so it runs, or fix it")


# ── scan an outgoing draft for computed assertions ─────────────────────────
# an arithmetic assertion: an expression containing an operator, '=', then a number.
_ASSERT = re.compile(r"(\d[\d+\-*/^%().\s]*?[-+*/^%][\d+\-*/^%().\s]*?)=\s*(-?\d+(?:\.\d+)?)\s*(%?)")


def scan_draft(text: str, frame: Frame = STANDARD) -> list:
    """Find computed assertions (EXPR op ... = NUMBER) in a draft and check each. Only
    recomputable arithmetic assertions surface; everything else (empirical numbers like
    '934 patterns', file counts, rates) is CANT_EVALUATE and dropped — a DIFFERENT verifier's
    job, honestly out of scope here."""
    out = []
    for m in _ASSERT.finditer(text):
        expr = m.group(1).strip().replace("^", "**")
        raw = m.group(2)
        claimed = float(raw) if "." in raw else int(raw)
        # PERCENTAGE FRAME: 'EXPR = Z%' declares the percent frame — Z% means Z/100. So
        # '6/6 = 100%' HOLDS (1.0 == 100/100), while a real percent lie ('6/6 = 50%') still
        # DOESNT_HOLD. Honoring the declared '%' frame is the floor's own principle, not a
        # bypass. (Fixed 2026-07-03: the % was silently dropped → 3 false A7 positives.)
        if m.group(3) == "%":
            claimed = claimed / 100.0
        v = check_claim(expr, claimed, frame)
        if v.verdict != CANT_EVALUATE:
            out.append(v)
    return out


# ── self-test ──────────────────────────────────────────────────────────────
def _selftest() -> bool:
    ok, total = 0, 0

    def check(desc, cond):
        nonlocal ok, total
        total += 1
        ok += bool(cond)
        print(f"  {'OK ' if cond else 'XX '} {desc}")

    print("standard frame (the default, NOT privileged truth):")
    v = check_claim("2+2", 5)                     # the Radiohead claim, standard frame
    check(f"2+2=5 under standard → DOESNT_HOLD, not 'false'  [{v.message}]", v.verdict == DOESNT_HOLD)
    check("2+2=4 under standard → HOLDS", check_claim("2+2", 4).verdict == HOLDS)
    check("3*4=12 under standard → HOLDS", check_claim("3*4", 12).verdict == HOLDS)

    print("\nframe extensibility + the run-gate:")
    # the Radiohead frame: a + b = a + b + 1  → 2+2 = 5, exactly.
    radiohead = Frame("radiohead", {**_STD_OPS, "Add": lambda a, b: a + b + 1},
                      "the Radiohead frame — a+b = a+b+1")
    register_frame(radiohead, witness=("2+2", 5))          # run-gate: must yield 5
    check("radiohead frame admitted (its formula runs → 2+2=5)", "radiohead" in frames())
    v = check_claim("2+2", 5, radiohead)
    check(f"2+2=5 under radiohead → HOLDS  [{v.message}]", v.verdict == HOLDS)
    # now standard-frame check knows another frame makes it hold → says so, still not "false"
    v = check_claim("2+2", 5)
    check(f"2+2=5 under standard now cites radiohead  [{v.message}]",
          v.verdict == DOESNT_HOLD and "radiohead" in v.message)

    print("\nthe run-gate REJECTS a frame whose formula doesn't do what it claims:")
    bogus = Frame("bogus", {**_STD_OPS, "Add": lambda a, b: a + b}, "claims 2+2=5 but is really standard")
    try:
        register_frame(bogus, witness=("2+2", 5))
        check("bogus frame rejected", False)
    except FrameError:
        check("bogus frame REJECTED by run-gate (2+2=4, not 5)", True)

    print("\nscanning a draft:")
    verds = scan_draft("the sum is 2+2=5 and separately 3*4=12")
    kinds = {v.claim.split(" =")[0]: v.verdict for v in verds}
    check(f"draft scan flags 2+2=5 (DOESNT_HOLD) and passes 3*4=12 (HOLDS)  {kinds}",
          kinds.get("2+2") == DOESNT_HOLD and kinds.get("3*4") == HOLDS)
    empirical = scan_draft("the Brain has 934 patterns across 9 categories")
    check(f"empirical numbers ('934 patterns') → not a computed assertion → ignored  ({len(empirical)} flagged)",
          empirical == [])

    print("\npercentage frame (the 'X/Y = Z%' fix — Z% means Z/100):")
    pct_ok = scan_draft("fire-rate 6/6 = 100% this session")
    check(f"'6/6 = 100%' → HOLDS (percent frame), floor won't fire  {[v.verdict for v in pct_ok]}",
          len(pct_ok) == 1 and pct_ok[0].verdict == HOLDS)
    pct_lie = scan_draft("the fire-rate was 6/6 = 50%")
    check(f"a REAL percent lie '6/6 = 50%' → DOESNT_HOLD (still caught)  {[v.verdict for v in pct_lie]}",
          len(pct_lie) == 1 and pct_lie[0].verdict == DOESNT_HOLD)

    print(f"\naccuracy: {ok}/{total} = {100 * ok // total}%")
    return ok == total


def main():
    import sys
    if len(sys.argv) < 2:
        raise SystemExit(0 if _selftest() else 1)
    # ad-hoc: numeric_floor.py "2+2" 5
    expr, claimed = sys.argv[1], sys.argv[2]
    cl = float(claimed) if "." in claimed else int(claimed)
    v = check_claim(expr, cl)
    print(f"{v.verdict}  ({v.message})")


if __name__ == "__main__":
    main()
