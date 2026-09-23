#!/usr/bin/env python3
"""aptness.py — mechanism #2: the pre-advice APTNESS selftest (end loose-recognition
false alarms). Companion to logic_lane/pause; the registry is one of its selftest sources.

THE PROBLEM: the Brain surfaces a move surface-similar-but-WRONG for this moment
(cross-architecture-model-deployment fired on an A/B question; MathBrain read "A/B" as a
fraction). FIX: before a move is surfaced, run SEVERAL DIFFERENT-NATURE checks and attach
an APTNESS SCORE — loud-first, the score is SHOWN, the caller/floor decides. We do NOT
"fire less" (that silences good advice — the mirror trap that over-fired 4Q's
builder_review). We fire WITH a self-assessed aptness, and SUPPRESS only on a HARD fail
(a proven tautology / a hard axiom-violation). Measure CALIBRATION (apt-fires / total),
never a suppression rate.

APT (Illia's sitting, settled 2026-07-10) = structurally-fitting THIS moment, OUTCOME-BLIND
(same law as `held`: aptness ≠ correctness). A fire is apt when it passes a majority of
independent-nature checks:
  - ROBUSTNESS        broad, decisive support — not a brittle single cue (margin over the
                      runner-up + an absolute floor).
  - NON-DISCRIMINATION it would NOT also fire on unrelated CONTROL situations (the tautology
                      class — the strongest catch; a HARD fail if it fires on most controls).
  - PRECONDITION-FIT  the move's consumed signature is actually present (a math move needs a
                      math expr — math_need._looks_math IS this for the math lane; pluggable
                      per lane; N/A for a plain dialogue move).
  - AXIOM-OK          it doesn't violate a registry axiom (pluggable; a HARD fail if it does).

Grading via the ONE wisdom loop (no new grader): the aptness score rides the fire row;
`held` stays the deliberation signal.

  python3 aptness.py --selftest
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# unrelated, diverse control situations — a move that ALSO fires on these is a tautology.
CONTROLS = (
    "the weather is nice today",
    "restart the gateway daemon on the mesh node",
    "i love you brother, thank you",
    "what time is the meeting tomorrow",
)
ROBUST_FLOOR = 0.35     # a fire below this absolute score is not decisive (calibratable)
ROBUST_MARGIN = 0.05    # …and must clear the runner-up by at least this (brittle otherwise)
TAUTOLOGY_FRAC = 0.5    # fires on >= this fraction of controls → HARD fail (non-discriminating)


@dataclass
class Check:
    name: str
    applicable: bool
    passed: bool | None       # None when not applicable to this lane
    hard: bool = False        # a failed `hard` check forces suppression
    detail: str = ""


@dataclass
class AptnessReport:
    move: str
    situation: str
    checks: list = field(default_factory=list)
    lane: str = "brain"

    @property
    def _applicable(self):
        return [c for c in self.checks if c.applicable]

    @property
    def score(self) -> float:
        """Fraction of APPLICABLE checks passed (0..1). Loud-first: always shown."""
        ap = self._applicable
        return round(sum(1 for c in ap if c.passed) / len(ap), 3) if ap else 0.0

    @property
    def hard_fail(self) -> bool:
        return any(c.applicable and c.passed is False and c.hard for c in self.checks)

    @property
    def verdict(self) -> str:
        if self.hard_fail:
            bad = next(c.name for c in self.checks if c.applicable and c.passed is False and c.hard)
            return f"SUPPRESS — hard fail: {bad}"
        return f"fire (aptness {self.score})"


def _robustness(candidates: list) -> Check:
    """candidates = [(move, score), ...] descending. Decisive + not brittle."""
    if not candidates:
        return Check("robustness", False, None, detail="no candidates")
    top = float(candidates[0][1])
    runner = float(candidates[1][1]) if len(candidates) > 1 else 0.0
    ok = top >= ROBUST_FLOOR and (top - runner) >= ROBUST_MARGIN
    return Check("robustness", True, ok, detail=f"top={top:.3f} margin={top - runner:.3f}")


def _non_discrimination(move: str, recall_fn, controls=CONTROLS, k: int = 3) -> Check:
    """Does `move` ALSO surface for unrelated controls? recall_fn(sit) -> [(move, score), ...].
    HARD fail if it fires on >= TAUTOLOGY_FRAC of controls (a tautology, fires on anything)."""
    if recall_fn is None:
        return Check("non_discrimination", False, None, detail="no recall_fn")
    hits = 0
    for c in controls:
        try:
            top = [m for m, _ in (recall_fn(c) or [])[:k]]
        except Exception:
            top = []
        hits += move in top
    frac = hits / len(controls)
    passed = frac < TAUTOLOGY_FRAC
    return Check("non_discrimination", True, passed, hard=True,
                 detail=f"fires on {hits}/{len(controls)} controls")


def _precondition_fit(situation: str, precondition_fn) -> Check:
    """The move's consumed signature must actually be present. precondition_fn(situation)
    -> bool (e.g. math_need's is_math for the math lane). N/A when None (plain dialogue move)."""
    if precondition_fn is None:
        return Check("precondition_fit", False, None, detail="no precondition (dialogue move)")
    try:
        ok = bool(precondition_fn(situation))
    except Exception as e:
        return Check("precondition_fit", True, False, detail=f"precondition raised: {e}")
    return Check("precondition_fit", True, ok, detail=("present" if ok else "MISSING — consumes X, no X"))


def _axiom_ok(axiom_check_fn) -> Check:
    """Does the move violate a registry axiom? axiom_check_fn() -> (ok: bool, why). N/A when
    None. HARD fail on violation (a move that contradicts a proven axiom is never apt)."""
    if axiom_check_fn is None:
        return Check("axiom_ok", False, None, detail="no axiom check")
    try:
        ok, why = axiom_check_fn()
    except Exception as e:
        return Check("axiom_ok", True, False, hard=True, detail=f"axiom check raised: {e}")
    return Check("axiom_ok", True, bool(ok), hard=True, detail=(why or ("ok" if ok else "VIOLATION")))


def aptness(situation: str, move: str, candidates: list, *, recall_fn=None,
            precondition_fn=None, axiom_check_fn=None, lane: str = "brain") -> AptnessReport:
    """Run every applicable check on a recognized move BEFORE it is surfaced. Loud-first:
    returns a report with a SHOWN score; only `hard_fail` argues for suppression."""
    checks = [
        _robustness(candidates),
        _non_discrimination(move, recall_fn),
        _precondition_fit(situation, precondition_fn),
        _axiom_ok(axiom_check_fn),
    ]
    return AptnessReport(move=move, situation=situation, checks=checks, lane=lane)


def render(r: AptnessReport) -> str:
    lines = [f"aptness of {r.move!r} for {r.situation[:56]!r}: {r.verdict}"]
    for c in r.checks:
        mark = "·  n/a" if not c.applicable else (" ✓ pass" if c.passed else " ✗ FAIL")
        lines.append(f"  {mark}  {c.name:18} {c.detail}")
    return "\n".join(lines)


def selftest() -> int:
    checks = []

    # a discriminating recall: M_apt fires ONLY for its target; a tautology M_tauto fires
    # for EVERYTHING (including controls). Deterministic — no embedder needed.
    def recall_apt(sit):
        if "config" in sit or "editing" in sit:
            return [("read-docs-before-editing", 0.72), ("other", 0.41)]
        return [("other", 0.30)]

    def recall_tauto(sit):
        return [("cross-architecture-fires-on-anything", 0.46), ("x", 0.44)]

    # 1. a genuinely apt fire: decisive margin, discriminates, no false control hits.
    a = aptness("about to edit the gateway config blind", "read-docs-before-editing",
                [("read-docs-before-editing", 0.72), ("other", 0.41)], recall_fn=recall_apt)
    checks.append(("apt fire passes robustness", a.checks[0].passed is True))
    checks.append(("apt fire passes non-discrimination", a.checks[1].passed is True))
    checks.append(("apt fire NOT hard-fail", a.hard_fail is False))
    checks.append(("apt fire high score", a.score >= 0.99))

    # 2. THE SPECIMEN: a tautology move that fires on everything → HARD fail (suppress).
    t = aptness("is my A/B conversion difference significant", "cross-architecture-fires-on-anything",
                [("cross-architecture-fires-on-anything", 0.46), ("x", 0.44)], recall_fn=recall_tauto)
    checks.append(("tautology fails non-discrimination", t.checks[1].passed is False))
    checks.append(("tautology is HARD fail → SUPPRESS", t.hard_fail is True
                   and t.verdict.startswith("SUPPRESS")))

    # 3. brittle fire: thin margin + low absolute → robustness fails (soft, score down, not suppressed)
    b = aptness("some ambiguous ask", "brittle-move",
                [("brittle-move", 0.33), ("almost-tied", 0.31)], recall_fn=recall_apt)
    checks.append(("brittle fire fails robustness", b.checks[0].passed is False))
    checks.append(("brittle fire NOT hard-suppressed (loud-first)", b.hard_fail is False))
    checks.append(("brittle fire score reflects the miss", 0.0 < b.score < 1.0))

    # 4. precondition-fit (the math lane): a math move with NO math expr → MISSING.
    import math_need
    pf = lambda s: math_need.math_need(s).is_math
    m1 = aptness("is my A/B test significant", "math:solve", [("math:solve", 0.9)],
                 precondition_fn=pf, lane="math")
    m2 = aptness("solve x**2 - 5*x + 6 = 0", "math:solve", [("math:solve", 0.9)],
                 precondition_fn=pf, lane="math")
    checks.append(("math move on 'A/B' → precondition MISSING", m1.checks[2].passed is False))
    checks.append(("math move on real expr → precondition present", m2.checks[2].passed is True))

    # 5. axiom violation → HARD fail.
    v = aptness("x", "m", [("m", 0.8)], axiom_check_fn=lambda: (False, "contradicts axiom Y"))
    checks.append(("axiom violation → hard fail", v.hard_fail is True))

    # 6. applicability: a plain dialogue move has only robustness+non-discrimination applicable.
    d = aptness("some dialogue", "a-move", [("a-move", 0.6), ("b", 0.3)], recall_fn=recall_apt)
    applicable = [c.name for c in d.checks if c.applicable]
    checks.append(("dialogue move: only robustness+non-discrimination apply",
                   set(applicable) == {"robustness", "non_discrimination"}))

    ok = 0
    for name, passed in checks:
        print(f"  {'✓' if passed else '✗ FAIL'}  {name}")
        ok += passed
    print(f"\n{ok}/{len(checks)} checks passed"
          + ("" if ok == len(checks) else " — FIX BEFORE TRUSTING"))
    return 0 if ok == len(checks) else 1


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        raise SystemExit(selftest())
    print(__doc__)


if __name__ == "__main__":
    main()
