#!/usr/bin/env python3
"""mathbrain.py — the MathematicalBrain v1 (the PCE Brain architecture, for math).

Council-designed 2026-06-28 (Illia·Claude·Steward), curated + built by Claude. Two chambers:
  EYE   — classify the expression's STRUCTURE against a finite pattern set, with a CONFIDENCE.
  FLOOR — deterministic compute (sympy): exact, never guessed.
Dispatch: confidence ≥ threshold → solve with sympy; below → defer to the REVIEW QUEUE
(NOT auto-retrain — that optimizes away visibility). sympy errors also queue. Threshold is
bounds-checked [0.5, 0.99]. Same shape as the PCE brain: recognize → floor → log for human
review → tune. The honest split it fixes: an LLM has math INTUITION but not exactness — this
supplies the exactness. The eye proposes; deterministic compute guarantees.

Run:
  python3 mathbrain.py "x**2 - 5*x + 6 = 0"      # classify + solve, exact
  python3 mathbrain.py "factor: x**3 - 1"        # explicit op hint
  python3 mathbrain.py --review                   # scan the defer/reject queue
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # published settings module (see VENDORING.md)

QUEUE = paths.BRAIN_HOME / "math_misses.jsonl"
THRESHOLD = 0.7
assert 0.5 <= THRESHOLD <= 0.99, "threshold out of bounds [0.5, 0.99]"
_OP_HINTS = {"factor", "simplify", "solve", "diff", "integrate", "expand"}


@dataclass
class Result:
    pattern: str
    confidence: float
    op: str
    answer: object
    exact: bool
    note: str = ""


SOURCE_WINDOW = 120   # chars of context kept each side of the expression


def _queue(rec: dict):
    rec["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rec.setdefault("review_status", "pending")
    with QUEUE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def _source_excerpt(source: str, text: str) -> str:
    """The sentence the expression was cut out of, windowed around it.

    Added 2026-07-25 (L2 audit). Without it a queue row cannot be graded at all: "1/3" is
    'one third' or '1 of 3 done' and ONLY the source says which. The first 530 rows were
    logged expression-only and 9 of them are permanently ungradable because of it. Windowed
    rather than truncated-from-the-start — a dialogue turn can be thousands of characters
    and the expression is rarely at the front."""
    if not source:
        return ""
    source = source.strip()
    key = text.split(":", 1)[1].strip() if (
        ":" in text and text.split(":", 1)[0].strip().lower() in _OP_HINTS) else text.strip()
    i = source.find(key) if key else -1
    if i < 0:                                   # expression not found verbatim → head of turn
        head = source[:2 * SOURCE_WINDOW]
        return head + ("…" if len(source) > len(head) else "")
    a, b = max(0, i - SOURCE_WINDOW), min(len(source), i + len(key) + SOURCE_WINDOW)
    return ("…" if a else "") + source[a:b] + ("…" if b < len(source) else "")


def _parse(text: str):
    import sympy as sp
    from sympy.parsing.sympy_parser import parse_expr
    op_hint = None
    if ":" in text and text.split(":", 1)[0].strip().lower() in _OP_HINTS:
        op_hint, text = (s.strip() for s in text.split(":", 1))
        op_hint = op_hint.lower()
    eqs, expr = [], None
    for p in (s for s in text.split(";") if s.strip()):
        if "=" in p:
            lhs, rhs = p.split("=", 1)
            eqs.append(sp.Eq(parse_expr(lhs), parse_expr(rhs)))
        else:
            expr = parse_expr(p)
    syms = set().union(*[e.free_symbols for e in eqs]) if eqs else (expr.free_symbols if expr is not None else set())
    return expr, eqs, sorted(syms, key=str), op_hint


def classify(expr, eqs, symbols):
    """The EYE: structural classification + heuristic confidence → (pattern, conf, op)."""
    import sympy as sp
    if len(eqs) > 1:
        return ("system", 0.85, "solve")
    if eqs:
        e0 = eqs[0].lhs - eqs[0].rhs
        if symbols and e0.is_polynomial(*symbols):
            deg = sp.degree(e0, symbols[0]) if len(symbols) == 1 else None
            return ("polynomial_equation", 0.9 if (deg is not None and deg <= 6) else 0.75, "solve")
        if e0.has(sp.sin, sp.cos, sp.tan, sp.exp, sp.log):
            return ("transcendental_equation", 0.6, "solve")
        return ("equation_other", 0.55, "solve")
    t = expr
    if symbols and t.is_polynomial(*symbols):
        return ("polynomial_expr", 0.85, "factor")
    if t.has(sp.Integral, sp.Derivative):
        return ("unevaluated_calculus", 0.8, "doit")
    return ("expr_other", 0.6, "simplify")


def _execute(op, expr, eqs, symbols):
    import sympy as sp
    if op == "solve":
        return sp.solve(eqs if eqs else expr, symbols)
    if op == "factor":
        return sp.factor(expr)
    if op == "simplify":
        return sp.simplify(expr)
    if op == "expand":
        return sp.expand(expr)
    if op == "diff":
        return sp.diff(expr, *symbols)
    if op == "integrate":
        return sp.integrate(expr, *symbols)
    if op == "doit":
        return expr.doit()
    raise ValueError(f"unknown op {op}")


def solve(text: str, source: str = "") -> Result:
    """`source` is the situation the expression was extracted from — pass it whenever you
    have it (node.step does). Every queued row carries a windowed excerpt of it, because a
    row without its sentence is a hypothesis nobody can grade."""
    src = _source_excerpt(source, text)

    def q(rec: dict):
        if src:
            rec["source"] = src
        _queue(rec)                 # global lookup on purpose: math_review.replay stubs it

    try:
        expr, eqs, symbols, op_hint = _parse(text)
    except Exception as e:
        q({"input": text, "stage": "parse", "error": f"{type(e).__name__}: {e}"})
        return Result("unparseable", 0.0, "-", None, False, f"parse failed → queued: {e}")
    pattern, conf, op = classify(expr, eqs, symbols)
    if op_hint:
        op, conf = op_hint, max(conf, 0.95)   # explicit op named → no "which op" uncertainty to gate on
    if conf < THRESHOLD:
        if pattern == "transcendental_equation":
            # frames run-gate (C1, 2026-07-05): structural confidence cannot separate
            # solvable transcendentals (sin(x)=0.5) from unsolvable ones
            # (exp(x)+sin(x)=x**3) — only the attempt can. Exact solve is the floor,
            # not a guess: succeed → answer + a queued witness row (visibility kept);
            # fail → defer exactly as before.
            try:
                ans = _execute(op, expr, eqs, symbols)
            except Exception:
                ans = None
            if ans:
                q({"input": text, "pattern": pattern, "confidence": conf, "op": op,
                   "reason": "below threshold → run-gate witness (solved exactly)",
                   "review_status": "auto_witness"})
                return Result(pattern, conf, op, ans, True,
                              "run-gate witness: low structural confidence, sympy solved exactly")
        q({"input": text, "pattern": pattern, "confidence": conf, "op": op, "reason": "below threshold"})
        return Result(pattern, conf, op, None, False, f"confidence {conf} < {THRESHOLD} → deferred to review queue")
    try:
        return Result(pattern, conf, op, _execute(op, expr, eqs, symbols), True)
    except Exception as e:
        q({"input": text, "pattern": pattern, "confidence": conf, "op": op,
           "sympy_error": f"{type(e).__name__}: {e}"})
        return Result(pattern, conf, op, None, False, f"sympy error → queued: {e}")


def review():
    if not QUEUE.exists():
        print("review queue empty — nothing deferred or rejected."); return
    rows = [json.loads(l) for l in QUEUE.read_text().splitlines() if l.strip()]
    print(f"review queue: {len(rows)} item(s) (newest last)")
    for r in rows[-20:]:
        why = r.get("reason") or r.get("sympy_error") or r.get("error", "")
        print(f"  [{r.get('review_status','?')}] {str(r.get('input','?'))[:48]!r} · "
              f"{r.get('pattern','-')} conf={r.get('confidence','-')} · {why}")


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    if sys.argv[1] == "--review":
        review(); return
    r = solve(" ".join(sys.argv[1:]))
    print(f"eye:   {r.pattern}  (confidence {r.confidence})")
    print(f"op:    {r.op}")
    print(f"floor: {r.answer}   [exact, sympy]" if r.exact else f"floor: — ({r.note})")


if __name__ == "__main__":
    main()
